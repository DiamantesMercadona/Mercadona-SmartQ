from fastapi import APIRouter
from .mqtt_client import mqtt_client

router = APIRouter()

@router.post("/vibrar/{id_pulsera}")
def vibrar(id_pulsera: str):
    topic = f"tienda/pulsera/{id_pulsera}/vibrar"
    mqtt_client.publish(topic, "1")
    return {"status": "ok"}

@router.post("/display")
def display(msg: str):
    mqtt_client.publish("tienda/display/caja/mensaje", msg)
    return {"status": "ok"}
