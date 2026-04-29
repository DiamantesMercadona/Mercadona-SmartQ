from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .database import update_queue

router = APIRouter()

class QueueUpdate(BaseModel):
    length: int
    status: str

@router.post("/queues/{queue_id}")
async def update_queue_endpoint(queue_id: int, update: QueueUpdate):
    """
    Actualizar el estado de una cola específica.
    """
    try:
        update_queue(queue_id, update.length, update.status)
        return {"message": "Cola actualizada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))