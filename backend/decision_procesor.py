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

    def obtener_datos_camara(self):
        """Para pruebas: Simulamos que los 'grupos' son el total de personas dividido por 1.5"""
        try:
            conn = sqlite3.connect(self.db_path)
            query = "SELECT personas_en_cola FROM registro_colas ORDER BY id DESC LIMIT 3"
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if df.empty:
                return 0, 0, 0
                
            total_personas = df['personas_en_cola'].mean()
            carros = int(total_personas * 0.2)
            cestas = int(total_personas - carros)
            grupos = math.ceil(total_personas / 1.5)
            
            return cestas, carros, grupos
        except Exception:
            return 0, 0, 0

    def evaluar_estado(self):
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