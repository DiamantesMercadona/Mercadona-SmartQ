import os
import sys
import tempfile
import unittest
from pathlib import Path

# Asegurarse de que el directorio backend esté en sys.path para importar módulos locales.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import CONFIG
from database import DatabaseMSQ
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from api.get_endpoints import router as get_router
except ImportError:
    from .api.get_endpoints import router as get_router


class TestApiGetEndpoints(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test_msq.db")
        self.original_db_path = CONFIG["DATABASE"]["db_path"]
        CONFIG["DATABASE"]["db_path"] = self.db_path

        self.db = DatabaseMSQ(db_path=self.db_path)

        self.empleado_activo_id = self.db.crear_empleado("Ana", "García", "p-123")
        self.empleado_inactivo_id = self.db.crear_empleado("Luis", "Pérez", "p-456")
        self.db.actualizar_empleado(self.empleado_inactivo_id, activo=False)

        self.db.crear_caja(id="1", estado="abierta", id_empleado=self.empleado_activo_id)
        self.db.crear_caja(id="2", estado="cerrada", id_empleado=None)

        self.estado_instantanea = {
            "1": ["sinCarro", "conCarro"],
            "2": ["sinCarro"],
        }
        self.db.registrar_instantanea(estado_cajas=self.estado_instantanea)

        self.db.registrar_metrica(tiempo_medio_espera_segundos=7.25, fuente="test")
        self.db.registrar_metrica(tiempo_medio_espera_segundos=12.5, id_caja="1", fuente="test")

        self.app = FastAPI()
        self.app.include_router(get_router, prefix="/api/v1")
        self.client = TestClient(self.app)

    def tearDown(self):
        self.db.close()
        CONFIG["DATABASE"]["db_path"] = self.original_db_path
        self.tempdir.cleanup()

    def test_get_queues(self):
        response = self.client.get("/api/v1/queues")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("queues", payload)
        self.assertEqual(len(payload["queues"]), 2)

        queue_1 = next(q for q in payload["queues"] if q["id"] == "1")
        queue_2 = next(q for q in payload["queues"] if q["id"] == "2")

        self.assertEqual(queue_1["status"], "abierta")
        self.assertEqual(queue_1["length"], 2)
        self.assertEqual(queue_2["status"], "cerrada")
        self.assertEqual(queue_2["length"], 1)

    def test_get_queue_by_id(self):
        response = self.client.get("/api/v1/queues/1")
        self.assertEqual(response.status_code, 200)
        queue = response.json()
        self.assertEqual(queue["id"], "1")
        self.assertEqual(queue["status"], "abierta")
        self.assertEqual(queue["length"], 2)

        response_not_found = self.client.get("/api/v1/queues/999")
        self.assertEqual(response_not_found.status_code, 404)

    def test_get_cajas(self):
        response = self.client.get("/api/v1/cajas")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("cajas", payload)
        self.assertEqual(len(payload["cajas"]), 2)

        ids = {c["id"] for c in payload["cajas"]}
        self.assertSetEqual(ids, {"1", "2"})

    def test_get_caja_by_id(self):
        response = self.client.get("/api/v1/cajas/1")
        self.assertEqual(response.status_code, 200)
        caja = response.json()
        self.assertEqual(caja["id"], "1")
        self.assertEqual(caja["estado"], "abierta")
        self.assertEqual(caja["id_empleado"], self.empleado_activo_id)

        response_not_found = self.client.get("/api/v1/cajas/missing")
        self.assertEqual(response_not_found.status_code, 404)

    def test_get_instantaneas(self):
        response = self.client.get("/api/v1/instantaneas?limite=5")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("instantaneas", payload)
        self.assertEqual(len(payload["instantaneas"]), 1)
        self.assertEqual(payload["instantaneas"][0]["estado_cajas"], self.estado_instantanea)

    def test_get_metricas(self):
        response = self.client.get("/api/v1/metricas")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("metricas", payload)
        self.assertEqual(len(payload["metricas"]), 2)

        response_global = self.client.get("/api/v1/metricas?solo_global=true")
        self.assertEqual(response_global.status_code, 200)
        payload_global = response_global.json()
        self.assertEqual(len(payload_global["metricas"]), 1)
        self.assertIsNone(payload_global["metricas"][0]["id_caja"])

    def test_get_empleados(self):
        response_all = self.client.get("/api/v1/empleados?activos=false")
        self.assertEqual(response_all.status_code, 200)
        payload_all = response_all.json()
        self.assertEqual(len(payload_all["empleados"]), 2)

        response_active = self.client.get("/api/v1/empleados?activos=true")
        self.assertEqual(response_active.status_code, 200)
        payload_active = response_active.json()
        self.assertEqual(len(payload_active["empleados"]), 1)
        self.assertEqual(payload_active["empleados"][0]["id"], self.empleado_activo_id)

    def test_get_empleado_by_id(self):
        response = self.client.get(f"/api/v1/empleados/{self.empleado_activo_id}")
        self.assertEqual(response.status_code, 200)
        empleado = response.json()
        self.assertEqual(empleado["nombre"], "Ana")
        self.assertEqual(empleado["apellidos"], "García")

        response_not_found = self.client.get("/api/v1/empleados/9999")
        self.assertEqual(response_not_found.status_code, 404)

    def test_get_turnos(self):
        response = self.client.get("/api/v1/turnos")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("turnos", payload)
        self.assertEqual(len(payload["turnos"]), 14)

        response_filtered = self.client.get("/api/v1/turnos?dia_semana=lunes&turno=mañana")
        self.assertEqual(response_filtered.status_code, 200)
        payload_filtered = response_filtered.json()
        self.assertEqual(len(payload_filtered["turnos"]), 1)
        turno = payload_filtered["turnos"][0]
        self.assertEqual(turno["dia_semana"], "lunes")
        self.assertEqual(turno["turno"], "mañana")
        self.assertEqual(turno["orden"], [])


if __name__ == "__main__":
    unittest.main()
