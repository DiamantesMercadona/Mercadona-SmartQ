from fastapi import FastAPI

from .database import init_db
from .get_endpoints import router as get_router
from .post_endpoints import router as post_router
from .video_endpoints import router as video_router

# Inicializar la base de datos
init_db()

app = FastAPI(
    title="Mercadona Queue API",
    description="API para acceder al estado de las colas"
)

# Rutas GET
app.include_router(get_router, prefix="/api/v1", tags=["GET Endpoints"])

# Rutas POST (colas, pulsera, display)
app.include_router(post_router, prefix="/api/v1", tags=["POST Endpoints"])

# Rutas de vídeo + WebSockets + pulsera + display
app.include_router(video_router, prefix="/api/v1", tags=["Video Redis Ingest"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    