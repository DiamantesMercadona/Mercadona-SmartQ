import sys
from pathlib import Path
from fastapi import FastAPI

# Agregar el directorio backend al path (para DatabaseMSQ)
BACKEND_DIR = Path(__file__).resolve().parent.parent
API_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

# Importar con fallback para ambos modos de ejecución
# Intentar primero importaciones relativas (para cuando se ejecuta como módulo)
try:
    from .db_helpers import init_db
    from .get_endpoints import router as get_router
    from .post_endpoints import router as post_router
    from .video_endpoints import router as video_router
except ImportError:
    # Fallback para importaciones absolutas (para ejecución directa)
    try:
        from db_helpers import init_db
        from get_endpoints import router as get_router
        from post_endpoints import router as post_router
        from video_endpoints import router as video_router
    except ImportError:
        raise

#PODRIA GENERAR PROBLEMAS
#from backend.iot.routes import router as iot_router

# Inicializar la base de datos
init_db()

app = FastAPI(
    title="Mercadona Queue API",
    description="API para acceder al estado de las colas"
)

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "Mercadona Queue API",
        "usage": "Use /api/v1/* endpoints or /docs for API documentation",
        "endpoints": [
            "/api/v1/queues",
            "/api/v1/cajas",
            "/api/v1/instantaneas",
            "/api/v1/metricas",
            "/api/v1/empleados",
            "/api/v1/turnos",
        ],
    }

# si el broker no esta activo podría generar dependencias con MQTT.
#app.include_router(iot_router, prefix="/api/v1", tags=["IoT MQTT"])
#para hacer uso de:
#/api/v1/vibrar/{id_pulsera}
#/api/v1/display

# Rutas GET
app.include_router(get_router, prefix="/api/v1", tags=["GET Endpoints"])

# Rutas POST (colas, pulsera, display)
app.include_router(post_router, prefix="/api/v1", tags=["POST Endpoints"])

# Rutas de vídeo + WebSockets + pulsera + display
app.include_router(video_router, prefix="/api/v1", tags=["Video Redis Ingest"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
    