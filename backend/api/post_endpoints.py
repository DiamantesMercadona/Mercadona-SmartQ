from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone

from .database import update_queue
from .redis_client import set_bytes, publish_bytes

router = APIRouter()

# ------------------------------
# MODELOS
# ------------------------------

class QueueUpdate(BaseModel):
    length: int = 0
    status: str


class PulseraEvent(BaseModel):
    pulsera_id: str
    evento: str
    timestamp: datetime = datetime.now(timezone.utc)


class DisplayEvent(BaseModel):
    mensaje: str
    timestamp: datetime = datetime.now(timezone.utc)


# ------------------------------
# ENDPOINT ORIGINAL (colas)
# ------------------------------

@router.post("/queues/{queue_id}")
async def update_queue_endpoint(queue_id: str, update: QueueUpdate):
    """
    Actualizar el estado de una cola específica.
    """
    try:
        updated = update_queue(queue_id, update.length, update.status)
        if not updated:
            raise HTTPException(status_code=404, detail="Cola no encontrada")
        return {"message": "Cola actualizada correctamente"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------
# NUEVO: EVENTO DE PULSERA
# ------------------------------

@router.post("/pulsera/evento")
async def recibir_evento_pulsera(evento: PulseraEvent):
    """
    Recibe un evento de la pulsera y lo publica en Redis.
    """
    try:
        payload = evento.model_dump_json().encode("utf-8")
        await set_bytes("ultimo_evento_pulsera", payload)
        await publish_bytes("canal_pulsera", payload)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------
# NUEVO: EVENTO DE DISPLAY
# ------------------------------

@router.post("/display/evento")
async def recibir_evento_display(evento: DisplayEvent):
    """
    Recibe un mensaje del display y lo publica en Redis.
    """
    try:
        payload = evento.model_dump_json().encode("utf-8")
        await set_bytes("ultimo_evento_display", payload)
        await publish_bytes("canal_display", payload)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
