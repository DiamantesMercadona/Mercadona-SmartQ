import cv2
import numpy as np
from ultralytics import YOLO
from typing import Union, List, Tuple
import sqlite3
from datetime import datetime
import os
from scipy.cluster.hierarchy import fclusterdata
import time

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
        self.default_video = os.path.join(self.base_dir, "resources", "walking_demo.mp4")

        # Fuente de video
        if source is None:
            source = self.default_video
        elif isinstance(source, str) and not os.path.isabs(source):
            source = os.path.join(self.base_dir, source)

        self.cap = cv2.VideoCapture(source)

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

        # Región de interés: (x_inicio, y_inicio, ancho, alto)
        self.roi_coords = (200, 250, 200, 500)
        self.count = 0

        # Conexión a la base de datos
        self.conn = sqlite3.connect("msq.db")
        self.cursor = self.conn.cursor()

        # Crear tabla si no existe
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS detecciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                personas_en_cola INTEGER NOT NULL,
                caja_saturada INTEGER NOT NULL
            );
        """)
        self.conn.commit()

    def guardar_evento(self, personas: int, saturada: int):
        """
        Guarda un evento de detección en la base de datos.
        """
        self.cursor.execute("""
            INSERT INTO detecciones (timestamp, personas_en_cola, caja_saturada)
            VALUES (?, ?, ?)
        """, (datetime.now().isoformat(), personas, saturada))
        self.conn.commit()

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

            current_count = 0
            x_roi, y_roi, w_roi, h_roi = self.roi_coords

            for (x1, y1, x2, y2) in person_boxes:
                feet_x = int((x1 + x2) / 2)
                feet_y = y2

                is_in_queue = (x_roi < feet_x < x_roi + w_roi and 
                               y_roi < feet_y < y_roi + h_roi)

                color = (0, 255, 0) if is_in_queue else (200, 200, 200)
                if is_in_queue:
                    current_count += 1

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            self.count = current_count
            caja_saturada = 1 if self.count >= 4 else 0

            # Guardar en la base de datos (solo en frames procesados)
            if self.frame_count % self.frame_skip == 0:
                self.guardar_evento(self.count, caja_saturada)

            # Dibujar interfaz
            self._draw_interface(frame, x_roi, y_roi, w_roi, h_roi)
            cv2.imshow('MSQ Engine', frame)

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

    def _draw_interface(self, frame: np.ndarray, x: int, y: int, w: int, h: int) -> None:
        """
        Dibuja la interfaz de usuario sobre el frame.
        """
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        cv2.rectangle(frame, (15, 10), (475, 80), (0, 0, 0), -1)
        cv2.putText(frame, f"MSQ - Personas en cola: {self.count}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(frame, f"FPS: {self.fps}", (20, 75), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    def _terminate(self) -> None:
        """
        Libera hardware y cierra la base de datos.
        """
        self.cap.release()
        cv2.destroyAllWindows()
        self.conn.close()

if __name__ == "__main__":
    engine = VisionEngine()
    engine.process()
