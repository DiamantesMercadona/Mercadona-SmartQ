import cv2
import numpy as np
from ultralytics import YOLO
from typing import Union
import sqlite3
from datetime import datetime

class MSQEngine:
    """
    Motor de visión artificial para Mercadona SmartQ (MSQ).
    Procesa flujo de video para la detección de personas y 
    gestiona colas mediante YOLOv8 y análisis espacial.
    """

    def __init__(self, source: Union[int, str] = 0):
        """
        Inicializa los recursos del motor.
        """
        # Fuente de video
        self.cap = cv2.VideoCapture(source)

        # Modelo YOLOv8
        self.model = YOLO('yolov8n.pt')

        # Región de interés
        self.roi_coords = (100, 100, 300, 400)
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
        """Guarda un evento de detección en la base de datos."""
        self.cursor.execute("""
            INSERT INTO detecciones (timestamp, personas_en_cola, caja_saturada)
            VALUES (?, ?, ?)
        """, (datetime.now().isoformat(), personas, saturada))

        self.conn.commit()

    def process(self) -> None:
        """
        Bucle principal de inferencia.
        """
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            results = self.model(frame, classes=0, verbose=False)

            current_count = 0
            x_roi, y_roi, w_roi, h_roi = self.roi_coords

            for r in results:
                for box in r.boxes:
                    coords = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = map(int, coords)

                    feet_x = int((x1 + x2) / 2)
                    feet_y = y2

                    is_in_queue = (x_roi < feet_x < x_roi + w_roi and 
                                   y_roi < feet_y < y_roi + h_roi)

                    if is_in_queue:
                        current_count += 1
                        color = (0, 255, 0)
                    else:
                        color = (200, 200, 200)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            self.count = current_count

            # Determinar si la cola está saturada
            caja_saturada = 1 if self.count >= 4 else 0

            # Guardar en la base de datos
            self.guardar_evento(self.count, caja_saturada)

            # Dibujar interfaz
            self._draw_interface(frame, x_roi, y_roi, w_roi, h_roi)

            cv2.imshow('MSQ Engine', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self._terminate()

    def _draw_interface(self, frame: np.ndarray, x: int, y: int, w: int, h: int) -> None:
        """Dibuja la interfaz de usuario técnica sobre el frame."""
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

        cv2.rectangle(frame, (15, 10), (475, 55), (0, 0, 0), -1)
        cv2.putText(frame, f"MSQ - Personas en cola: {self.count}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    def _terminate(self) -> None:
        """Libera hardware y cierra la base de datos."""
        self.cap.release()
        cv2.destroyAllWindows()
        self.conn.close()
if __name__ == "__main__":
    engine = MSQEngine()
    engine.process()
