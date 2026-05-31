import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


# Asegurar que el directorio backend esté en sys.path para poder realizar las importaciones locales
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import CONFIG
from database import DatabaseMSQ
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from api.post_endpoints import router as post_router
except ImportError:
    # pyrefly: ignore [missing-import]
    from .api.post_endpoints import router as post_router

# ------------------------------------------------------------------
# Test de Endpoints de Escritura, Autenticación y Lotes de la API
# ------------------------------------------------------------------

class TestApiPostEndpoints(unittest.TestCase):
    """Batería de pruebas unitarias para los endpoints POST y PATCH de la API.

    Valida la creación y actualización de cajas y empleados, la lógica de autenticación (login)
    y el registro masivo de cuadrantes de turnos (UPSERT).
    """

    def setUp(self):
        # Usar un archivo de base de datos local estático para aislar las pruebas de la base real
        self.db_path = os.path.abspath("test_post_msq.db")
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass
        self.original_db_path = CONFIG["DATABASE"]["db_path"]
        CONFIG["DATABASE"]["db_path"] = self.db_path

        # Inicializar base de datos limpia de pruebas
        self.db = DatabaseMSQ(db_path=self.db_path)

        # Configurar cliente de pruebas de FastAPI
        self.app = FastAPI()
        self.app.include_router(post_router, prefix="/api/v1")
        self.client = TestClient(self.app)



    def tearDown(self):
        # Cerrar y limpiar la base de datos local
        self.db.close()
        CONFIG["DATABASE"]["db_path"] = self.original_db_path
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass



    def test_create_and_patch_cajas(self):
        """Verifica que se puedan crear y modificar propiedades parciales de las cajas en tiempo real."""
        # 1. Crear una nueva caja
        response = self.client.post(
            "/api/v1/cajas",
            json={"id": "3", "estado": "cerrada", "id_empleado": None}
        )
        self.assertEqual(response.status_code, 201)

        # 2. Modificar el estado y asignar un empleado
        # Crear primero el empleado para que sea una clave foránea válida
        emp_id = self.db.crear_empleado("José", "Molina", "p-999")
        
        response_patch = self.client.patch(
            "/api/v1/cajas/3",
            json={"estado": "abierta", "id_empleado": emp_id}
        )
        self.assertEqual(response_patch.status_code, 200)
        
        # Validar en base de datos que se consolidó el cambio
        caja = self.db.obtener_caja("3")
        self.assertEqual(caja["estado"], "abierta")
        self.assertEqual(caja["id_empleado"], emp_id)

    def test_create_and_patch_empleados(self):
        """Verifica la creación y actualización parcial de fichas del personal del supermercado."""
        # 1. Crear un empleado
        response = self.client.post(
            "/api/v1/empleados",
            json={"nombre": "Pedro", "apellidos": "Sanz", "id_pulsera": "p-100"}
        )
        self.assertEqual(response.status_code, 201)
        emp_id = response.json()["empleado"]["id"]

        # 2. Actualizar parcialmente (dar de baja y cambiar pulsera)
        response_patch = self.client.patch(
            f"/api/v1/empleados/{emp_id}",
            json={"id_pulsera": "p-200", "activo": False}
        )
        self.assertEqual(response_patch.status_code, 200)

        # Validar en base de datos
        empleado = self.db.obtener_empleado(emp_id)
        self.assertEqual(empleado["id_pulsera"], "p-200")
        self.assertEqual(empleado["activo"], 0)

    def test_bulk_upsert_turnos(self):
        """Verifica el registro masivo (lote) de la asignación semanal de turnos sin duplicidades."""
        # Configurar un empleado de prueba
        emp_id = self.db.crear_empleado("Laura", "Benítez", "p-789")

        # Intentar el envío masivo de turnos
        response = self.client.post(
            "/api/v1/turnos",
            json=[
                {
                    "dia_semana": "lunes",
                    "turno": "mañana",
                    "orden": [{"id": emp_id}]
                }
            ]
        )
        self.assertEqual(response.status_code, 200)

        # Verificar que el lunes por la mañana tiene ahora asignada a Laura
        turno = self.db.obtener_turnos(dia_semana="lunes", turno="mañana")[0]
        self.assertEqual(turno["orden"], [{"id": emp_id}])

    def test_delete_caja(self):
        """Verifica la eliminación correcta de una caja y el error 404 al intentar borrar una inexistente."""
        # 1. Crear caja para borrar
        self.client.post("/api/v1/cajas", json={"id": "eliminar_caja", "estado": "cerrada"})
        
        # 2. Eliminar caja creada
        response = self.client.delete("/api/v1/cajas/eliminar_caja")
        self.assertEqual(response.status_code, 204)
        
        # 3. Validar eliminación intentando eliminarla de nuevo (debe dar 404)
        response_not_found = self.client.delete("/api/v1/cajas/eliminar_caja")
        self.assertEqual(response_not_found.status_code, 404)

    def test_delete_empleado(self):
        """Verifica la eliminación correcta de un empleado y el error 404 al intentar borrar uno inexistente."""
        # 1. Crear empleado para borrar
        res = self.client.post("/api/v1/empleados", json={"nombre": "Borrar", "apellidos": "Test"})
        emp_id = res.json()["empleado"]["id"]
        
        # 2. Eliminar empleado creado
        response = self.client.delete(f"/api/v1/empleados/{emp_id}")
        self.assertEqual(response.status_code, 204)
        
        # 3. Validar eliminación intentando eliminarlo de nuevo (debe dar 404)
        response_not_found = self.client.delete(f"/api/v1/empleados/{emp_id}")
        self.assertEqual(response_not_found.status_code, 404)



    def test_crear_metrica(self):
        """Verifica el registro de nuevas métricas globales y por caja."""
        # 1. Crear caja requerida para métrica local
        self.client.post("/api/v1/cajas", json={"id": "caja_m", "estado": "abierta"})

        # 2. Crear métrica global
        response_global = self.client.post(
            "/api/v1/metricas",
            json={"tiempo_medio_espera_segundos": 8.5, "fuente": "api_test"}
        )
        self.assertEqual(response_global.status_code, 201)

        # 3. Crear métrica asociada a caja
        response_caja = self.client.post(
            "/api/v1/metricas",
            json={"tiempo_medio_espera_segundos": 14.2, "id_caja": "caja_m", "fuente": "api_test"}
        )
        self.assertEqual(response_caja.status_code, 201)

    def test_crear_instantanea(self):
        """Verifica el correcto almacenamiento de una instantánea del estado de las cajas."""
        response = self.client.post(
            "/api/v1/instantaneas",
            json={
                "estado_cajas": {
                    "1": ["sinCarro", "conCarro"],
                    "2": []
                }
            }
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.json())

    @patch("api.post_endpoints.set_bytes")
    @patch("api.post_endpoints.publish_bytes")
    def test_recibir_evento_pulsera_y_display(self, mock_publish, mock_set):
        """Verifica que los eventos de pulsera y pantalla se gestionen y publiquen correctamente en el broker."""
        mock_set.return_value = True
        mock_publish.return_value = 1

        # 1. Probar evento de pulsera
        response_pulsera = self.client.post(
            "/api/v1/pulsera/evento",
            json={"pulsera_id": "p-100", "evento": "boton_panico"}
        )
        self.assertEqual(response_pulsera.status_code, 200)
        self.assertEqual(response_pulsera.json(), {"status": "ok"})
        mock_set.assert_called()
        mock_publish.assert_called()

        # Resetear mocks
        mock_set.reset_mock()
        mock_publish.reset_mock()

        # 2. Probar evento de display
        response_display = self.client.post(
            "/api/v1/display/evento",
            json={"mensaje": "Caja 3 saturada"}
        )
        self.assertEqual(response_display.status_code, 200)
        self.assertEqual(response_display.json(), {"status": "ok"})
        mock_set.assert_called()
        mock_publish.assert_called()


if __name__ == "__main__":
    unittest.main()
