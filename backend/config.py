CONFIG = {
    # Configuración de Entorno y Hardware
    "APP": {
        "mode": "DEBUG",                # "DEBUG" o "PRODUCTION"
        "source_index": 0,              # ID de la cámara (Webcam = 0)
        "yolo_model": "yolov8n.pt",     # Modelo de IA
    },

    # Infraestructura y Persistencia
    "DATABASE": {
        "redis_host": "localhost",      # Host de Redis
        "redis_port": 6379,             # Puerto de Redis
        "redis_db": 0,                  # Base logica de Redis
        "redis_video_channel": "msq:video:events",  # Canal Pub/Sub para eventos del simulador
        "db_path": "msq.db",            # Archivo SQLite para almacenamiento local
        "cadencia_grabacion_seg": 5,    # Intervalo de guardado en SQLite
    },

    # Parámetros del Motor de Visión
    "VISION": {
        "cluster_radius_px": 120,       # Radio DBSCAN para agrupar personas, en píxeles
    },

    # Lógica de Negocio y Algoritmo de Decisión
    "DECISION": {
        "peso_persona": 1.5,            # Minutos de trabajo por persona
        "peso_carrito": 4.5,            # Minutos de trabajo por carrito
        
        "umbral_tiempo_alerta": 8,      # Minutos de TEE para ABRIR caja
        "umbral_grupos_max": 5,         # Grupos máximos para ABRIR caja (Saturación física)
        
        "umbral_tiempo_cierre": 2.5,    # Minutos de TEE para CERRAR caja
        "umbral_grupos_min": 2,         # Grupos mínimos para CERRAR caja
        "tiempo_gracia_cierre": 20,     # Segundos del cronómetro de cortesía
        
        "cajas_totales": 6,             # Límite físico del supermercado
        "cooldown_abrir": 15,           # Segundos de bloqueo tras abrir caja
        "cooldown_cerrar": 20           # Segundos de bloqueo tras cerrar caja
    }
}
