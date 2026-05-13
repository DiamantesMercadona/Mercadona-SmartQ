CONFIG = {
    # Configuración de Entorno y Hardware
    "APP": {
        "mode": "DEBUG",                    # "DEBUG" o "PRODUCTION"
        "input_source_type": "webcam",      # "webcam", "video" o "image"
        "source_index": 0,                  # ID de la cámara (Webcam = 0)
        "default_image": "backend/resources/test_photo.jpg",        # Imagen por defecto para pruebas
        "default_video": "backend/resources/3d_demo.webm",      # Video de prueba por defecto
        "default_source": "backend/resources/3d_demo.webm",     # Fuente por defecto si se usa un archivo
        "yolo_model": "yolov8n.pt",                                 # Modelo YOLO original para detección de personas
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
        "roi_columns": 3,               # Columnas de áreas ROI
        "roi_rows": 2,                  # Filas de áreas ROI (3x2 = 6 áreas)
        "roi_margin_x": 40,             # Margen horizontal de las áreas ROI
        "roi_margin_top": 120,          # Margen superior de las áreas ROI
        "roi_margin_bottom": 40,        # Margen inferior de las áreas ROI
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
