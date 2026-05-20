# Importaciones
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from vision_engine import VisionEngine


# Define la clase de pruebas unitarias para el motor de visión (VisionEngine)
class TestVisionEngine(unittest.TestCase):

    # Configuración inicial antes de cada caso de prueba, aplicando mocks para aislar el entorno
    def setUp(self):
        # Parchear el cargador del modelo de Deep Learning YOLOv8
        self.yolo_patcher = patch("vision_engine.YOLO")
        self.mock_yolo = self.yolo_patcher.start()

        # Parchear el controlador de captura de vídeo de OpenCV
        self.cap_patcher = patch("vision_engine.cv2.VideoCapture")
        self.mock_cap = self.cap_patcher.start()

        # Simular un flujo de vídeo de 1280 píxeles de anchura horizontal
        self.cap_instance = self.mock_cap.return_value
        self.cap_instance.get.return_value = 1280.0
        self.cap_instance.isOpened.return_value = True

        # Parchear la base de datos centralizada
        self.db_patcher = patch("vision_engine.DatabaseMSQ")
        self.mock_db = self.db_patcher.start()

        # Parchear el cargador de ventanas OpenCV
        self.named_window_patcher = patch("vision_engine.cv2.namedWindow")
        self.mock_named_window = self.named_window_patcher.start()

        # Instanciar el motor de visión bajo prueba de forma aislada
        self.engine = VisionEngine()

    # Libera los mocks y detiene los servicios simulados tras cada prueba
    def tearDown(self):
        self.yolo_patcher.stop()
        self.cap_patcher.stop()
        self.db_patcher.stop()
        self.named_window_patcher.stop()
        # Cerrar el motor y liberar recursos
        self.engine._terminate()

    # --- 1. CICLO DE VIDA Y CONTEXT MANAGER ---
    def test_ciclo_vida_y_context_manager(self):
        # Verificar inicialización básica de variables y estados por defecto
        self.assertEqual(self.engine.roi_left_margin, 200)
        self.assertEqual(self.engine.roi_right_margin, 200)
        self.assertEqual(self.engine.roi_top_expansion, -20)
        self.assertEqual(self.engine.roi_bottom_expansion, 70)
        self.assertEqual(self.engine.roi_global_expansion, 0)
        self.assertEqual(self.engine.roi_offset_x, 0)
        self.assertEqual(self.engine.roi_offset_y, 0)

        # Probar el soporte para gestor de contexto (Context Manager)
        with VisionEngine() as context_engine:
            self.assertIsInstance(context_engine, VisionEngine)

    # --- 2. CÁLCULOS GEOMÉTRICOS DE LAS ROIs ---
    def test_calculos_geometricos_rois(self):
        # 1. Caso base de coordenadas (Caja 1: extremo izquierdo)
        roi_polygon_base = self.engine._build_roi_polygon("1")
        # El lado superior debe ser menor en 20px (roi_top_expansion = -20)
        # El lado inferior debe expandirse en 70px (roi_bottom_expansion = 70) y desplazarse 140px a la izquierda
        self.assertEqual(roi_polygon_base.shape, (4, 2))

        # 2. Comprobar efecto de desplazamientos en ejes X e Y (Offsets)
        self.engine.roi_offset_x = 50
        self.engine.roi_offset_y = -30
        roi_polygon_offset = self.engine._build_roi_polygon("1")

        # Comprobar que los cuatro vértices del polígono se desplazaron exactamente 50 en X y -30 en Y
        for i in range(4):
            self.assertEqual(roi_polygon_offset[i][0] - roi_polygon_base[i][0], 50)
            self.assertEqual(roi_polygon_offset[i][1] - roi_polygon_base[i][1], -30)

        # 3. Comprobar efecto de la separación horizontal (Margin/Interlineado)
        self.engine.roi_offset_x = 0
        self.engine.roi_offset_y = 0
        roi_1_base = self.engine._build_roi_polygon("1")
        roi_2_base = self.engine._build_roi_polygon("2")

        # Cambiar el interlineado a 25px
        self.engine.roi_margin_between = 25
        roi_1_spacing = self.engine._build_roi_polygon("1")
        roi_2_spacing = self.engine._build_roi_polygon("2")

        # El ancho de la ROI debería ser constante, pero su punto de inicio cambia por la holgura acumulativa
        self.assertEqual(roi_1_spacing[0][0], roi_1_base[0][0])  # Caja 1 inicia en la misma base izquierda
        # Caja 2 debe desplazarse proporcionalmente al incremento de interlineado (de 10px a 25px -> +15px)
        self.assertEqual(roi_2_spacing[0][0] - roi_2_base[0][0], 15)

    # --- 3. EVALUACIÓN DE PUNTOS EN ROI (PERMANENCIA) ---
    def test_punto_dentro_fuera_roi(self):
        # Crear un polígono simple de forma rectangular
        # [ [0,0], [100, 0], [100, 100], [0, 100] ]
        polygon = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.int32)

        # Punto interior (centro)
        self.assertTrue(self.engine._point_in_roi((50, 50), polygon))

        # Punto exterior (fuera de límites)
        self.assertFalse(self.engine._point_in_roi((150, 50), polygon))

    # --- 4. SEPARACIÓN DE CAJAS SOLAPADAS (CLUSTERING) ---
    def test_separacion_cajas_solapadas(self):
        # Dos cajas delimitadoras muy cercanas (centros separados por menos de 40px)
        caja_grande = (10, 10, 50, 50)  # Superficie = 1600 px^2
        caja_pequena = (12, 12, 30, 30)  # Superficie = 324 px^2

        detecciones = [caja_grande, caja_pequena]

        # La heurística de clustering debe agruparlas y dejar únicamente la caja de mayor área
        filtradas = self.engine._separate_overlapping_boxes(detecciones)
        self.assertEqual(len(filtradas), 1)
        self.assertEqual(filtradas[0], caja_grande)

    # --- 5. INTERSECCIÓN SOBRE UNIÓN (IoU) ---
    def test_iou_cajas(self):
        box_a = (0, 0, 10, 10)
        box_b = (5, 0, 15, 10)

        # La intersección es de 5x10 = 50. La unión es 100 + 100 - 50 = 150.
        # IoU esperado: 50 / 150 = 0.3333
        iou_calc = self.engine._iou(box_a, box_b)
        self.assertAlmostEqual(iou_calc, 0.3333333, places=5)

        # Cajas idénticas (IoU = 1.0)
        self.assertEqual(self.engine._iou(box_a, box_a), 1.0)

        # Sin solapamiento (IoU = 0.0)
        box_c = (20, 20, 30, 30)
        self.assertEqual(self.engine._iou(box_a, box_c), 0.0)

    # --- 6. SEGUIMIENTO DE DETECCIONES (TRACKING) ---
    def test_tracking_detecciones(self):
        # Primer frame: una detección única
        det_1 = (10, 10, 40, 80)
        tracks_f1 = self.engine._update_tracks([det_1])

        self.assertEqual(len(tracks_f1), 1)
        track_id, box = tracks_f1[0]
        self.assertEqual(track_id, 1)
        self.assertEqual(box, det_1)

        # Segundo frame: la detección se mueve ligeramente (IoU >= 0.3)
        det_2 = (12, 12, 42, 82)
        tracks_f2 = self.engine._update_tracks([det_2])

        self.assertEqual(len(tracks_f2), 1)
        t_id, t_box = tracks_f2[0]
        # El ID de trayectoria se debe conservar (ID = 1)
        self.assertEqual(t_id, 1)
        self.assertEqual(t_box, det_2)


if __name__ == "__main__":
    unittest.main()
