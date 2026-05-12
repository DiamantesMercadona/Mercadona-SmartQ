import sqlite3
import time
import random
from config import CONFIG

class SimuladorRealista:
    def __init__(self, db_name=CONFIG["DATABASE"]["db_path"]):
        self.db_name = db_name
        self.zona = "Caja_Principal"
        self.cola_espera = [] 
        self.siguiente_id = 1
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DROP TABLE IF EXISTS registro_colas')
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
        print("[SIMULADOR] Base de datos inicializada (FIFO con Oleadas).")

    def _insertar_dato(self, personas: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO registro_colas (zona, personas_en_cola) 
            VALUES (?, ?)
        ''', (self.zona, personas))
        conn.commit()
        conn.close()

    def ejecutar(self, intervalo_ciclo=2):
        print("[SIMULADOR] Iniciando. Alternando Hora Punta y Tranquila cada 90s.\n")
        
        ultimo_tiempo = time.time()
        ciclos_totales = 0
        hora_punta = False
        
        try:
            while True:
                tiempo_actual = time.time()
                delta_tiempo = tiempo_actual - ultimo_tiempo
                ultimo_tiempo = tiempo_actual
                hora = time.strftime('%H:%M:%S')
                ciclos_totales += 1
                
                # --- SISTEMA DE OLEADAS ---
                # Cambiamos de fase cada 45 ciclos (90 segundos reales)
                if ciclos_totales % 45 == 0:
                    hora_punta = not hora_punta
                    if hora_punta:
                        print(f"\n{'='*65}\n[{hora}] [ALERTA] COMIENZA LA HORA PUNTA\n{'='*65}")
                    else:
                        print(f"\n{'='*65}\n[{hora}] [ALERTA] COMIENZA LA HORA TRANQUILA\n{'='*65}")
                
                # 1. ATENDER A LOS CLIENTES
                # Simulamos que el supermercado responde abriendo hasta 4 cajas físicas 
                # para poder drenar el atasco cuando hay mucha gente.
                clientes_atendidos = min(4, len(self.cola_espera))
                
                for i in range(clientes_atendidos):
                    self.cola_espera[i]['tiempo_restante'] -= delta_tiempo
                
                # 2. SALIDAS (Limpiar la cola)
                clientes_restantes = []
                for cliente in self.cola_espera:
                    if cliente['tiempo_restante'] <= 0:
                        print(f"[{hora}] [SALIDA] Cliente {cliente['id']} ({cliente['tipo']}) ha pagado.")
                    else:
                        clientes_restantes.append(cliente)
                        
                self.cola_espera = clientes_restantes

                # 3. LLEGADAS (Generar trafico variable)
                # 35% de prob. en hora punta, solo 2% en hora tranquila
                prob_llegada = 0.35 if hora_punta else 0.02
                
                if random.random() < prob_llegada: 
                    # Tiempos ligeramente reducidos para no alargar la prueba
                    if random.random() < 0.80:
                        tipo = "Cesta"
                        tiempo_base = random.uniform(20, 40)
                    else:
                        tipo = "Carro"
                        tiempo_base = random.uniform(70, 110)
                        
                    nuevo_cliente = {
                        'id': self.siguiente_id,
                        'tipo': tipo,
                        'tiempo_restante': tiempo_base
                    }
                    self.cola_espera.append(nuevo_cliente)
                    print(f"[{hora}] [LLEGADA] Cliente {self.siguiente_id} entra con {tipo} ({int(tiempo_base)}s de caja).")
                    self.siguiente_id += 1

                # 4. GUARDAR ESTADO PARA EL PROCESADOR
                total_personas = len(self.cola_espera)
                self._insertar_dato(total_personas)
                
                print(f"[{hora}] [ESTADO] Personas en linea de caja: {total_personas}")
                print("-" * 65)
                
                time.sleep(intervalo_ciclo)

        except KeyboardInterrupt:
            print("\n[SIMULADOR] Simulacion detenida.")

if __name__ == "__main__":
    simulador = SimuladorRealista()
    simulador.ejecutar(intervalo_ciclo=2)