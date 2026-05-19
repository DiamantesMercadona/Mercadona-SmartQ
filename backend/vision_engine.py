import cv2
import numpy as np
from ultralytics import YOLO
from typing import Union, List, Tuple
import sqlite3
from datetime import datetime
import os
from scipy.cluster.hierarchy import fclusterdata
import time
import ctypes

try:
    from .database import DatabaseMSQ
except ImportError:
    from database import DatabaseMSQ

class VisionEngine:
    """
    Motor de visión artificial para Mercadona SmartQ (MSQ).
    Procesa flujo de video para la detección de personas y 
    gestiona colas mediante YOLOv8 y análisis espacial.
    """

    def __init__(self, source: Union[int, str, None] = None):
        """
        Inicializa los recursos del motor.
        """
        self.base_dir = os.path.dirname(__file__)
        self.default_video = os.path.join(self.base_dir, "resources", "3d_demo.webm")

        # Fuente de video
        if source is None:
            source = self.default_video
        elif isinstance(source, str) and not os.path.isabs(source):
            source = os.path.join(self.base_dir, source)

        self.cap = cv2.VideoCapture(source)
        self.window_name = 'MSQ Engine'

        # Pantalla disponible para la ventana de visualizacion.
        self.screen_width, self.screen_height = self._get_screen_size()
        self.window_margin = 80
        self.window_scale_min = 0.75

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)

        # Modelo YOLOv8 - optimizado para velocidad en video real
        self.model = YOLO('yolov8n.pt')  # Modelo nano para máxima velocidad
        self.confidence_threshold = 0.3   # Threshold más alto para reducir parpadeo
        self.iou_threshold = 0.45         # NMS estándar
        self.imgsz = 480                  # Resolución muy baja para 30 fps en video real
        
        # Frame skipping para duplicar FPS
        self.frame_skip = 2               # Procesar cada 2 frames
        self.frame_count = 0
        self.last_person_boxes = []       # Cajas del último frame procesado
        
        # Separación de personas pegadas
        self.use_cluster_separation = True
        self.cluster_distance = 40
        
        # FPS tracking
        self.fps_time = time.time()
        self.fps_count = 0
        self.fps = 0

        # Configuración de 6 ROIs (Regiones de Interés) para 6 cajas
        # Calculamos la anchura dinámicamente con el frame
        frame_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        if frame_w <= 0:
            frame_w = 1280  # Valor por defecto
            
        # Margen izquierdo (200, como la original) y márgen derecho simétrico
        left_margin = 200
        right_margin = 200
        available_w = frame_w - left_margin - right_margin
        
        # 6 cajas + 1 hueco en el medio = 7 espacios en total
        margin_between = 10
        roi_w = max(10, (available_w - (6 * margin_between)) // 7)
        
        self.rois = {}
        self.counts = {}
        
        # Índices de las posiciones de las cajas (saltándonos el índice 3: hueco central)
        posiciones = [0, 1, 2, 4, 5, 6]
        
        for i, pos_idx in enumerate(posiciones, 1):
            caja_id = str(i)
            x_roi = left_margin + pos_idx * (roi_w + margin_between)
            self.rois[caja_id] = (x_roi, 250, roi_w, 500)
            self.counts[caja_id] = 0

        # Conexión a la base de datos (canonical schema)
        self.db = DatabaseMSQ()
        self.last_db_save_time = time.time()

        # Asegurar que las 6 cajas existan en la tabla cajas
        for caja_id in self.rois.keys():
            if not self.db.obtener_caja(id=caja_id):
                try:
                    self.db.crear_caja(id=caja_id, estado="abierta")
                    print(f"[VisionEngine] Caja '{caja_id}' registrada en la base de datos.")
                except sqlite3.IntegrityError:
                    pass

    def guardar_evento(self, counts: dict):
        """
        Guarda una instantánea con el estado de las 6 colas a través de DatabaseMSQ.
        """
        # Mapeamos la detección cruda al esquema de instantaneas para cada caja
        # Definimos cada persona/grupo detectado de momento como "sinCarro".
        estado_cajas = {}
        for caja_id, personas in counts.items():
            estado_cajas[caja_id] = ["sinCarro"] * personas
        
        self.db.registrar_instantanea(
            estado_cajas=estado_cajas
        )

    def _separate_overlapping_boxes(self, boxes: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """
        Separa cajas solapadas usando clustering jerárquico.
        """
        if len(boxes) <= 1 or not self.use_cluster_separation:
            return boxes
        
        try:
            # Calcular centros de las cajas
            centers = np.array([(
                (box[0] + box[2]) / 2,
                (box[1] + box[3]) / 2
            ) for box in boxes])
            
            # Clustering jerárquico para separar grupos pegados
            clusters = fclusterdata(centers, t=self.cluster_distance, 
                                   method='complete', criterion='distance')
            
            # Para cada cluster con múltiples cajas, mantener solo la más grande
            filtered_boxes = []
            for cluster_id in np.unique(clusters):
                cluster_boxes = [boxes[i] for i in range(len(boxes)) if clusters[i] == cluster_id]
                if len(cluster_boxes) > 1:
                    largest = max(cluster_boxes, 
                                 key=lambda b: (b[2]-b[0]) * (b[3]-b[1]))
                    filtered_boxes.append(largest)
                else:
                    filtered_boxes.append(cluster_boxes[0])
            
            return filtered_boxes
        except Exception:
            return boxes

    def process(self) -> None:
        """
        Bucle principal optimizado para 30 fps con frame skipping.
        """
        target_fps = 30
        frame_time = 1.0 / target_fps
        
        while self.cap.isOpened():
            frame_start = time.time()
            ret, frame = self.cap.read()
            if not ret:
                break

            self.frame_count += 1
            
            # Procesar solo cada N frames para ganar velocidad
            if self.frame_count % self.frame_skip == 0:
                # Detección YOLO en frame actual
                results = self.model(frame, classes=0, verbose=False,
                                    conf=self.confidence_threshold, iou=self.iou_threshold,
                                    imgsz=self.imgsz, augment=False)

                person_boxes = []
                for r in results:
                    for box in r.boxes:
                        coords = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = map(int, coords)
                        person_boxes.append((x1, y1, x2, y2))
                
                # Separar detecciones solapadas
                person_boxes = self._separate_overlapping_boxes(person_boxes)
                self.last_person_boxes = person_boxes
            else:
                # Usar cajas del último frame procesado (suavizar)
                person_boxes = self.last_person_boxes

            current_counts = {str(i): 0 for i in range(1, 7)}

            for (x1, y1, x2, y2) in person_boxes:
                feet_x = int((x1 + x2) / 2)
                feet_y = y2

                in_any_roi = False
                for caja_id, (x_roi, y_roi, w_roi, h_roi) in self.rois.items():
                    if x_roi < feet_x < x_roi + w_roi and y_roi < feet_y < y_roi + h_roi:
                        current_counts[caja_id] += 1
                        in_any_roi = True
                        break  # Una persona solo puede estar en una cola

                color = (0, 255, 0) if in_any_roi else (200, 200, 200)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            self.counts = current_counts

            # Guardar en la base de datos (cada 5 segundos)
            current_time = time.time()
            if current_time - self.last_db_save_time >= 5.0:
                self.guardar_evento(self.counts)
                self.last_db_save_time = current_time

            # Dibujar interfaz
            self._draw_interface(frame)
            display_frame = self._fit_frame_to_screen(frame)
            cv2.resizeWindow(self.window_name, display_frame.shape[1], display_frame.shape[0])
            cv2.imshow(self.window_name, display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # Control de FPS
            elapsed = time.time() - frame_start
            sleep_time = frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            # Calcular FPS
            self.fps_count += 1
            if time.time() - self.fps_time >= 1.0:
                self.fps = self.fps_count
                self.fps_count = 0
                self.fps_time = time.time()

        self._terminate()

    def _draw_interface(self, frame: np.ndarray) -> None:
        """
        Dibuja la interfaz de usuario sobre el frame.
        """
        # Dibujar cada ROI y su contador
        for caja_id, (x, y, w, h) in self.rois.items():
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(frame, f"Caja {caja_id}: {self.counts[caja_id]}", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        # Panel superior agregado a todas las colas
        cv2.rectangle(frame, (15, 10), (475, 45), (0, 0, 0), -1)
        total_personas = sum(self.counts.values())
        cv2.putText(frame, f"MSQ - Personas en colas: {total_personas} | FPS: {self.fps}", (20, 35), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    def _get_screen_size(self) -> Tuple[int, int]:
        """
        Devuelve tamano del monitor principal con fallback seguro.
        """
        try:
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            return 1366, 768

    def _fit_frame_to_screen(self, frame: np.ndarray) -> np.ndarray:
        """
        Ajusta el frame al monitor manteniendo relacion de aspecto.
        """
        h, w = frame.shape[:2]
        max_w = max(320, self.screen_width - self.window_margin)
        max_h = max(240, self.screen_height - self.window_margin)
        min_w = int(self.screen_width * self.window_scale_min)
        min_h = int(self.screen_height * self.window_scale_min)

        # Escala objetivo para que el visor no se abra pequeno.
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

    def _terminate(self) -> None:
        """
        Libera hardware y cierra la base de datos.
        """
        self.cap.release()
        cv2.destroyAllWindows()
        self.db.close()

if __name__ == "__main__":
    engine = VisionEngine()
    engine.process()
