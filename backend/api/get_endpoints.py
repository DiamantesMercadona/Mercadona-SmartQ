from fastapi import APIRouter, HTTPException
from .database import get_queues

router = APIRouter()

@router.get("/queues")
async def get_all_queues():
    """
    Obtener el estado de todas las colas.
    """
    try:
        queues = get_queues()
        return {"queues": queues}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queues/{queue_id}")
async def get_queue(queue_id: int):
    """
    Obtener el estado de una cola específica por ID.
    """
    try:
        queues = get_queues()
        queue = next((q for q in queues if q["id"] == queue_id), None)
        if not queue:
            raise HTTPException(status_code=404, detail="Cola no encontrada")
        return queue
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
