import sqlite3
import time
import random

class SimuladorCamaraMSQ:
    def __init__(self, db_name='metricas_supermercado.db'):
        self.db_name = db_name
        self.zona = "Caja_Principal_Simulada"
        self._init_db()

    def _init_db(self):
        """Recrea la misma estructura de tabla que usará la cámara real."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registro_colas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                zona TEXT,
                personas_en_cola INTEGER
            )
        ''')
        conn.commit()
        conn.close()
        print("✅ Base de datos inicializada/verificada por el simulador.")

    def _insertar_dato(self, personas: int):
        """Inserta el dato simulado en SQLite."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO registro_colas (zona, personas_en_cola) 
            VALUES (?, ?)
        ''', (self.zona, personas))
        conn.commit()
        conn.close()

    def ejecutar(self, intervalo_segundos=5):
        print(f"🎥 Simulador de Cámara Avanzado Iniciado...")
        personas = 2 
        ciclo = 0

        try:
            while True:
                ciclo += 1
                
                # Cada 15 ciclos, simulamos un "AUTOBÚS" (Pico masivo de gente)
                if ciclo % 15 == 0:
                    print("\n⚠️ ¡ATENCIÓN! Ha llegado mucha gente de golpe al súper ⚠️")
                    fluctuacion = random.randint(5, 8)
                else:
                    # Comportamiento normal
                    fluctuacion = random.randint(-2, 2)
                
                personas = max(0, min(20, personas + fluctuacion))
                
                print(f"[{time.strftime('%H:%M:%S')}] 🧍 Detectadas {personas} personas en cámara.")
                self._insertar_dato(personas)
                time.sleep(intervalo_segundos)
                
        except KeyboardInterrupt:
            print("\n🛑 Simulador detenido.")

if __name__ == "__main__":
    simulador = SimuladorCamaraMSQ()
    # Usamos 10 segundos para que puedas hacer pruebas rápido sin esperar tanto.
    # En producción (la cámara real) esto será más alto.
    simulador.ejecutar(intervalo_segundos=3)