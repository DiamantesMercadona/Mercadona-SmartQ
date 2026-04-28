import cv2
import numpy as np
from ultralytics import YOLO
from typing import Union

class MSQEngine:
    """
    Motor de visión artificial para Mercadona SmartQ (MSQ).
    
    Procesa flujo de video para la detección de personas y 
    gestiona colas mediante YOLOv8 y análisis espacial.
    """

    def __init__(self, source: Union[int, str] = 0):
        """
        Inicializa los recursos del motor.
        
        Args:
            source: Origen del video (ID de cámara o ruta de archivo/stream).
        """
        # Establece la conexión con la fuente de video
        self.cap = cv2.VideoCapture(source)
        
        # Carga el modelo YOLOv8 Nano optimizado para CPU
        self.model = YOLO('yolov8n.pt') 
        
        # Define las coordenadas de la Región de Interés (ROI) [x, y, w, h]
        self.roi_coords = (100, 100, 300, 400)
        self.count = 0

    def process(self) -> None:
        """
        Ejecuta el bucle principal de inferencia y renderizado.
        """
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            # Realiza la detección selectiva (clase 0: persona)
            results = self.model(frame, classes=0, verbose=False)
            
            current_count = 0
            x_roi, y_roi, w_roi, h_roi = self.roi_coords

            for r in results:
                for box in r.boxes:
                    # Extrae las coordenadas y las convierte a enteros para OpenCV
                    coords = box.xyxy[0].cpu().numpy()
                    x1, y1, x2, y2 = map(int, coords)
                    
                    # Calcula el punto base (pies) para validar la posición
                    feet_x = int((x1 + x2) / 2)
                    feet_y = y2

                    # Comprueba la pertenencia a la zona de cola
                    is_in_queue = (x_roi < feet_x < x_roi + w_roi and 
                                   y_roi < feet_y < y_roi + h_roi)

                    if is_in_queue:
                        current_count += 1
                        color = (0, 255, 0)  # Verde: Activo en cola
                    else:
                        color = (200, 200, 200)  # Gris: Fuera de zona

                    # Dibuja el cuadro delimitador del sujeto detectado
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            self.count = current_count

            # Renderiza elementos visuales y métricas de saturación
            self._draw_interface(frame, x_roi, y_roi, w_roi, h_roi)

            # Muestra la ventana de monitorización
            cv2.imshow('MSQ Engine', frame)

            # Interrumpe el proceso si se detecta la tecla 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self._terminate()

    def _draw_interface(self, frame: np.ndarray, x: int, y: int, w: int, h: int) -> None:
        """Dibuja la interfaz de usuario técnica sobre el frame."""
        # Dibuja los límites de la zona de control
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
        
        # Renderiza el panel de información superior
        cv2.rectangle(frame, (15, 10), (475, 55), (0, 0, 0), -1)
        cv2.putText(frame, f"MSQ - Personas en cola: {self.count}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    def _terminate(self) -> None:
        """Libera hardware y destruye ventanas activas."""
        self.cap.release()
        cv2.destroyAllWindows()