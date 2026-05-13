# ============================================================
#  BACKEND FASTAPI + IOT (AÚN NO ACTIVADO)
#  — Esto lo dejo comentado como pediste —
# ============================================================

# from fastapi import FastAPI
# from iot.routes import router as iot_router
#
# app = FastAPI(
#     title="Mercadona SmartQ Backend",
#     description="Backend con FastAPI + MQTT + IoT",
#     version="1.0"
# )
#
# # Registrar rutas IoT
# app.include_router(iot_router, prefix="/iot")
#
# @app.get("/")
# def root():
#     return {"status": "backend running", "iot": "ready"}


# ============================================================
#  TU CÓDIGO ORIGINAL (ACTIVO)
# ============================================================
from vision_engine import VisionEngine

def main():

    # Instancia y ejecuta el motor de visión
    engine = VisionEngine()
    engine.process()

if __name__ == "__main__":
    main()