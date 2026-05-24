# ------------------------------------------------------------------
# CONFIGURACIÓN GENERAL - MERCADONA SMARTQ (MSQ)
# ------------------------------------------------------------------
# Este módulo define el diccionario centralizado de configuración de la
# aplicación. Agrupa parámetros del motor de visión artificial (YOLO),
# infraestructura de persistencia (SQLite y Redis) y las reglas de negocio
# del algoritmo de toma de decisiones para la gestión de colas.

CONFIG = {
    # ------------------------------------------------------------------
    # Configuración del Motor de Visión Artificial
    # ------------------------------------------------------------------
    "VISION": {
        "yolo_model": "yolov8s.pt",          # Modelo YOLOv8 a cargar para la detección de personas
        "yolo_imgsz": 640,                   # Resolución en píxeles de la imagen de entrada para inferencia
        "yolo_confidence": 0.20,             # Umbral de confianza mínimo de detección (bajar para más recall)
        "yolo_iou": 0.45,                    # Umbral de Intersection over Union (IoU) para Non-Maximum Suppression (NMS)
        "yolo_frame_skip": 1,                # Factor de omisión de fotogramas para inferencia (1 = procesar todos)
        "cart_association_threshold": 120,   # Umbral de distancia en píxeles para emparejar carros con personas
    },

    # ------------------------------------------------------------------
    # Configuración de Persistencia y Mensajería
    # ------------------------------------------------------------------
    "DATABASE": {
        "db_path": "backend/msq.db",         # Ruta física local del archivo SQLite para el histórico
        "redis_host": "localhost",           # Dirección del servidor de mensajería rápida Redis
        "redis_port": 6379,                  # Puerto TCP de conexión para el servidor de Redis
        "redis_db": 0,                       # Índice de base de datos lógica de Redis a utilizar
        "redis_video_channel": "msq:video:events",  # Canal Pub/Sub para transmisión de eventos en simulación
    },

    # ------------------------------------------------------------------
    # Configuración del Algoritmo de Toma de Decisiones
    # ------------------------------------------------------------------
    "DECISION": {
        "cajas_totales": 6,                  # Límite máximo de cajas físicas instaladas en la tienda
        "peso_persona": 1.5,                 # Peso estimado en minutos asignado a cada persona con cesta
        "peso_carrito": 4.5,                 # Peso estimado en minutos asignado a cada persona con carro
        "umbral_tiempo_alerta": 8,           # Minutos de tiempo de espera límite para activar sugerencia de APERTURA
        "umbral_tiempo_cierre": 2.5,         # Minutos de tiempo de espera mínimo para sugerencia de CIERRE
        "umbral_grupos_max": 5,              # Personas toleradas por cola física antes de saturar una caja
        "umbral_grupos_min": 2,              # Personas en cola por debajo del cual es apta para cerrar caja
        "cooldown_abrir": 15,                # Tiempo de bloqueo en segundos tras abrir caja (evita oscilaciones)
        "cooldown_cerrar": 20,               # Tiempo de bloqueo en segundos tras cerrar caja (evita oscilaciones)
        "tiempo_gracia_cierre": 20,          # Período de gracia en segundos antes de consolidar el cierre definitivo
    }
}
