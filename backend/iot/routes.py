from fastapi import APIRouter
from .mqtt_client import mqtt_client

router = APIRouter()

# ---------------------------------------------------------
# ENVIAR VIBRACIÓN A UNA PULSERA
# ---------------------------------------------------------

@router.post("/vibrar/{id_pulsera}")
def vibrar(id_pulsera: str):
    """
    Envía una orden de vibración a la pulsera indicada.
    """
    topic = f"tienda/pulsera/{id_pulsera}/vibrar"
    mqtt_client.publish(topic, "1")
    return {"status": "ok", "topic": topic}


# ---------------------------------------------------------
# ENVIAR MENSAJE AL DISPLAY
# ---------------------------------------------------------

@router.post("/display")
def display(msg: str):
    """
    Envía un mensaje al display de la caja.
    """
    topic = "tienda/display/caja/mensaje"
    mqtt_client.publish(topic, msg)
    return {"status": "ok", "topic": topic, "mensaje": msg}
