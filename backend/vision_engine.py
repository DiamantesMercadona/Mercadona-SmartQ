# Importaciones y configuración
from __future__ import annotations
import asyncio
import ctypes
import os
import queue
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
from scipy.cluster.hierarchy import fclusterdata
from ultralytics import YOLO

try:
    from .database import DatabaseMSQ
except ImportError:
    from database import DatabaseMSQ
try:
    from .config import CONFIG
except ImportError:
    from config import CONFIG


# ------------------------------------------------------------------
# Fuente de vídeo por WebSocket (para recibir frames de la simulación)
# ------------------------------------------------------------------

class WsVideoSource:
    """
    Fuente de vídeo asíncrona que recibe frames JPEG desde un endpoint WebSocket.

    Diseñada para conectarse a /ws/video/events del backend FastAPI, que redistribuye
    los frames JPEG binarios enviados por la simulación 3D (Vue/Three.js) a través de
    Redis Pub/Sub.

    Corre en un hilo de background con su propio event loop asyncio. Los frames
    decodificados (numpy arrays BGR) se colocan en una Queue thread-safe para que el
    bucle principal de VisionEngine los consuma de forma síncrona.

    Flujo completo:
        Simulación → WS /ws/video → Redis → WS /ws/video/events → WsVideoSource → VisionEngine

    Parámetros de reconexión:
        En caso de pérdida de conexión, reintenta automáticamente cada 2 segundos.
    """

    _RECONNECT_DELAY = 2.0   # segundos entre reintentos de conexión
    _READ_TIMEOUT    = 0.15  # segundos de espera máxima en read() antes de devolver vacío

    def __init__(self, url: str, maxsize: int = 8) -> None:
        """
        Args:
            url:     URL WebSocket completa, p.ej. 'ws://localhost:8000/api/v1/ws/video/events'
            maxsize: Tamaño máximo de la cola interna de frames.
                     Frames más antiguos se descartan al llenarse (backpressure).
        """
        self._url = url
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Arranca el hilo de recepción de frames en background."""
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="WsVideoSource",
        )
        self._thread.start()

    def stop(self) -> None:
        """Señaliza el cierre y espera a que el hilo termine (máximo 4 s)."""
        self._stop_event.set()
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=4.0)
        # Sentinel para desbloquear cualquier read() pendiente
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

    def release(self) -> None:
        """Alias de stop() para compatibilidad con la interfaz de cv2.VideoCapture."""
        self.stop()

    # ------------------------------------------------------------------
    # Interfaz pública (compatible con cv2.VideoCapture)
    # ------------------------------------------------------------------

    def isOpened(self) -> bool:  # noqa: N802
        """Devuelve True mientras el hilo receptor esté activo."""
        return (
            self._thread is not None
            and self._thread.is_alive()
            and not self._stop_event.is_set()
        )

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Lee el siguiente frame disponible de la cola interna.

        Returns:
            ``(True, frame)``  → frame BGR listo para procesar.
            ``(False, None)``  → sin frame en este ciclo (WS reconectando o cola vacía).
                                 Llama a ``isOpened()`` para saber si la fuente sigue activa.
        """
        if self._stop_event.is_set():
            return False, None
        try:
            frame = self._queue.get(timeout=self._READ_TIMEOUT)
            if frame is None:       # sentinel de cierre
                return False, None
            return True, frame
        except queue.Empty:
            return False, None      # sin frame en este ciclo; la fuente sigue activa

    # ------------------------------------------------------------------
    # Internals: hilo de background + event loop asyncio
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Crea un event loop asyncio dedicado y ejecuta la coroutine de recepción."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._receive_frames())
        except Exception as exc:
            print(f"[WsVideoSource] Error en el loop asyncio: {exc}")
        finally:
            self._loop.close()
            try:
                self._queue.put_nowait(None)   # sentinel de cierre
            except queue.Full:
                pass

    async def _receive_frames(self) -> None:
        """Coroutine principal: conecta al WebSocket y recibe frames JPEG en bucle.

        Reconexión automática cada ``_RECONNECT_DELAY`` segundos en caso de error.
        """
        import websockets  # importación local para no penalizar si no se usa el modo WS

        while not self._stop_event.is_set():
            try:
                async with websockets.connect(
                    self._url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    print(f"[WsVideoSource] Conectado a {self._url}")
                    async for message in ws:
                        if self._stop_event.is_set():
                            return

                        if not isinstance(message, bytes):
                            continue  # ignorar mensajes de texto

                        frame = self._decode_jpeg(message)
                        if frame is None:
                            continue

                        # Backpressure: descartar el frame más antiguo si la cola está llena
                        if self._queue.full():
                            try:
                                self._queue.get_nowait()
                            except queue.Empty:
                                pass
                        try:
                            self._queue.put_nowait(frame)
                        except queue.Full:
                            pass  # descartado si la cola se llenó justo antes

            except OSError as exc:
                print(f"[WsVideoSource] No se pudo conectar a {self._url}: {exc}")
            except Exception as exc:  # noqa: BLE001
                print(f"[WsVideoSource] Error inesperado: {exc}")

            if not self._stop_event.is_set():
                print(f"[WsVideoSource] Reintentando en {self._RECONNECT_DELAY} s...")
                await asyncio.sleep(self._RECONNECT_DELAY)

    @staticmethod
    def _decode_jpeg(data: bytes) -> Optional[np.ndarray]:
        """Decodifica un buffer JPEG a un array numpy BGR (formato OpenCV).

        Args:
            data: Bytes del frame JPEG recibido por el WebSocket.

        Returns:
            Array BGR de shape (H, W, 3), o None si la decodificación falla.
        """
        try:
            buf = np.frombuffer(data, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            return frame if frame is not None and frame.size > 0 else None
        except Exception:
            return None


# Declara la clase VisionEngine, responsable del procesamiento de vídeo en tiempo real,
# detección e identificación de colas de clientes utilizando modelos de Deep Learning.
class VisionEngine:
    """
    Motor centralizado de visión artificial para el sistema Mercadona SmartQ (MSQ).

    Proporciona capacidades de análisis espacial y procesamiento de vídeo para:
    - Carga de flujos de vídeo (cámara o archivos multimedia).
    - Detección en tiempo real de personas mediante YOLOv8.
    - Agrupación (clustering) espacial para la separación de multitudes.
    - Segmentación dinámica de colas a través de 6 Regiones de Interés (ROIs).
    - Persistencia automatizada de instantáneas en la base de datos central.
    """

    # ------------------------------------------------------------------
    # Inicialización y gestión de ciclo de vida
    # ------------------------------------------------------------------

    # Esquemas reconocidos como fuente WebSocket
    _WS_SCHEMES = ("ws://", "wss://")

    # Inicializa el motor de visión configurando la captura, parámetros de YOLO, ROIs y base de datos.
    def __init__(self, source: Optional[Union[int, str]] = None) -> None:
        """Inicializa los recursos del motor de visión.

        Configura la captura de vídeo, inicializa la red neuronal YOLO, computa la geometría base
        de las ROIs y establece conexión con la base de datos relacional para el registro continuo.

        Args:
            source: Fuente de vídeo. Puede ser:
                - ``None``           → vídeo de demostración local (defecto).
                - ``"ws"``           → WebSocket con la URL configurada en CONFIG["VISION"]["ws_url"]
                                       (recibe frames JPEG de la simulación vía /ws/video/events).
                - ``"ws://..."``     → URL WebSocket completa explícita.
                - ``"wss://..."``    → URL WebSocket segura explícita.
                - ``int``            → índice de cámara física.
                - ``str`` (ruta)     → ruta a un archivo de vídeo local.

        Example:
            # Modo WebSocket (simulación 3D como fuente de vídeo)
            with VisionEngine(source="ws") as engine:
                engine.process()

            # Modo archivo local (defecto)
            with VisionEngine() as engine:
                engine.process()
        """
        self.base_dir = os.path.dirname(__file__)
        self.default_video = os.path.join(self.base_dir, "resources", "videos", "demo.webm")

        # ------------------------------------------------------------------
        # Resolución de la fuente de vídeo: archivo/cámara o WebSocket
        # ------------------------------------------------------------------
        vision_cfg = CONFIG.get("VISION", {})

        # El valor especial "ws" usa la URL configurada en CONFIG
        if source not in ("ws", "demo") and not (isinstance(source, str) and source.startswith(self._WS_SCHEMES)):
            source = "demo"

        if source == "ws":
            source = vision_cfg.get(
                "ws_url",
                "ws://localhost:8000/api/v1/ws/video/events",
            )

        self._ws_mode: bool = isinstance(source, str) and source.startswith(self._WS_SCHEMES)

        if self._ws_mode:
            # Modo WebSocket: usar WsVideoSource como fuente de frames
            assert isinstance(source, str)
            self._ws_source = WsVideoSource(source)
            self._ws_source.start()
            self.cap = self._ws_source          # interfaz compatible (isOpened / read / release)

            # Dimensiones de frame para los cálculos de ROI (configurables, sin VideoCapture)
            frame_w = vision_cfg.get("ws_frame_width", 1280)
            print(f"[VisionEngine] Modo WebSocket activado. URL: {source}")
        else:
            # Modo tradicional: archivo de vídeo o cámara física
            self._ws_source = None
            if source is None or source in ("demo"):
                source = self.default_video
            elif isinstance(source, str) and not os.path.isabs(source):
                source = os.path.join(self.base_dir, source)

            self.cap = cv2.VideoCapture(source)

            # Computar la anchura horizontal de forma dinámica respecto al ancho del vídeo
            frame_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            if frame_w <= 0:
                frame_w = 1280

        self.window_name = "MSQ Engine"

        # Obtener dimensiones físicas del monitor para una presentación adaptativa de la interfaz
        self.screen_width, self.screen_height = self._get_screen_size()
        self.window_margin = 80
        self.window_scale_min = 0.75

        # Inicialización segura de la ventana de renderizado de OpenCV
        try:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        except cv2.error:
            pass

        # Cargar configuración del modelo YOLOv8 desde la configuración global o establecer valores por defecto
        yolo_model = vision_cfg.get("yolo_model", "yolov8n.pt")
        self.model = YOLO(yolo_model)
        self.confidence_threshold = vision_cfg.get("yolo_confidence", 0.3)
        self.iou_threshold = vision_cfg.get("yolo_iou", 0.45)
        self.imgsz = vision_cfg.get("yolo_imgsz", 480)

        # Configuración del factor de omisión de frames (frame skipping) para optimizar rendimiento
        self.frame_skip = vision_cfg.get("yolo_frame_skip", 2)
        self.frame_count = 0
        self.last_person_boxes: List[Tuple[int, int, int, int]] = []

        # Parámetros para la separación por agrupamiento espacial de personas solapadas
        self.use_cluster_separation = True
        self.cluster_distance = 40

        # Historial y contadores de rendimiento temporal (FPS)
        self.fps_time = time.time()
        self.fps_count = 0
        self.fps = 0

        # Márgenes laterales para centrar las regiones de interés (ROIs) en pantalla
        self.roi_left_margin = 200
        self.roi_right_margin = 200
        available_w = frame_w - self.roi_left_margin - self.roi_right_margin

        # Cálculo dinámico de anchos para las 6 cajas (saltando el hueco central de separación)
        self.roi_margin_between = 10
        roi_w = max(10, (available_w - (6 * self.roi_margin_between)) // 7)
        self.roi_base_width = roi_w
        self.roi_base_height = 500

        # Configuración avanzada de variables de control y ajuste dinámico espacial
        self.roi_lower_shift_left = 120            # Desplazamiento lateral inferior hacia la izquierda de las 3 ROIs izquierdas
        self.roi_lower_shift_right = 160           # Desplazamiento lateral inferior hacia la derecha de las 3 ROIs derechas
        self.roi_lower_width = roi_w               # Ancho de referencia inferior de las ROIs
        self.roi_left_offset_x = 120               # Desplazamiento horizontal completo hacia la derecha de las 3 ROIs izquierdas
        self.roi_right_offset_x = -20              # Desplazamiento horizontal completo hacia la izquierda de las 3 ROIs derechas
        self.roi_right_width_delta = -15           # Reducción de ancho de las 3 ROIs derechas (se juntan hacia la izquierda)
        self.roi_global_y_offset = -10             # Elevación vertical global de todas las ROIs (subir 10px)
        self.roi_base_y = 250 + self.roi_global_y_offset  # Coordenada vertical Y base para los polígonos de las ROIs
 
        self.roi_top_expansion = -20               # Expansión superior de los polígonos de las ROIs
        self.roi_bottom_expansion = 70             # Expansión inferior de los polígonos de las ROIs
        self.roi_global_expansion = 0              # Expansión global de los polígonos de las ROIs
 
        self.roi_offset_x = 0                      # Offset dinámico horizontal global de ajuste fino
        self.roi_offset_y = 0                      # Offset dinámico vertical global de ajuste fino

        self.rois: Dict[str, Tuple[int, int, int, int]] = {}
        self.counts: Dict[str, List[str]] = {}

        # Mapeo de posiciones espaciales de cajas en pantalla (del 0 al 6, omitiendo el 3)
        posiciones = [0, 1, 2, 4, 5, 6]

        for i, pos_idx in enumerate(posiciones, 1):
            caja_id = str(i)
            caja_w = roi_w
            if i <= 3:
                x_roi = self.roi_left_margin + pos_idx * (roi_w + self.roi_margin_between) + self.roi_left_offset_x
            else:
                caja_w += self.roi_right_width_delta
                # El punto de inicio de la primera de la derecha (i = 4, pos_idx = 4)
                x_start_right = self.roi_left_margin + 4 * (roi_w + self.roi_margin_between) + self.roi_right_offset_x
                # Cada caja de la derecha se junta hacia la izquierda con su nuevo ancho y margen
                x_roi = x_start_right + (i - 4) * (caja_w + self.roi_margin_between)
            self.rois[caja_id] = (int(x_roi), int(self.roi_base_y), int(caja_w), self.roi_base_height)
            self.counts[caja_id] = []

        # Inicialización de la base de datos centralizada
        self.db = DatabaseMSQ()
        self.last_db_save_time = time.time()

        # Garantizar que las 6 cajas existan previamente registradas en el esquema de base de datos
        for caja_id in self.rois.keys():
            if not self.db.obtener_caja(id=caja_id):
                try:
                    self.db.crear_caja(id=caja_id, estado="abierta")
                    print(f"[VisionEngine] Caja '{caja_id}' registrada en la base de datos.")
                except sqlite3.IntegrityError:
                    pass

    # Soporte para gestores de contexto de Python (permite el uso de bloques 'with').
    def __enter__(self) -> VisionEngine:
        """Permite el soporte de gestor de contexto para inicializaciones seguras.

        Returns:
            Instancia configurada del motor de visión.
        """
        return self

    # Soporte para salida de gestor de contexto garantizando la liberación de recursos.
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Asegura la liberación automática de recursos al finalizar el contexto."""
        self._terminate()

    # Libera los controladores de captura física y destruye todas las ventanas gráficas activas.
    def _terminate(self) -> None:
        """Libera de forma ordenada los recursos del sistema y conexiones.

        Cierra la captura de vídeo (VideoCapture o WsVideoSource), destruye las interfaces
        visuales y finaliza la conexión activa a la base de datos SQLite.
        """
        # release() funciona igual para cv2.VideoCapture y WsVideoSource
        self.cap.release()
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass
        self.db.close()

    # ------------------------------------------------------------------
    # Construcción y cálculo geométrico de las ROIs
    # ------------------------------------------------------------------

    # Construye el polígono en base a la interpolación geométrica y desplazamientos espaciales.
    def _build_roi_polygon(self, caja_id: str) -> np.ndarray:
        """Calcula las coordenadas de los vértices del polígono de una ROI dinámica.

        Aplica las reglas espaciales del sistema que especifican reducciones/crecimientos
        en los lados superior e inferior de forma simétrica según su lateralidad.

        Args:
            caja_id: Identificador numérico de la caja a computar.

        Returns:
            Matriz de tipo NumPy con las cuatro coordenadas del polígono en formato [x, y].
        """
        roi_num = int(caja_id)
        is_left = roi_num <= 3

        # Determinar el índice de posición horizontal original en la escena
        posiciones = [0, 1, 2, 4, 5, 6]
        pos_idx = posiciones[roi_num - 1]

        # Computar geométricamente de forma dinámica para reflejar cualquier cambio en tiempo de ejecución
        roi_w = self.roi_base_width
        caja_w = roi_w
        if roi_num <= 3:
            x_roi = self.roi_left_margin + pos_idx * (roi_w + self.roi_margin_between) + self.roi_left_offset_x
        else:
            caja_w += self.roi_right_width_delta
            x_start_right = self.roi_left_margin + 4 * (roi_w + self.roi_margin_between) + self.roi_right_offset_x
            x_roi = x_start_right + (roi_num - 4) * (caja_w + self.roi_margin_between)

        w = caja_w
        h = self.roi_base_height

        # Computar la posición vertical corregida según el desplazamiento global
        y = self.roi_base_y + self.roi_offset_y

        # Determinar la coordenada superior X inicial con offset global incluido
        x = x_roi + self.roi_offset_x

        # Combinación de deltas dinámicos globales y de nivel
        bottom_expansion = self.roi_bottom_expansion + self.roi_global_expansion
        top_expansion = self.roi_top_expansion + self.roi_global_expansion

        if is_left:
            # Geometría para el conjunto de colas en el lateral izquierdo (crecen hacia la izquierda)
            top_left_x = x - top_expansion * (4 - roi_num)
            top_right_x = top_left_x + w + top_expansion

            bottom_left_x = x - self.roi_lower_shift_left - bottom_expansion * (4 - roi_num)
            bottom_right_x = bottom_left_x + w + bottom_expansion
        else:
            # Geometría para el conjunto de colas en el lateral derecho (crecen hacia la derecha)
            top_left_x = x + top_expansion * (roi_num - 4)
            top_right_x = top_left_x + w + top_expansion

            bottom_left_x = x + self.roi_lower_shift_right + bottom_expansion * (roi_num - 4)
            bottom_right_x = bottom_left_x + w + bottom_expansion

        return self._get_roi_polygon(
            int(top_left_x), int(top_right_x), int(y), int(h), int(bottom_left_x), int(bottom_right_x)
        )

    # Crea una estructura matricial NumPy de tipo polígono a partir de sus cuatro extremos calculados.
    def _get_roi_polygon(
        self,
        top_left_x: int,
        top_right_x: int,
        y: int,
        h: int,
        bottom_left_x: int,
        bottom_right_x: int,
    ) -> np.ndarray:
        """Crea la estructura del polígono a partir de las coordenadas especificadas.

        Args:
            top_left_x: Extremo superior izquierdo.
            top_right_x: Extremo superior derecho.
            y: Coordenada vertical superior.
            h: Altura vertical de la región.
            bottom_left_x: Extremo inferior izquierdo.
            bottom_right_x: Extremo inferior derecho.

        Returns:
            Estructura NumPy con el polígono mapeado.
        """
        return np.array(
            [
                [top_left_x, y],
                [top_right_x, y],
                [bottom_right_x, y + h],
                [bottom_left_x, y + h],
            ],
            dtype=np.int32,
        )

    # Identifica si una caja pertenece al lateral izquierdo y su índice relativo de caja.
    def _get_roi_shape_params(self, caja_id: str) -> Tuple[bool, int, int]:
        """Obtiene parámetros de posición de una caja para validación o análisis secundario.

        Args:
            caja_id: Identificador único de la caja.

        Returns:
            Tupla conteniendo (es_izquierda, indice_lateral, numero_caja).
        """
        roi_num = int(caja_id)
        is_left = roi_num <= 3
        side_index = roi_num - 1 if is_left else roi_num - 4
        return is_left, side_index, roi_num

    # Determina el punto de inicio inferior para una cadena lateral de ROIs de forma teórica.
    def _get_roi_lower_chain_start(self, caja_id: str) -> int:
        """Calcula teóricamente el inicio del segmento inferior en la cadena de alineamiento.

        Args:
            caja_id: Identificador numérico de la caja.

        Returns:
            Coordenada X horizontal inicial.
        """
        roi_num = int(caja_id)
        is_left = roi_num <= 3
        first_roi_id = "1" if is_left else "4"
        first_x, _, _, _ = self.rois[first_roi_id]
        if is_left:
            return first_x - self.roi_lower_shift_left
        else:
            return first_x + self.roi_lower_shift_right

    # Verifica si un par de coordenadas espaciales residen dentro del perímetro de un polígono.
    def _point_in_roi(self, point: Tuple[int, int], roi_polygon: np.ndarray) -> bool:
        """Determina mediante análisis de contorno si un punto se encuentra en la ROI.

        Args:
            point: Coordenadas (X, Y) del punto de control (ej. base de los pies de una persona).
            roi_polygon: Polígono de la ROI a evaluar.

        Returns:
            True si el punto reside en el polígono, False de lo contrario.
        """
        return cv2.pointPolygonTest(roi_polygon, point, False) >= 0

    # ------------------------------------------------------------------
    # Procesamiento espacial y separación de detecciones
    # ------------------------------------------------------------------

    # Filtra y reduce detecciones solapadas empleando clustering jerárquico por proximidad espacial.
    def _separate_overlapping_boxes(
        self, boxes: List[Tuple[int, int, int, int]]
    ) -> List[Tuple[int, int, int, int]]:
        """Aplica un agrupamiento espacial para separar detecciones de personas excesivamente cercanas.

        Evita sobreconteos y duplicados cuando varias cajas se superponen en zonas
        congestionadas, manteniendo la caja con mayor volumen de píxeles por clúster.

        Args:
            boxes: Lista de cajas delimitadoras candidatas detectadas.

        Returns:
            Lista filtrada de cajas sin solapamientos redundantes.
        """
        if len(boxes) <= 1 or not self.use_cluster_separation:
            return boxes

        try:
            # Obtener el centro geométrico bidimensional de cada caja
            centers = np.array([((box[0] + box[2]) / 2, (box[1] + box[3]) / 2) for box in boxes])

            # Agrupar jerárquicamente a partir de la distancia euclídea configurada
            clusters = fclusterdata(
                centers, t=self.cluster_distance, method="complete", criterion="distance"
            )

            filtered_boxes = []
            for cluster_id in np.unique(clusters):
                cluster_boxes = [boxes[i] for i in range(len(boxes)) if clusters[i] == cluster_id]
                if len(cluster_boxes) > 1:
                    # En caso de colisión, se conserva únicamente la caja de mayor superficie
                    largest = max(cluster_boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
                    filtered_boxes.append(largest)
                else:
                    filtered_boxes.append(cluster_boxes[0])

            return filtered_boxes
        except Exception:
            return boxes

    # Calcula la métrica de Intersección sobre Unión (IoU) entre dos rectángulos espaciales.
    def _iou(self, boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
        """Calcula la coincidencia relativa (IoU) entre dos cajas delimitadoras.

        Args:
            boxA: Coordenadas de la primera caja.
            boxB: Coordenadas de la segunda caja.

        Returns:
            Coeficiente IoU en el rango de [0.0, 1.0].
        """
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interW = max(0, xB - xA)
        interH = max(0, yB - yA)
        interArea = interW * interH

        boxAArea = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
        boxBArea = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])

        denom = float(boxAArea + boxBArea - interArea)
        if denom <= 0:
            return 0.0
        return interArea / denom

    # Actualiza y realiza el seguimiento de las trayectorias de detecciones basándose en IoU.
    def _update_tracks(
        self, detections: List[Tuple[int, int, int, int]]
    ) -> List[Tuple[int, Tuple[int, int, int, int]]]:
        """Realiza el seguimiento temporal (tracking) por heurística de proximidad.

        Args:
            detections: Lista de detecciones localizadas en el frame actual.

        Returns:
            Lista de tuplas de tipo (track_id, caja) conteniendo los elementos activos y estables.
        """
        if not hasattr(self, "tracks"):
            self.tracks: Dict[int, Dict[str, Any]] = {}
            self.next_track_id = 1
            self.max_missed_frames = 5
            self.track_iou_threshold = 0.3

        matched_tracks = set()
        matched_dets = set()

        # Construcción de la matriz de correspondencias IoU
        iou_matrix = []
        for t_id, t in self.tracks.items():
            row = [self._iou(t["box"], d) for d in detections]
            iou_matrix.append((t_id, row))

        # Asignación codiciosa (greedy matching) a las pistas existentes
        for t_id, row in iou_matrix:
            if not row:
                continue
            best_idx = int(np.argmax(row))
            best_iou = row[best_idx]
            if best_iou >= self.track_iou_threshold and best_idx not in matched_dets:
                self.tracks[t_id]["box"] = detections[best_idx]
                self.tracks[t_id]["misses"] = 0
                matched_tracks.add(t_id)
                matched_dets.add(best_idx)

        # Crear nuevas pistas para detecciones no emparejadas
        for i, det in enumerate(detections):
            if i in matched_dets:
                continue
            tid = self.next_track_id
            self.tracks[tid] = {"box": det, "misses": 0}
            matched_tracks.add(tid)
            self.next_track_id += 1

        # Incrementar pérdidas en pistas ausentes y eliminar las obsoletas
        for t_id in list(self.tracks.keys()):
            if t_id in matched_tracks:
                continue
            self.tracks[t_id]["misses"] += 1
            if self.tracks[t_id]["misses"] > self.max_missed_frames:
                del self.tracks[t_id]

        active = [
            (t_id, data["box"])
            for t_id, data in self.tracks.items()
            if data["misses"] == 0
        ]
        return active

    # ------------------------------------------------------------------
    # Bucle principal de procesamiento de video
    # ------------------------------------------------------------------

    # Inicia y ejecuta el procesamiento del flujo de vídeo frame a frame en tiempo real.
    def process(self) -> None:
        """Ejecuta el ciclo principal de captura, inferencia de YOLO y lógica espacial.

        Mantiene la cadencia controlada a 30 FPS, distribuye el procesamiento omitiendo frames
        según configuración y delega la representación visual del panel de control de forma robusta.

        En modo WebSocket la fuente puede no enviar frame en cada iteración (reconexión,
        red lenta…). En ese caso el bucle simplemente espera al siguiente ciclo sin romper
        el procesamiento, a diferencia del modo archivo/cámara donde un ``ret=False`` indica
        el fin del flujo y cierra el motor.

        Example:
            # Modo archivo/cámara (comportamiento original)
            with VisionEngine() as engine:
                engine.process()

            # Modo simulación WebSocket
            with VisionEngine(source="ws") as engine:
                engine.process()
        """
        target_fps = 30
        frame_time = 1.0 / target_fps

        while self.cap.isOpened():
            frame_start = time.time()
            ret, frame = self.cap.read()

            if not ret or frame is None:
                if self._ws_mode:
                    # En modo WS un ciclo sin frame es normal (WS reconectando o sin datos todavía).
                    # Mantener cadencia y reintentar en el siguiente tick.
                    elapsed = time.time() - frame_start
                    if elapsed < frame_time:
                        time.sleep(frame_time - elapsed)
                    continue
                else:
                    # En modo archivo/cámara el fin del flujo rompe el bucle.
                    break

            self.frame_count += 1

            # Dibujar primero los polígonos de las ROIs de fondo
            self._draw_rois(frame)

            # Ejecutar modelo de detección únicamente en los frames indicados por frame_skip
            if self.frame_count % self.frame_skip == 0:
                results = self.model(
                    frame,
                    classes=[0], # Detección únicamente de personas (0)
                    verbose=False,
                    conf=self.confidence_threshold,
                    iou=self.iou_threshold,
                    imgsz=self.imgsz,
                    augment=False,
                )

                person_boxes = []
                for r in results:
                    for box in r.boxes:
                        coords = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, coords)
                        person_boxes.append((x1, y1, x2, y2))

                # Dispersar detecciones redundantes y actualizar histórico temporal
                person_boxes = self._separate_overlapping_boxes(person_boxes)
                self.last_person_boxes = person_boxes
                tracked = self._update_tracks(person_boxes)
            else:
                # Utilizar predicciones del fotograma anterior en frames omitidos
                person_boxes = self.last_person_boxes
                tracked = self._update_tracks(person_boxes)

            current_counts: Dict[str, List[str]] = {str(i): [] for i in range(1, 7)}

            # Procesar pertenencia espacial utilizando preferentemente el histórico de tracks
            boxes_to_process = tracked if tracked else [(None, b) for b in person_boxes]
            for track_data in boxes_to_process:
                box = track_data[1]
                x1, y1, x2, y2 = box
                feet_x = int((x1 + x2) / 2)
                feet_y = y2

                in_any_roi = False
                for caja_id in self.rois.keys():
                    roi_polygon = self._build_roi_polygon(caja_id)
                    if self._point_in_roi((feet_x, feet_y), roi_polygon):
                        current_counts[caja_id].append("sinCarro")
                        in_any_roi = True
                        break

                color = (0, 255, 0)      # Las cajas de las personas son siempre verdes (requisito de UI)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

            self.counts = current_counts

            # Volcar instantánea métrica a base de datos de manera secuencial e intercalada
            current_time = time.time()
            if current_time - self.last_db_save_time >= 5.0:
                self.guardar_evento(self.counts)
                self.last_db_save_time = current_time

            # Dibujar elementos gráficos y ajustar el frame para visualización segura
            self._draw_interface(frame)
            display_frame = self._fit_frame_to_screen(frame)

            # Control de redimensionamiento e interfaz a prueba de fallos GUI / Headless
            try:
                if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) >= 0:
                    cv2.resizeWindow(
                        self.window_name, display_frame.shape[1], display_frame.shape[0]
                    )
                    cv2.imshow(self.window_name, display_frame)
                else:
                    break
            except cv2.error:
                pass

            try:
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
            except cv2.error:
                pass

            # Control exacto de FPS mediante retardos precisos
            elapsed = time.time() - frame_start
            sleep_time = frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

            # Computar frecuencia media de refresco
            self.fps_count += 1
            if time.time() - self.fps_time >= 1.0:
                self.fps = self.fps_count
                self.fps_count = 0
                self.fps_time = time.time()

        self._terminate()

    # Mapea y guarda la instantánea actual del estado de cajas en el gestor de base de datos relacional.
    def guardar_evento(self, counts: Dict[str, List[str]]) -> None:
        """Registra el conteo actual de colas como una instantánea en la base de datos.

        Mapea el desglose tipográfico de cada caja al esquema y lo almacena con marca de tiempo.

        Args:
            counts: Diccionario que asocia el identificador de caja con la lista de tipos de cliente ("conCarro"/"sinCarro") detectados.
        """
        self.db.registrar_instantanea(estado_cajas=counts)

    # ------------------------------------------------------------------
    # Renderizado de interfaz y visualización
    # ------------------------------------------------------------------

    # Dibuja los límites de los polígonos, contadores y cabecera sobre el fotograma de salida.
    def _draw_rois(self, frame: np.ndarray) -> None:
        """Dibuja únicamente los polígonos de contorno de las ROIs en el fotograma."""
        for caja_id in self.rois.keys():
            roi_polygon = self._build_roi_polygon(caja_id)
            cv2.polylines(frame, [roi_polygon], isClosed=True, color=(255, 0, 0), thickness=1)

    def _draw_interface(self, frame: np.ndarray) -> None:
        """Dibuja los elementos de la interfaz de usuario en el fotograma.

        Dibuja los textos informativos de cada caja alineados dinámicamente y el panel superior de resumen.

        Args:
            frame: Fotograma en formato de matriz NumPy sobre el cual dibujar.
        """
        for caja_id in self.rois.keys():
            roi_polygon = self._build_roi_polygon(caja_id)
            text_x = roi_polygon[3][0]
            text_y = roi_polygon[3][1] + 20
            personas = len(self.counts[caja_id])
            cv2.putText(
                frame,
                f"Caja {caja_id}: {personas}",
                (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 0),
                1,
            )

        # Panel superior de información general
        cv2.rectangle(frame, (15, 10), (510, 45), (0, 0, 0), -1)
        total_personas = sum(len(cola) for cola in self.counts.values())
        cv2.putText(
            frame,
            f"MSQ - Personas: {total_personas} | FPS: {self.fps}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 255, 0),
            1,
        )

    # Redimensiona el fotograma manteniendo la relación de aspecto para ajustarse a las cotas físicas de la pantalla.
    def _fit_frame_to_screen(self, frame: np.ndarray) -> np.ndarray:
        """Ajusta el tamaño del fotograma para visualizarse adecuadamente en pantalla.

        Args:
            frame: Fotograma original a redimensionar.

        Returns:
            Fotograma ajustado proporcionalmente al tamaño del monitor principal.
        """
        h, w = frame.shape[:2]
        max_w = max(320, self.screen_width - self.window_margin)
        max_h = max(240, self.screen_height - self.window_margin)
        min_w = int(self.screen_width * self.window_scale_min)
        min_h = int(self.screen_height * self.window_scale_min)

        fit_scale = min(max_w / w, max_h / h)
        min_scale = min_w / w if w < min_w else 0.0
        min_scale_h = min_h / h if h < min_h else 0.0

        scale = max(fit_scale if fit_scale < 1.0 else 1.0, min_scale, min_scale_h)
        scale = min(scale, fit_scale)

        if abs(scale - 1.0) < 0.01:
            return frame

        new_w = int(w * scale)
        new_h = int(h * scale)
        interpolation = cv2.INTER_LINEAR if scale > 1.0 else cv2.INTER_AREA
        return cv2.resize(frame, (new_w, new_h), interpolation=interpolation)

    # Obtiene el tamaño del monitor principal en píxeles de manera segura y adaptativa en Windows.
    def _get_screen_size(self) -> Tuple[int, int]:
        """Obtiene la resolución de pantalla activa en entornos Windows.

        Returns:
            Tupla conteniendo (ancho, alto) de la pantalla principal.
        """
        try:
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            return 1366, 768


# Punto de entrada principal en caso de ejecución independiente del motor de visión.
if __name__ == "__main__":
    with VisionEngine() as engine:
        engine.process()
