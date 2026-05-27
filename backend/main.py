# Importaciones
try:
    from .vision_engine import VisionEngine
    from .database import DatabaseMSQ
except ImportError:
    from vision_engine import VisionEngine
    from database import DatabaseMSQ

try:
    from .config import CONFIG
except ImportError:
    from config import CONFIG

# Fuente de vídeo activa cargada desde la configuración
VIDEO_SOURCE = CONFIG["VISION"].get("video_source", "ws")

# Definición del punto de entrada del backend
def main():
    print("[Backend] Arrancando servicios de Mercadona SmartQ...")

    # 1. Inicialización de la base de datos (asegura creación de tablas y admin)
    print("[Backend] Verificando e inicializando base de datos...")
    db = DatabaseMSQ()
    db.close()
    print("[Backend] Base de datos lista.")

    # 2. Instanciación y ejecución del motor de visión
    print(f"[Backend] Iniciando el motor de visión (source={VIDEO_SOURCE!r})...")
    engine = VisionEngine(source=VIDEO_SOURCE)
    engine.process()

# Ejecución del punto de entrada
if __name__ == "__main__":
    main()
