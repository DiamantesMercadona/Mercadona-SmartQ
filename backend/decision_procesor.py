import time
import math
import collections
from config import CONFIG
from database import DatabaseMSQ



class HistorialMetricas:
    """
    Almacena en memoria las últimas `ventana` lecturas de TEE global y por caja.
    No depende de la BD → latencia cero, útil para lógica de decisión en tiempo real.
    """

    def __init__(self, ventana: int = 60):
        self.ventana = ventana
        # TEE global: deque de (timestamp, tee_segundos)
        self.global_tee: collections.deque = collections.deque(maxlen=ventana)
        # TEE por caja: dict de id_caja → deque de (timestamp, tee_segundos)
        self.por_caja: dict[str, collections.deque] = {}

    def registrar_global(self, tee: float):
        self.global_tee.append((time.time(), tee))

    def registrar_caja(self, id_caja: str, tee: float):
        if id_caja not in self.por_caja:
            self.por_caja[id_caja] = collections.deque(maxlen=self.ventana)
        self.por_caja[id_caja].append((time.time(), tee))

    def media_global(self) -> float:
        """Media aritmética simple del TEE global en la ventana."""
        if not self.global_tee:
            return 0.0
        return sum(v for _, v in self.global_tee) / len(self.global_tee)

    def media_caja(self, id_caja: str) -> float:
        """Media aritmética del TEE de una caja concreta."""
        datos = self.por_caja.get(id_caja)
        if not datos:
            return 0.0
        return sum(v for _, v in datos) / len(datos)

    def tendencia_global(self) -> str:
        """
        Compara el primer tercio del historial con el último tercio.
        Devuelve: 'subiendo', 'bajando' o 'estable'.
        """
        if len(self.global_tee) < 6:
            return "estable"

        valores = [v for _, v in self.global_tee]
        tercio = max(1, len(valores) // 3)
        media_inicio = sum(valores[:tercio]) / tercio
        media_fin = sum(valores[-tercio:]) / tercio

        delta = media_fin - media_inicio
        umbral_cambio = media_inicio * 0.15  # 15 % de variación mínima

        if delta > umbral_cambio:
            return "subiendo"
        elif delta < -umbral_cambio:
            return "bajando"
        return "estable"

    def resumen(self) -> dict:
        """Devuelve un dict con todas las métricas en memoria."""
        return {
            "tee_global_actual": self.global_tee[-1][1] if self.global_tee else 0.0,
            "tee_global_media": self.media_global(),
            "tendencia": self.tendencia_global(),
            "cajas": {
                cid: {
                    "tee_actual": datos[-1][1] if datos else 0.0,
                    "tee_media": self.media_caja(cid),
                }
                for cid, datos in self.por_caja.items()
            },
        }


class ProcesadorDecisionesMSQ:

    # ── EMA alpha: 0.3 = más peso al historial, 0.7 = más reactivo ──
    EMA_ALPHA = 0.3

    def __init__(self):
        # 1. Estado del sistema
        self.cajas_totales = CONFIG["DECISION"]["cajas_totales"]
        self.cajas_abiertas = 1

        # 2. Tiempos Base (minutos → segundos)
        self.tiempo_cesta = CONFIG["DECISION"]["peso_persona"] * 60
        self.tiempo_carro = CONFIG["DECISION"]["peso_carrito"] * 60

        # 3. Umbrales SLA (minutos → segundos)
        self.umbral_abrir_segundos = CONFIG["DECISION"]["umbral_tiempo_alerta"] * 60
        self.umbral_cerrar_segundos = CONFIG["DECISION"]["umbral_tiempo_cierre"] * 60

        # Umbrales por saturación física
        self.umbral_grupos_max = CONFIG["DECISION"]["umbral_grupos_max"]
        self.umbral_grupos_min = CONFIG["DECISION"]["umbral_grupos_min"]

        # 4. Cooldowns y cortesía (ya en segundos)
        self.cooldown_abrir = CONFIG["DECISION"]["cooldown_abrir"]
        self.cooldown_cerrar = CONFIG["DECISION"]["cooldown_cerrar"]
        self.tiempo_cortesia_segundos = CONFIG["DECISION"]["tiempo_gracia_cierre"]

        self.inicio_calma_sostenida = None
        self.ultimo_cambio = 0

        # ── NUEVO: EMA del TEE global ──────────────────────────────────────
        self._ema_tee: float | None = None

        # ── NUEVO: Historial en memoria ────────────────────────────────────
        self.historial = HistorialMetricas(ventana=60)

        # 5. Sincronizamos la BD con el estado inicial
        self.sincronizar_cajas_db()

    # ─────────────────────────────────────────────────────────────────────────
    # LECTURA DE CÁMARA
    # ─────────────────────────────────────────────────────────────────────────

    def obtener_datos_camara(self):
        """
        Lee las instantáneas desde DatabaseMSQ y devuelve medias de cestas,
        carros y grupos totales. Sin cambios funcionales respecto a la v1.
        """
        try:
            with DatabaseMSQ() as db:
                ultimas_instantaneas = db.obtener_instantaneas(limite=3)

            if not ultimas_instantaneas:
                return 0, 0, 0

            total_cestas = total_carros = 0

            for snapshot in ultimas_instantaneas:
                for cola in snapshot["estado_cajas"].values():
                    total_cestas += cola.count("sinCarro")
                    total_carros += cola.count("conCarro")

            n = len(ultimas_instantaneas)
            return int(total_cestas / n), int(total_carros / n), int((total_cestas + total_carros) / n)

        except Exception as e:
            print(f"[Error de Lectura DB]: {e}")
            return 0, 0, 0

    # ─────────────────────────────────────────────────────────────────────────
    # NUEVO: EMA sobre el TEE
    # ─────────────────────────────────────────────────────────────────────────

    def _actualizar_ema(self, tee_nuevo: float) -> float:
        """
        Aplica Exponential Moving Average para suavizar picos de cámara.
        En la primera lectura inicializa con el valor crudo.
        """
        if self._ema_tee is None:
            self._ema_tee = tee_nuevo
        else:
            self._ema_tee = self.EMA_ALPHA * tee_nuevo + (1 - self.EMA_ALPHA) * self._ema_tee
        return self._ema_tee

    # ─────────────────────────────────────────────────────────────────────────
    # SINCRONIZACIÓN BD
    # ─────────────────────────────────────────────────────────────────────────

    def sincronizar_cajas_db(self):
        """Garantiza que la tabla 'cajas' refleje el estado decidido por el algoritmo."""
        try:
            with DatabaseMSQ() as db:
                cajas_db = {c["id"]: c["estado"] for c in db.obtener_cajas()}

                for i in range(1, self.cajas_totales + 1):
                    id_caja = str(i)
                    estado_deseado = "abierta" if i <= self.cajas_abiertas else "cerrada"

                    if id_caja not in cajas_db:
                        db.crear_caja(id=id_caja, estado=estado_deseado)
                        print(f"📦 [SISTEMA] Caja {id_caja} dada de alta como '{estado_deseado}'.")
                    elif cajas_db[id_caja] != estado_deseado:
                        db.actualizar_caja(id=id_caja, estado=estado_deseado)
        except Exception as e:
            print(f"[ERROR DB] Fallo al sincronizar cajas: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # MÉTRICAS BD  +  MEMORIA EN TIEMPO REAL
    # ─────────────────────────────────────────────────────────────────────────

    def guardar_metricas_db(self, tee_global: float):
        """
        Registra en BD el TEE global y el TEE individual de cada caja abierta.
        ADEMÁS actualiza el historial en memoria para uso inmediato por el algoritmo.
        """
        # ── Actualizar historial en memoria ──────────────────────────────────
        self.historial.registrar_global(tee_global)

        try:
            with DatabaseMSQ() as db:
                # TEE global
                db.registrar_metrica(
                    tiempo_medio_espera_segundos=tee_global,
                    id_caja=None,
                    fuente="decision_processor",
                )

                ultimas = db.obtener_instantaneas(limite=1)
                if not ultimas:
                    return

                estado_cajas = ultimas[0]["estado_cajas"]

                for id_caja, cola in estado_cajas.items():
                    if int(id_caja) <= self.cajas_abiertas:
                        cestas = cola.count("sinCarro")
                        carros = cola.count("conCarro")
                        tee_ind = (cestas * self.tiempo_cesta) + (carros * self.tiempo_carro)

                        # ── Guardar en memoria por caja ───────────────────
                        self.historial.registrar_caja(id_caja, tee_ind)

                        db.registrar_metrica(
                            tiempo_medio_espera_segundos=tee_ind,
                            id_caja=str(id_caja),
                            fuente="decision_processor",
                        )

        except Exception as e:
            print(f"[ERROR DB] Fallo al guardar métricas: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # NUEVO: DETECCIÓN DE DESEQUILIBRIO DE CARGA ENTRE CAJAS
    # ─────────────────────────────────────────────────────────────────────────

    def _detectar_desequilibrio(self) -> list[str]:
        """
        Compara el TEE medio de cada caja abierta.
        Si una caja supera en >50 % la media del resto, emite una alerta.
        Devuelve lista de strings de alerta (vacía si todo OK).
        """
        alertas = []
        cajas_activas = [str(i) for i in range(1, self.cajas_abiertas + 1)]
        medias = {cid: self.historial.media_caja(cid) for cid in cajas_activas}

        if len(medias) < 2:
            return alertas

        media_global = sum(medias.values()) / len(medias)
        if media_global == 0:
            return alertas

        for cid, media in medias.items():
            ratio = media / media_global
            if ratio > 1.5:
                alertas.append(
                    f"⚠️  Caja {cid} tiene cola {ratio:.1f}x la media "
                    f"({int(media // 60)}m {int(media % 60)}s vs media {int(media_global // 60)}m {int(media_global % 60)}s)"
                )
        return alertas

    # ─────────────────────────────────────────────────────────────────────────
    # NUEVO: DIAGNÓSTICO COMPLETO (llamable desde fuera o en logs periódicos)
    # ─────────────────────────────────────────────────────────────────────────

    def diagnosticar(self):
        """
        Imprime un resumen completo del estado en memoria:
        TEE global actual y media, TEE por caja, tendencia y alertas de desequilibrio.
        """
        r = self.historial.resumen()
        tend = r["tendencia"]
        icono_tend = {"subiendo": "📈", "bajando": "📉", "estable": "➡️"}.get(tend, "➡️")

        print("\n" + "═" * 75)
        print("📊  DIAGNÓSTICO DEL SISTEMA")
        print(f"    TEE global ahora : {int(r['tee_global_actual'] // 60)}m {int(r['tee_global_actual'] % 60)}s")
        print(f"    TEE global media : {int(r['tee_global_media'] // 60)}m {int(r['tee_global_media'] % 60)}s")
        print(f"    Tendencia        : {icono_tend} {tend.upper()}")
        print(f"    Cajas abiertas   : {self.cajas_abiertas}/{self.cajas_totales}")

        if r["cajas"]:
            print("    ── TEE por caja ─────────────────────────────────────────")
            for cid, datos in sorted(r["cajas"].items()):
                act = datos["tee_actual"]
                med = datos["tee_media"]
                print(
                    f"       Caja {cid}: ahora={int(act // 60)}m{int(act % 60)}s  "
                    f"media={int(med // 60)}m{int(med % 60)}s"
                )

        alertas = self._detectar_desequilibrio()
        if alertas:
            print("    ── Alertas de desequilibrio ─────────────────────────────")
            for a in alertas:
                print(f"       {a}")
        else:
            print("    ✅ Carga equilibrada entre cajas.")
        print("═" * 75 + "\n")

    # ─────────────────────────────────────────────────────────────────────────
    # LÓGICA PRINCIPAL DE EVALUACIÓN
    # ─────────────────────────────────────────────────────────────────────────

    def evaluar_estado(self):
        cestas, carros, grupos = self.obtener_datos_camara()

        if cestas == 0 and carros == 0 and self.cajas_abiertas == 1:
            self.guardar_metricas_db(0.0)
            return

        carga_total_segundos = (cestas * self.tiempo_cesta) + (carros * self.tiempo_carro)
        tee_crudo = carga_total_segundos / self.cajas_abiertas if self.cajas_abiertas > 0 else carga_total_segundos

        # ── NUEVO: suavizamos el TEE con EMA antes de tomar decisiones ──────
        tee = self._actualizar_ema(tee_crudo)

        print(
            f"[{time.strftime('%H:%M:%S')}] "
            f"👥 Grupos: {grupos} | 🛒 {cestas} cest, {carros} carr | "
            f"🟩 Cajas: {self.cajas_abiertas}/{self.cajas_totales}"
        )
        print(
            f"⏱️  TEE crudo: {int(tee_crudo // 60)}m {int(tee_crudo % 60)}s  "
            f"| TEE EMA: {int(tee // 60)}m {int(tee % 60)}s"
        )

        # Guardamos telemetría (BD + memoria)
        self.guardar_metricas_db(tee)

        # ── NUEVO: usamos la tendencia para ajustar umbrales dinámicamente ──
        tendencia = self.historial.tendencia_global()
        factor_tendencia_abrir = 0.85 if tendencia == "subiendo" else 1.0   # anticipa apertura
        factor_tendencia_cerrar = 1.15 if tendencia == "bajando" else 1.0   # retrasa cierre

        umbral_abrir_efectivo = self.umbral_abrir_segundos * factor_tendencia_abrir
        umbral_cerrar_efectivo = self.umbral_cerrar_segundos * factor_tendencia_cerrar

        tiempo_desde_cambio = time.time() - self.ultimo_cambio

        # ── LÓGICA DE APERTURA ───────────────────────────────────────────────
        cajas_por_tee = math.ceil(carga_total_segundos / umbral_abrir_efectivo)
        cajas_por_grupos = 1 + (grupos // self.umbral_grupos_max)
        cajas_objetivo = min(max(cajas_por_tee, cajas_por_grupos), self.cajas_totales)

        if self.cajas_abiertas < cajas_objetivo:
            if self.inicio_calma_sostenida is not None:
                self.inicio_calma_sostenida = None

            if tiempo_desde_cambio > self.cooldown_abrir:
                a_abrir = cajas_objetivo - self.cajas_abiertas
                self.cajas_abiertas += a_abrir
                self.ultimo_cambio = time.time()
                self.sincronizar_cajas_db()

                razon = (
                    f"TEE EMA excedido ({tendencia})"
                    if cajas_por_tee >= cajas_por_grupos
                    else f"Ratio físico ({grupos} grupos)"
                )
                print(f"🚨 EMERGENCIA: {razon}. Abriendo {a_abrir} caja(s) → total {self.cajas_abiertas}.")

        # ── LÓGICA DE CIERRE ─────────────────────────────────────────────────
        elif (
            self.cajas_abiertas > cajas_objetivo
            and (tee < umbral_cerrar_efectivo or grupos <= self.umbral_grupos_min)
        ):
            if self.cajas_abiertas > 1:
                if tiempo_desde_cambio > self.cooldown_cerrar:

                    if self.inicio_calma_sostenida is None:
                        self.inicio_calma_sostenida = time.time()
                        print(f"⏱️  CORTESÍA: Afluencia baja. Esperando {self.tiempo_cortesia_segundos}s...")
                    else:
                        tiempo_en_calma = time.time() - self.inicio_calma_sostenida

                        if tiempo_en_calma >= self.tiempo_cortesia_segundos:
                            cajas_simuladas = self.cajas_abiertas - 1
                            tee_proyectado = carga_total_segundos / cajas_simuladas
                            zona_peligro = umbral_abrir_efectivo * 0.85

                            if tee_proyectado < zona_peligro:
                                self.cajas_abiertas -= 1
                                self.ultimo_cambio = time.time()
                                self.inicio_calma_sostenida = None
                                self.sincronizar_cajas_db()
                                print("📉 CIERRE CONFIRMADO: Cerrando 1 caja.")
                            else:
                                print("🛡️  PREVENCIÓN: Cierre abortado. TEE proyectado en zona de peligro.")
                                self.inicio_calma_sostenida = None

        else:
            if self.inicio_calma_sostenida is not None:
                self.inicio_calma_sostenida = None
            print("✅ FLUJO ÓPTIMO.")

        # ── Alertas de desequilibrio en tiempo real ──────────────────────────
        for alerta in self._detectar_desequilibrio():
            print(alerta)

        print("-" * 75)

    # ─────────────────────────────────────────────────────────────────────────
    # BUCLE PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def iniciar(self, intervalo: int = 5, intervalo_diagnostico: int = 60):
        """
        Arranca el procesador.
        - intervalo           : segundos entre cada evaluación (default 5).
        - intervalo_diagnostico: segundos entre diagnósticos completos (default 60).
        """
        print(f"🚀 Iniciando Procesador de Decisiones MSQ v2 (Intervalo: {intervalo}s)")
        print(f"⚙️  Límite: {self.cajas_totales} cajas | EMA α={self.EMA_ALPHA}")
        print(f"⚙️  SLA Abrir: {self.umbral_abrir_segundos // 60}m | SLA Cerrar: {self.umbral_cerrar_segundos // 60}m")
        print("=" * 75)

        ultimo_diagnostico = time.time()

        try:
            while True:
                self.evaluar_estado()

                # Diagnóstico periódico completo
                if time.time() - ultimo_diagnostico >= intervalo_diagnostico:
                    self.diagnosticar()
                    ultimo_diagnostico = time.time()

                time.sleep(intervalo)

        except KeyboardInterrupt:
            print("\n🛑 Procesador detenido por el usuario.")
            self.diagnosticar()  # Resumen final al salir


if __name__ == "__main__":
    procesador = ProcesadorDecisionesMSQ()
    procesador.iniciar(intervalo=5, intervalo_diagnostico=60)