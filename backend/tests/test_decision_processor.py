import os
import sys
import tempfile
import unittest
from pathlib import Path

# Asegurar que el directorio backend esté en sys.path para poder realizar las importaciones locales
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import CONFIG
from database import DatabaseMSQ
from decision_processor import HistorialMetricas, ProcesadorDecisionesMSQ

# ------------------------------------------------------------------
# Test de la lógica de decisiones (SLA, EMA y Cooldowns)
# ------------------------------------------------------------------

class TestDecisionProcessor(unittest.TestCase):
    """Batería de pruebas unitarias para el motor de decisiones de MSQ.

    Cubre la lógica del historial TEE, la suavización exponencial EMA,
    la detección de desequilibrio de carga y la sincronización con la BD.
    """

    def setUp(self):
        # Usar un archivo de base de datos local estático para aislar las pruebas de la base real
        self.db_path = os.path.abspath("test_decision_msq.db")
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass
        self.original_db_path = CONFIG["DATABASE"]["db_path"]
        CONFIG["DATABASE"]["db_path"] = self.db_path

        # Inicializar base de datos limpia de pruebas
        self.db = DatabaseMSQ(db_path=self.db_path)

    def tearDown(self):
        # Cerrar y limpiar la base de datos local
        self.db.close()
        CONFIG["DATABASE"]["db_path"] = self.original_db_path
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass


    def test_historial_tee_global_and_box_averages(self):
        """Verifica que el registrador e historial TEE calcule de forma correcta las medias globales y por caja."""
        historial = HistorialMetricas(ventana=5)

        # Registrar métricas globales y validar la media
        historial.registrar_global(100.0)
        historial.registrar_global(200.0)
        self.assertEqual(historial.media_global(), 150.0)

        # Registrar métricas por caja y validar medias locales
        historial.registrar_caja("1", 50.0)
        historial.registrar_caja("1", 150.0)
        historial.registrar_caja("2", 300.0)
        self.assertEqual(historial.media_caja("1"), 100.0)
        self.assertEqual(historial.media_caja("2"), 300.0)

    def test_historial_tee_trends(self):
        """Verifica que la detección de tendencias asigne la etiqueta correcta según el cambio de valores."""
        historial = HistorialMetricas(ventana=10)

        # Con menos de 6 lecturas la tendencia debe ser estable
        self.assertEqual(historial.tendencia_global(), "estable")
        historial.registrar_global(10.0)
        historial.registrar_global(12.0)
        historial.registrar_global(15.0)
        historial.registrar_global(20.0)
        historial.registrar_global(25.0)
        self.assertEqual(historial.tendencia_global(), "estable")

        # 6 lecturas crecientes -> subiendo
        historial.registrar_global(30.0)
        self.assertEqual(historial.tendencia_global(), "subiendo")

        # Lecturas decrecientes -> bajando
        historial = HistorialMetricas(ventana=10)
        historial.registrar_global(30.0)
        historial.registrar_global(25.0)
        historial.registrar_global(20.0)
        historial.registrar_global(15.0)
        historial.registrar_global(12.0)
        historial.registrar_global(10.0)
        self.assertEqual(historial.tendencia_global(), "bajando")

    def test_ema_smoothing_logic(self):
        """Verifica que la suavización exponencial EMA aplique la fórmula matemática de forma precisa."""
        procesador = ProcesadorDecisionesMSQ()
        procesador.EMA_ALPHA = 0.2

        # Primera lectura inicializa el valor directamente
        valor_1 = procesador._actualizar_ema(100.0)
        self.assertEqual(valor_1, 100.0)

        # Segunda lectura aplica la fórmula: (0.2 * 200) + (0.8 * 100) = 40 + 80 = 120
        valor_2 = procesador._actualizar_ema(200.0)
        self.assertEqual(valor_2, 120.0)

    def test_detectar_desequilibrio_carga(self):
        """Verifica que el algoritmo alerte de forma correcta cuando una caja supera la media en más de un 50%."""
        procesador = ProcesadorDecisionesMSQ()
        procesador.cajas_abiertas = 3

        # Forzar un estado en el historial en memoria
        # Caja 1: media de 100s, Caja 2: media de 100s, Caja 3: media de 220s (Media del resto = 100s, 220s es > 150%)
        procesador.historial.registrar_caja("1", 100.0)
        procesador.historial.registrar_caja("2", 100.0)
        procesador.historial.registrar_caja("3", 220.0)

        alertas = procesador._detectar_desequilibrio()
        self.assertEqual(len(alertas), 1)
        self.assertIn("caja 3", alertas[0].lower())
        self.assertIn("cola", alertas[0].lower())

    def test_sincronizar_cajas_con_la_base_de_datos(self):
        """Verifica que el estado de las cajas se persista y actualice de forma síncrona según la decisión del motor."""
        procesador = ProcesadorDecisionesMSQ()
        procesador.cajas_totales = 6
        procesador.cajas_abiertas = 2

        # Ejecutar sincronización (debe abrir cajas 1 y 2, y cerrar las demás)
        procesador.sincronizar_cajas_db()

        with DatabaseMSQ() as db:
            caja_1 = db.obtener_caja("1")
            caja_3 = db.obtener_caja("3")

            self.assertEqual(caja_1["estado"], "abierta")
            self.assertEqual(caja_3["estado"], "cerrada")


if __name__ == "__main__":
    unittest.main()

