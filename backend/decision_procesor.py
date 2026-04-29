import sqlite3
import time
import pandas as pd

class ProcesadorDecisionesAvanzado:
    def __init__(self, db_path='metricas_supermercado.db'):
        self.db_path = db_path
        
        # --- PARÁMETROS AVANZADOS ---
        self.ventana_minutos = 4         # Analizamos más tiempo hacia atrás (4 min)
        self.umbral_critico = 8          # Límite duro para abrir caja sí o sí
        self.umbral_normal = 3           # Límite para cerrar cajas
        
        # --- SISTEMA DE COOLDOWN (Evitar volver locos a los cajeros) ---
        self.ultimo_cambio_tiempo = 0
        self.cooldown_segundos = 120     # Esperar 2 minutos mínimo entre decisiones

    def obtener_datos(self) -> pd.DataFrame:
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"""
                SELECT fecha_hora, personas_en_cola 
                FROM registro_colas 
                WHERE fecha_hora >= datetime('now', '-{self.ventana_minutos} minute')
                ORDER BY fecha_hora ASC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            return pd.DataFrame()

    def evaluar_estado(self) -> None:
        df = self.obtener_datos()
        
        if len(df) < 5:  # Necesitamos un mínimo de datos para hacer cálculos
            print(f"[{time.strftime('%H:%M:%S')}] Recopilando datos...")
            return

        # 1. Dividimos los datos en dos bloques: "Pasado" y "Presente reciente"
        mitad = len(df) // 2
        bloque_antiguo = df.iloc[:mitad]['personas_en_cola'].mean()
        bloque_reciente = df.iloc[mitad:]['personas_en_cola'].mean()

        # 2. Análisis de Tendencia (¿A qué velocidad crece la cola?)
        tendencia = bloque_reciente - bloque_antiguo
        media_actual = bloque_reciente

        print(f"[{time.strftime('%H:%M:%S')}] Media actual: {media_actual:.1f} | Tendencia: {tendencia:+.1f} personas/min")

        # 3. Comprobar Cooldown
        if time.time() - self.ultimo_cambio_tiempo < self.cooldown_segundos:
            tiempo_restante = int(self.cooldown_segundos - (time.time() - self.ultimo_cambio_tiempo))
            print(f"⏳ Sistema en Cooldown ({tiempo_restante}s restantes) para no marear al personal.")
            print("-" * 50)
            return

        # 4. Lógica de Decisión Proactiva
        accion_tomada = False

        if media_actual >= self.umbral_critico:
            print("🚨 ALERTA ROJA: Cola desbordada. ABRIR CAJA INMEDIATAMENTE.")
            accion_tomada = True
            
        elif media_actual >= (self.umbral_critico - 2) and tendencia > 1.5:
            print("📈 ALERTA PREVENTIVA: La cola crece rápido. ABRIR CAJA antes del colapso.")
            accion_tomada = True
            
        elif media_actual <= self.umbral_normal and tendencia < -1.0:
            print("📉 AVISO: Afluencia bajando rápidamente. PREPARAR PARA CERRAR CAJA.")
            accion_tomada = True
            
        else:
            print("✅ Flujo estable. Sin cambios.")

        # Si hemos tomado una decisión, activamos el temporizador de bloqueo
        if accion_tomada:
            self.ultimo_cambio_tiempo = time.time()
            
        print("-" * 50)

    def iniciar(self, intervalo=15):
        print("🧠 Procesador MSQ Avanzado Iniciado (Tendencia + Cooldown)...")
        while True:
            self.evaluar_estado()
            time.sleep(intervalo)

if __name__ == "__main__":
    procesador = ProcesadorDecisionesAvanzado()
    procesador.iniciar(intervalo=15)