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
        cursor.execute('DROP TABLE IF EXISTS registro_tiempos')
        
        # NUEVA TABLA: Guardamos Grupos de Cesta y Grupos de Carro
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registro_colas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                zona TEXT,
                grupos_cesta INTEGER,
                grupos_carro INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registro_tiempos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT,
                tiempo_tardado REAL
            )
        ''')
        conn.commit()
        conn.close()

    def _insertar_dato(self, g_cesta: int, g_carro: int):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO registro_colas (zona, grupos_cesta, grupos_carro) 
            VALUES (?, ?, ?)
        ''', (self.zona, g_cesta, g_carro))
        conn.commit()
        conn.close()

        # ---> PEGA ESTA FUNCIÓN AQUÍ <---
    def _insertar_tiempo_real(self, tipo: str, tiempo_tardado: float):
        """Guarda cuánto ha tardado de verdad un cliente para que el procesador aprenda."""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO registro_tiempos (tipo, tiempo_tardado) 
            VALUES (?, ?)
        ''', (tipo, tiempo_tardado))
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
                
                # 2. SALIDAS
                clientes_restantes = []
                for cliente in self.cola_espera:
                    if cliente['tiempo_restante'] <= 0:
                        # CORRECCIÓN 1: El nombre exacto de la función es _insertar_tiempo_real
                        # CORRECCIÓN 2: Le pasamos 'tiempo_total', no 'tiempo_restante'
                        self._insertar_tiempo_real(cliente['tipo'], cliente['tiempo_total'])
                        
                        print(f"[{hora}] [SALIDA] Cliente {cliente['id']} ({cliente['tipo']}) ha pagado en {int(cliente['tiempo_total'])}s.")
                    else:
                        clientes_restantes.append(cliente)
                self.cola_espera = clientes_restantes

                # 3. LLEGADAS (Generar trafico variable)
                prob_llegada = 0.35 if hora_punta else 0.02
                
                if random.random() < prob_llegada: 
                    if random.random() < 0.80:
                        tipo = "Cesta"
                        tiempo_base = random.uniform(20, 40)
                    else:
                        tipo = "Carro"
                        tiempo_base = random.uniform(70, 110)
                        
                    # ¡AQUÍ ESTÁ LA CLAVE! 
                    # Hay que añadir el 'tiempo_total' para que no dé el KeyError al salir
                    nuevo_cliente = {
                        'id': self.siguiente_id,
                        'tipo': tipo,
                        'tiempo_restante': tiempo_base,
                        'tiempo_total': tiempo_base  # <--- ESTA ES LA LÍNEA QUE FALTABA
                    }
                    self.cola_espera.append(nuevo_cliente)
                    print(f"[{hora}] [LLEGADA] Cliente {self.siguiente_id} entra con {tipo} ({int(tiempo_base)}s de caja).")
                    self.siguiente_id += 1

                # 4. GUARDAR ESTADO PARA EL PROCESADOR
                grupos_cesta = sum(1 for c in self.cola_espera if c['tipo'] == 'Cesta')
                grupos_carro = sum(1 for c in self.cola_espera if c['tipo'] == 'Carro')
                total_grupos = grupos_cesta + grupos_carro
                
                self._insertar_dato(grupos_cesta, grupos_carro)
                
                print(f"[{hora}] [ESTADO] Cola actual: {total_grupos} grupos ({grupos_cesta} Cestas, {grupos_carro} Carros)")
                print("-" * 65)
                
                time.sleep(intervalo_ciclo)

        except KeyboardInterrupt:
            print("\n[SIMULADOR] Simulacion detenida.")

if __name__ == "__main__":
    simulador = SimuladorRealista()
    simulador.ejecutar(intervalo_ciclo=2)