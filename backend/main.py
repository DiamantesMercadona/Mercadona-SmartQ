# Importaciones
try:
    from .vision_engine import VisionEngine
    from .database import DatabaseMSQ
except ImportError:
    from vision_engine import VisionEngine
    from database import DatabaseMSQ

# Fuente de vídeo activa. Cambiar aquí para alternar entre modos:
#   "ws"        → simulación 3D por WebSocket (CONFIG["VISION"]["ws_url"])
#   None        → vídeo de demostración local
#   0           → cámara física 0
#   "ruta.mp4"  → archivo de vídeo
VIDEO_SOURCE = "ws"

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
