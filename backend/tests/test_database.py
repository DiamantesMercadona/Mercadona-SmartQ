# Importaciones
import unittest
from database import DatabaseMSQ, _UNSET

# Define la clase de pruebas unitarias para DatabaseMSQ
class TestDatabaseMSQ(unittest.TestCase):

    # Configuración inicial antes de cada test (se usa una base de datos en memoria)
    def setUp(self):
        self.db = DatabaseMSQ(db_path=":memory:")

    # Cierra la conexión después de cada test
    def tearDown(self):
        self.db.close()

    # --- 1. INSTANTÁNEAS ---
    def test_instantaneas(self):

        estado = {
            "1": ["sinCarro", "conCarro"],
            "2": ["sinCarro"]
        }
        snap_id = self.db.registrar_instantanea(estado_cajas=estado)
        self.assertIsNotNone(snap_id)
        
        snapshots = self.db.obtener_instantaneas(limite=5)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["estado_cajas"], estado)

    # --- 2. CAJAS ---
    def test_cajas(self):

        # Crea un empleado para usar su id como foránea
        emp_id = self.db.crear_empleado("Tester", "App")
        
        # Crear
        self.db.crear_caja(id="Caja_Test", estado="cerrada", id_empleado=None)
        
        # Obtener
        caja = self.db.obtener_caja(id="Caja_Test")
        self.assertIsNotNone(caja)
        self.assertEqual(caja["estado"], "cerrada")
        self.assertIsNone(caja["id_empleado"])
        
        # Actualizar estado y empleado
        self.db.actualizar_caja(id="Caja_Test", estado="abierta", id_empleado=emp_id)
        caja_actualizada = self.db.obtener_caja(id="Caja_Test")
        self.assertEqual(caja_actualizada["estado"], "abierta")
        self.assertEqual(caja_actualizada["id_empleado"], emp_id)
        
        # Actualizar con desasignación
        self.db.actualizar_caja(id="Caja_Test", id_empleado=None) # Set None explícitamente
        caja_desasignada = self.db.obtener_caja(id="Caja_Test")
        self.assertIsNone(caja_desasignada["id_empleado"])
        self.assertEqual(caja_desasignada["estado"], "abierta") # Queda igual

        # Obtener_cajas
        todas = self.db.obtener_cajas()
        self.assertTrue(len(todas) > 0)
        
        # Eliminar
        exito = self.db.eliminar_caja("Caja_Test")
        self.assertTrue(exito)
        self.assertIsNone(self.db.obtener_caja("Caja_Test"))

    # --- 3. MÉTRICAS ---
    def test_metricas(self):

        # Crear la caja foránea primero
        self.db.crear_caja(id="Caja_M", estado="abierta")
        
        self.db.registrar_metrica(tiempo_medio_espera_segundos=10.5, fuente="test")
        self.db.registrar_metrica(tiempo_medio_espera_segundos=15.0, id_caja="Caja_M", fuente="test")
        
        # Las dos métricas existen independientemente
        todas = self.db.obtener_metricas()
        self.assertEqual(len(todas), 2)
        
        # Recuperar global vs local
        locales = self.db.obtener_metricas(id_caja="Caja_M")
        self.assertEqual(len(locales), 1)
        self.assertEqual(locales[0]["tiempo_medio_espera_segundos"], 15.0)

    # --- 4. EMPLEADOS ---
    def test_empleados(self):

        emp_id = self.db.crear_empleado(nombre="Ana", apellidos="García", id_pulsera="p-123")
        self.assertIsNotNone(emp_id)
        
        # Obtener
        emp = self.db.obtener_empleado(emp_id)
        self.assertIsNotNone(emp)
        self.assertEqual(emp["nombre"], "Ana")
        self.assertEqual(emp["id_pulsera"], "p-123")
        self.assertTrue(emp["activo"]) # Por defecto
        
        # Actualizar booleanos
        self.db.actualizar_empleado(id_empleado=emp_id, activo=False)
        emp_inactivo = self.db.obtener_empleado(emp_id)
        self.assertFalse(emp_inactivo["activo"])
        
        # Listar activos vs inactivos
        activos = self.db.listar_empleados(activos=True)
        self.assertEqual(len([e for e in activos if e["id"] == emp_id]), 0)
        
        todos = self.db.listar_empleados(activos=False)
        self.assertEqual(len([e for e in todos if e["id"] == emp_id]), 1)
        
        # Eliminar
        exito = self.db.eliminar_empleado(emp_id)
        self.assertTrue(exito)
        self.assertIsNone(self.db.obtener_empleado(emp_id))



    # --- 6. TURNOS ---
    def test_turnos(self):

        # Verificar Inicialización (Semana Completa = 7 dias * 2 turnos = 14 turnos vacios)
        semana = self.db.obtener_turnos()
        self.assertEqual(len(semana), 14)
        for t in semana:
            self.assertEqual(t["orden"], [])
            
        # Insertar Modificación con UPSERT en Batch list
        self.db.actualizar_turnos([
            {"dia_semana": "lunes", "turno": "mañana", "orden": [{"id": 3}, {"id": 10}]},
            {"dia_semana": "domingo", "turno": "tarde", "orden": []}
        ])
        
        lunes = self.db.obtener_turnos(dia_semana="lunes", turno="mañana")
        self.assertEqual(len(lunes), 1)
        self.assertEqual(lunes[0]["orden"], [{"id": 3}, {"id": 10}])

if __name__ == "__main__":
    unittest.main()
