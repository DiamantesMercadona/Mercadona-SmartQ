import time
import math
from config import CONFIG
from database import DatabaseMSQ

class ProcesadorDecisionesMSQ:
    def __init__(self):
        # 1. Estado del sistema
        self.cajas_totales = CONFIG["DECISION"]["cajas_totales"]
        self.cajas_abiertas = 1
        
        # 2. Tiempos Base (Convertimos los minutos del CONFIG a Segundos para la CPU)
        self.tiempo_cesta = CONFIG["DECISION"]["peso_persona"] * 60   
        self.tiempo_carro = CONFIG["DECISION"]["peso_carrito"] * 60  
        
        # 3. Umbrales SLA (Convertidos a Segundos)
        self.umbral_abrir_segundos = CONFIG["DECISION"]["umbral_tiempo_alerta"] * 60  
        self.umbral_cerrar_segundos = CONFIG["DECISION"]["umbral_tiempo_cierre"] * 60  
        
        # Umbrales por Saturación Física
        self.umbral_grupos_max = CONFIG["DECISION"]["umbral_grupos_max"]
        self.umbral_grupos_min = CONFIG["DECISION"]["umbral_grupos_min"]
        
        # 4. Cooldowns y Cortesía (Ya vienen en segundos)
        self.cooldown_abrir = CONFIG["DECISION"]["cooldown_abrir"]            
        self.cooldown_cerrar = CONFIG["DECISION"]["cooldown_cerrar"]           
        self.tiempo_cortesia_segundos = CONFIG["DECISION"]["tiempo_gracia_cierre"]  
        
        self.inicio_calma_sostenida = None
        self.ultimo_cambio = 0

        # 5. Forzamos que la BD arranque sincronizada con 1 caja abierta
        self.sincronizar_cajas_db()

    def obtener_datos_camara(self):
        """Lee las instantáneas desde el gestor centralizado DatabaseMSQ."""
        try:
            with DatabaseMSQ() as db:
                ultimas_instantaneas = db.obtener_instantaneas(limite=3)
            
            if not ultimas_instantaneas:
                return 0, 0, 0
                
            total_cestas = 0
            total_carros = 0
            
            # Recorremos las últimas 3 fotos para hacer la media (antirrebote visual)
            for snapshot in ultimas_instantaneas:
                estado_cajas = snapshot["estado_cajas"]
                
                # estado_cajas es un diccionario: {"1": ["sinCarro"], "2": ["conCarro", "sinCarro"]}
                for cola in estado_cajas.values():
                    total_cestas += cola.count("sinCarro")
                    total_carros += cola.count("conCarro")
            
            num_fotos = len(ultimas_instantaneas)
            grupos_cesta = int(total_cestas / num_fotos)
            grupos_carro = int(total_carros / num_fotos)
            grupos_totales = grupos_cesta + grupos_carro
            
            return grupos_cesta, grupos_carro, grupos_totales
            
        except Exception as e:
            print(f"[Error de Lectura DB]: {e}")
            return 0, 0, 0

    def sincronizar_cajas_db(self):
        """
        Garantiza que la tabla 'cajas' de la BD refleje 
        exactamente el número de cajas abiertas decidido por el algoritmo.
        """
        try:
            with DatabaseMSQ() as db:
                cajas_db = {caja["id"]: caja["estado"] for caja in db.obtener_cajas()}

                for i in range(1, self.cajas_totales + 1):
                    id_caja = str(i)
                    estado_deseado = "abierta" if i <= self.cajas_abiertas else "cerrada"

                    # Si la caja no existe, la creamos
                    if id_caja not in cajas_db:
                        db.crear_caja(id=id_caja, estado=estado_deseado)
                        print(f"📦 [SISTEMA] Caja {id_caja} dada de alta como '{estado_deseado}'.")
                    
                    # Si existe pero tiene un estado antiguo, lo actualizamos
                    elif cajas_db[id_caja] != estado_deseado:
                        db.actualizar_caja(id=id_caja, estado=estado_deseado)
        except Exception as e:
            print(f"[ERROR DB] Fallo al sincronizar el estado de las cajas: {e}")

    def guardar_metricas_db(self, tee_global):
        """
        Registra el TEE global y calcula el TEE real e independiente SOLO de las cajas abiertas.
        """
        try:
            with DatabaseMSQ() as db:
                # 1. Guardamos la métrica GLOBAL
                db.registrar_metrica(
                    tiempo_medio_espera_segundos=tee_global,
                    id_caja=None,
                    fuente="decision_processor"
                )
                
                # 2. Obtenemos la foto más reciente
                ultimas = db.obtener_instantaneas(limite=1)
                if not ultimas:
                    return
                
                estado_cajas = ultimas[0]["estado_cajas"] 
                
                # 3. Calculamos y guardamos el tiempo real SOLO para las cajas abiertas
                for id_caja, cola in estado_cajas.items():
                    if int(id_caja) <= self.cajas_abiertas:
                        cestas_en_esta_caja = cola.count("sinCarro")
                        carros_en_esta_caja = cola.count("conCarro")
                        
                        tee_individual = (cestas_en_esta_caja * self.tiempo_cesta) + (carros_en_esta_caja * self.tiempo_carro)
                        
                        db.registrar_metrica(
                            tiempo_medio_espera_segundos=tee_individual,
                            id_caja=str(id_caja),
                            fuente="decision_processor"
                        )
                    
        except Exception as e:
            print(f"[ERROR DB] Fallo al guardar las métricas: {e}")

    def evaluar_estado(self):
        cestas, carros, grupos = self.obtener_datos_camara()
        
        if cestas == 0 and carros == 0 and self.cajas_abiertas == 1:
            # Si no hay nadie, guardamos TEE de 0 para no dejar huecos en gráficas
            self.guardar_metricas_db(0.0) 
            return

        carga_total_segundos = (cestas * self.tiempo_cesta) + (carros * self.tiempo_carro)
        tee = carga_total_segundos / self.cajas_abiertas if self.cajas_abiertas > 0 else carga_total_segundos
        
        print(f"[{time.strftime('%H:%M:%S')}] 👥 Grupos: {grupos} | 🛒 Cola: {cestas} cest, {carros} carr | 🟩 Cajas: {self.cajas_abiertas}/{self.cajas_totales}")
        print(f"⏱️ ESPERA (TEE): {int(tee // 60)}m {int(tee % 60)}s")

        # Guardamos telemetría
        self.guardar_metricas_db(tee)

        tiempo_desde_cambio = time.time() - self.ultimo_cambio
        
        # --- LÓGICA DE APERTURA (POR RATIO ABSOLUTO Y TEE) ---
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
                
                # Actualizamos la Base de Datos
                self.sincronizar_cajas_db()
                
                if cajas_por_tee >= cajas_por_grupos:
                    razon = f"TEE Excedido"
                else:
                    razon = f"Ratio Físico ({grupos} grupos)"
                    
                print(f"🚨 EMERGENCIA: {razon}. Abriendo {a_abrir} caja(s) para llegar a {self.cajas_abiertas}.")
            else:
                pass 

        # --- LÓGICA DE CIERRE (SLA, Baja densidad y Suelo de Seguridad) ---
        elif self.cajas_abiertas > cajas_objetivo and (tee < self.umbral_cerrar_segundos or grupos <= self.umbral_grupos_min):
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
                                
                                # Actualizamos la Base de Datos
                                self.sincronizar_cajas_db()
                                
                                print("📉 CIERRE CONFIRMADO: Cerrando 1 caja.")
                            else:
                                print(f"🛡️ PREVENCIÓN: Cierre abortado. TEE proyectado en zona de peligro.")
                                self.inicio_calma_sostenida = None 
                else:
                    pass 
        else:
            if self.inicio_calma_sostenida is not None:
                self.inicio_calma_sostenida = None
            print("✅ FLUJO ÓPTIMO.")
            
        print("-" * 75)

    def iniciar(self, intervalo=5):
        print(f"🚀 Iniciando Procesador de Decisiones MSQ (Intervalo: {intervalo}s)")
        print(f"⚙️ Límite: {self.cajas_totales} cajas | SLA Abrir: {self.umbral_abrir_segundos//60}m | SLA Cerrar: {self.umbral_cerrar_segundos//60}m")
        print("="*75)
        
        try:
            while True:
                self.evaluar_estado()
                time.sleep(intervalo)
        except KeyboardInterrupt:
            print("\n🛑 Procesador detenido por el usuario.")

if __name__ == "__main__":
    procesador = ProcesadorDecisionesMSQ()
    # Pongo intervalo 5 por defecto (igual que cadencia_grabacion_seg)
    procesador.iniciar(intervalo=5)