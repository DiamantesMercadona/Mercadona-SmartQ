import sqlite3
import time
import pandas as pd
import math
from config import CONFIG  

class ProcesadorDecisionesMSQ:
    def __init__(self):
        self.db_path = CONFIG["DATABASE"]["db_path"]
        

        self.cajas_totales = CONFIG["DECISION"]["cajas_totales"]
        self.cajas_abiertas = 1
        self.factor_rendimiento = 1.0 
        
 
        self.tiempo_cesta = CONFIG["DECISION"]["peso_persona"] * 60   
        self.tiempo_carro = CONFIG["DECISION"]["peso_carrito"] * 60  
        

        self.umbral_abrir_segundos = CONFIG["DECISION"]["umbral_tiempo_alerta"] * 60  
        self.umbral_cerrar_segundos = CONFIG["DECISION"]["umbral_tiempo_cierre"] * 60  
        

        self.umbral_grupos_max = CONFIG["DECISION"]["umbral_grupos_max"]
        self.umbral_grupos_min = CONFIG["DECISION"]["umbral_grupos_min"]
        

        self.cooldown_abrir = CONFIG["DECISION"]["cooldown_abrir"]            
        self.cooldown_cerrar = CONFIG["DECISION"]["cooldown_cerrar"]           
        self.tiempo_cortesia_segundos = CONFIG["DECISION"]["tiempo_gracia_cierre"]  
        self.inicio_calma_sostenida = None
        self.ultimo_cambio = 0

        self.ultimo_ticket_procesado = 0 
        self.alfa_aprendizaje = 0.2

    def obtener_datos_camara(self):
        """Lee directamente los Grupos con Cesta y Grupos con Carro desde la BD."""
        try:
            conn = sqlite3.connect(self.db_path)
            # Ahora leemos las nuevas columnas
            query = "SELECT grupos_cesta, grupos_carro FROM registro_colas ORDER BY id DESC LIMIT 3"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return 0, 0, 0
                
            # Hacemos la media de los últimos 3 registros y redondeamos
            grupos_cesta = int(df['grupos_cesta'].mean())
            grupos_carro = int(df['grupos_carro'].mean())
            grupos_totales = grupos_cesta + grupos_carro
            
            return grupos_cesta, grupos_carro, grupos_totales
            
        except Exception as e:
            # Silenciamos el error si la tabla aún no está creada
            return 0, 0, 0
        
    def aprender_de_tiempos_reales(self):
        """Busca nuevos clientes que hayan terminado y actualiza las medias matemáticas."""
        try:
            conn = sqlite3.connect(self.db_path)
            # Buscamos en una nueva tabla donde el simulador (o el TPV real) dejará los tiempos
            query = f"SELECT id, tipo, tiempo_tardado FROM registro_tiempos WHERE id > {self.ultimo_ticket_procesado}"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return

            for index, row in df.iterrows():
                tipo_cliente = row['tipo']
                tiempo_real = row['tiempo_tardado']
                
                # Fórmula de Media Móvil Exponencial (EMA)
                if tipo_cliente == "Cesta":
                    self.tiempo_cesta = (self.alfa_aprendizaje * tiempo_real) + ((1 - self.alfa_aprendizaje) * self.tiempo_cesta)
                    print(f"🧠 [APRENDIZAJE] Cesta ajustada a: {int(self.tiempo_cesta)}s (Último cliente: {int(tiempo_real)}s)")
                elif tipo_cliente == "Carro":
                    self.tiempo_carro = (self.alfa_aprendizaje * tiempo_real) + ((1 - self.alfa_aprendizaje) * self.tiempo_carro)
                    print(f"🧠 [APRENDIZAJE] Carro ajustado a: {int(self.tiempo_carro)}s (Último cliente: {int(tiempo_real)}s)")
                
                self.ultimo_ticket_procesado = row['id']
                
        except sqlite3.OperationalError:
            # Si la tabla aún no existe (porque el simulador no la ha creado), no hacemos nada
            pass
        except Exception as e:
            print(f"[Error Aprendizaje]: {e}")

    def evaluar_estado(self):
        self.aprender_de_tiempos_reales()

        cestas, carros, grupos = self.obtener_datos_camara()
        
        if cestas == 0 and carros == 0 and self.cajas_abiertas == 1:
            return

        carga_total_segundos = (cestas * self.tiempo_cesta) + (carros * self.tiempo_carro)
        tee = carga_total_segundos / self.cajas_abiertas if self.cajas_abiertas > 0 else carga_total_segundos
        
        print(f"[{time.strftime('%H:%M:%S')}] 👥 Grupos: {grupos} | 🛒 Cola: {cestas} cest, {carros} carr | 🟩 Cajas: {self.cajas_abiertas}/{self.cajas_totales}")
        print(f"⏱️ ESPERA (TEE): {int(tee // 60)}m {int(tee % 60)}s")


        tiempo_desde_cambio = time.time() - self.ultimo_cambio
        

        cajas_por_tee = math.ceil(carga_total_segundos / self.umbral_abrir_segundos)
        

        cajas_por_grupos = 1 + (grupos // self.umbral_grupos_max)
        
        cajas_objetivo = max(cajas_por_tee, cajas_por_grupos)
        
        cajas_objetivo = min(cajas_objetivo, self.cajas_totales) 


        if self.cajas_abiertas < cajas_objetivo:
            if self.inicio_calma_sostenida is not None:
                self.inicio_calma_sostenida = None 
                
            if tiempo_desde_cambio > self.cooldown_abrir:
                a_abrir = cajas_objetivo - self.cajas_abiertas
                self.cajas_abiertas += a_abrir
                self.ultimo_cambio = time.time()
                
                if cajas_por_tee >= cajas_por_grupos:
                    razon = f"TEE Excedido"
                else:
                    razon = f"Ratio Físico ({grupos} grupos)"
                    
                print(f"🚨 EMERGENCIA: {razon}. Abriendo {a_abrir} caja(s) para llegar a {self.cajas_abiertas}.")
            else:
                pass

        elif tee < self.umbral_cerrar_segundos or grupos <= self.umbral_grupos_min:
            if self.cajas_abiertas > 1:
                if tiempo_desde_cambio > self.cooldown_cerrar:
                    
                    if self.inicio_calma_sostenida is None:
                        self.inicio_calma_sostenida = time.time()
                        print(f"⏱️ CORTESÍA: Afluencia baja. Esperando {self.tiempo_cortesia_segundos}s...")
                    else:
                        tiempo_en_calma = time.time() - self.inicio_calma_sostenida
                        
                        if tiempo_en_calma >= self.tiempo_cortesia_segundos:
                            cajas_simuladas = self.cajas_abiertas - 1
                            tee_proyectado = carga_total_segundos / cajas_simuladas
                            zona_de_peligro = self.umbral_abrir_segundos * 0.85 
                            
                            if tee_proyectado < zona_de_peligro:
                                self.cajas_abiertas -= 1
                                self.ultimo_cambio = time.time()
                                self.inicio_calma_sostenida = None 
                                print("📉 CIERRE CONFIRMADO: Cerrando 1 caja.")
                            else:
                                print(f"🛡️ PREVENCIÓN: Cierre abortado. TEE proyectado en zona de peligro.")
                                self.inicio_calma_sostenida = None 
                else:
                    pass # En cooldown
        else:
            if self.inicio_calma_sostenida is not None:
                self.inicio_calma_sostenida = None
            print("✅ FLUJO ÓPTIMO.")
            
        print("-" * 75)



    def iniciar(self, intervalo_evaluacion=4):
        print("🚀 Iniciando Motor de Decisiones MSQ (SLA + Predictivo + Cortesía)")
        print(f"Límites configurados -> Apertura: > {self.umbral_abrir_segundos}s | Cierre: < {self.umbral_cerrar_segundos}s\n")
        
        while True:
            self.evaluar_estado()
            time.sleep(intervalo_evaluacion)

if __name__ == "__main__":
    procesador = ProcesadorDecisionesMSQ()
    procesador.iniciar(intervalo_evaluacion=4)