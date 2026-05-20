import cv2
import numpy as np
from ultralytics import YOLO
from typing import Union, List, Tuple, Dict
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
try:
    from .config import CONFIG
except ImportError:
    from config import CONFIG

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

        # Modelo YOLOv8 - parámetros controlados desde config para pruebas
        yolo_model = CONFIG.get("APP", {}).get("yolo_model", "yolov8n.pt")
        self.model = YOLO(yolo_model)
        self.confidence_threshold = CONFIG.get("APP", {}).get("yolo_confidence", 0.3)
        self.iou_threshold = CONFIG.get("APP", {}).get("yolo_iou", 0.45)
        self.imgsz = CONFIG.get("APP", {}).get("yolo_imgsz", 480)

        # Frame skipping configurable (1 = todos los frames)
        self.frame_skip = CONFIG.get("APP", {}).get("yolo_frame_skip", 2)
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
            base_y = 250
            h_roi = 500

            y_roi = base_y

            self.rois[caja_id] = (int(x_roi), int(y_roi), int(roi_w), h_roi)
            self.counts[caja_id] = 0

        # Desplazamientos independientes para cada lado (en píxeles)
        # En el lado izquierdo la base inferior debe moverse hacia la izquierda
        # En el lado derecho la base inferior debe moverse hacia la derecha
        self.roi_lower_shift_left = 70
        self.roi_lower_shift_right = 70
        self.roi_lower_width = roi_w

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

    def _iou(self, boxA: Tuple[int, int, int, int], boxB: Tuple[int, int, int, int]) -> float:
        # Intersection over Union for two boxes
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

    def _get_roi_polygon(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        bottom_left_x: int,
    ) -> np.ndarray:
        """
        Devuelve el polígono de una ROI manteniendo la parte superior fija.
        La parte inferior se encadena con la ROI siguiente para que los extremos
        inferiores queden contiguos sin mover la parte superior.
        """
        bottom_right_x = bottom_left_x + w
        return np.array([
            [x, y],
            [x + w, y],
            [bottom_right_x, y + h],
            [bottom_left_x, y + h],
        ], dtype=np.int32)

    def _get_roi_lower_chain_start(self, caja_id: str) -> int:
        """
        Calcula el inicio de la cadena inferior para cada lado.
        """
        roi_num = int(caja_id)
        is_left = roi_num <= 3
        first_roi_id = "1" if is_left else "4"
        first_x, _, _, _ = self.rois[first_roi_id]
        if is_left:
            return first_x - self.roi_lower_shift_left
        else:
            return first_x + self.roi_lower_shift_right

    def _point_in_roi(self, point: Tuple[int, int], roi_polygon: np.ndarray) -> bool:
        """
        Comprueba si un punto cae dentro de un polígono ROI.
        """
        return cv2.pointPolygonTest(roi_polygon, point, False) >= 0

    def _update_tracks(self, detections: List[Tuple[int, int, int, int]]) -> List[Tuple[int, Tuple[int, int, int, int]]]:
        """
        Actualiza tracks existentes con las detecciones actuales usando greedy IoU matching.
        Devuelve lista de (track_id, box) para tracks activos.
        """
        # Inicializar estructura de tracks si no existe
        if not hasattr(self, 'tracks'):
            # tracks: id -> {box, misses}
            self.tracks: Dict[int, Dict] = {}
            self.next_track_id = 1
            self.max_missed_frames = 5
            self.track_iou_threshold = 0.3

        matched_tracks = set()
        matched_dets = set()

        # Build IoU matrix
        iou_matrix = []
        for t_id, t in self.tracks.items():
            row = [self._iou(t['box'], d) for d in detections]
            iou_matrix.append((t_id, row))

        # Greedy matching: for each existing track, find best detection
        for t_id, row in iou_matrix:
            if not row:
                continue
            best_idx = int(np.argmax(row))
            best_iou = row[best_idx]
            if best_iou >= self.track_iou_threshold and best_idx not in matched_dets:
                # match
                self.tracks[t_id]['box'] = detections[best_idx]
                self.tracks[t_id]['misses'] = 0
                matched_tracks.add(t_id)
                matched_dets.add(best_idx)

        # Unmatched detections -> new tracks
        for i, det in enumerate(detections):
            if i in matched_dets:
                continue
            tid = self.next_track_id
            self.tracks[tid] = {'box': det, 'misses': 0}
            self.next_track_id += 1

        # Increment misses for unmatched tracks
        for t_id in list(self.tracks.keys()):
            if t_id in matched_tracks:
                continue
            self.tracks[t_id]['misses'] += 1
            if self.tracks[t_id]['misses'] > self.max_missed_frames:
                # delete stale track
                del self.tracks[t_id]

        # Return active tracks
        active = [(t_id, data['box']) for t_id, data in self.tracks.items() if data['misses'] <= self.max_missed_frames]
        return active

    def _get_roi_shape_params(self, caja_id: str) -> Tuple[bool, int, int]:
        """
        Devuelve si la ROI pertenece al lado izquierdo y el índice relativo dentro de su lado.
        """
        roi_num = int(caja_id)
        is_left = roi_num <= 3
        side_index = roi_num - 1 if is_left else roi_num - 4
        return is_left, side_index, roi_num

    def _build_roi_polygon(self, caja_id: str) -> np.ndarray:
        """
        Construye el polígono de la ROI con el borde superior intacto y la base
        inferior encadenada por lado.
        """
        x, y, w, h = self.rois[caja_id]
        is_left, side_index, _ = self._get_roi_shape_params(caja_id)
        # Mantener la separación horizontal entre las esquinas superiores
        # y replicarla en las esquinas inferiores.
        first_roi_id = "1" if is_left else "4"
        first_top_x = self.rois[first_roi_id][0]
        # delta entre el top-left de esta ROI y el primero del lado
        delta_x = x - first_top_x
        lower_chain_start = self._get_roi_lower_chain_start(caja_id)
        bottom_left_x = int(lower_chain_start + delta_x)
        return self._get_roi_polygon(x, y, w, h, bottom_left_x)

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
                # Actualizar tracks para persistencia temporal
                tracked = self._update_tracks(person_boxes)
            else:
                # Usar cajas del último frame procesado (suavizar)
                # Intentar mantener tracks cuando no hay detecciones nuevas
                person_boxes = self.last_person_boxes
                tracked = self._update_tracks(person_boxes)

            current_counts = {str(i): 0 for i in range(1, 7)}

            # Si tenemos tracking, usamos los tracks; si no, usamos detecciones sueltas
            if tracked:
                for track_id, (x1, y1, x2, y2) in tracked:
                    feet_x = int((x1 + x2) / 2)
                    feet_y = y2

                    in_any_roi = False
                    for caja_id, (x_roi, y_roi, w_roi, h_roi) in self.rois.items():
                        roi_polygon = self._build_roi_polygon(caja_id)
                        if self._point_in_roi((feet_x, feet_y), roi_polygon):
                            current_counts[caja_id] += 1
                            in_any_roi = True
                            break

                    color = (0, 255, 0) if in_any_roi else (200, 200, 200)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(frame, f"ID:{track_id}", (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            else:
                for (x1, y1, x2, y2) in person_boxes:
                    feet_x = int((x1 + x2) / 2)
                    feet_y = y2

                    in_any_roi = False
                    for caja_id, (x_roi, y_roi, w_roi, h_roi) in self.rois.items():
                        roi_polygon = self._build_roi_polygon(caja_id)
                        if self._point_in_roi((feet_x, feet_y), roi_polygon):
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
            roi_polygon = self._build_roi_polygon(caja_id)
            cv2.polylines(frame, [roi_polygon], isClosed=True, color=(255, 0, 0), thickness=2)
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
