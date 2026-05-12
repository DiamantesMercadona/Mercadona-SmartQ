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
        "db_path": "msq.db",            # Archivo SQLite para almacenamiento local
        "cadencia_grabacion_seg": 5,    # Intervalo de guardado en SQLite
    },

    # Parámetros del Motor de Visión
    "VISION": {
        "cluster_radius_px": 120,       # Radio DBSCAN para agrupar personas, en píxeles
    },

    # Lógica de Negocio y Algoritmo de Decisión
    "DECISION": {

        # Ponderaciones para el cálculo del tiempo estimado
        "peso_persona": 1.5,            # Ponderación por persona detectada
        "peso_carrito": 4.5,            # Ponderación por carrito detectado
        
        # Umbrales de Apertura
        "umbral_tiempo_alerta": 8,      # Apertura por tiempo estimado, en minutos
        "umbral_grupos_max": 5,         # Apertura por saturación física de espacio, en número de grupos de personas
        
        # Umbrales de Cierre
        "umbral_tiempo_cierre": 2,      # Sugerencia de cierre por tiempo, en minutos
        "umbral_grupos_min": 2,         # Sugerencia de cierre por baja densidad, en número de grupos de personas
        "tiempo_gracia_cierre": 30,     # Segundos de espera antes de confirmar cierre, en segundos
    }
}
