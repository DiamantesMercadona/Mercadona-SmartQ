from fastapi import APIRouter, HTTPException, Query
from typing import Annotated

from .database import DatabaseMSQ, get_queues

router = APIRouter()


@router.get("/queues")
async def get_all_queues():
    """
    Compatibilidad con la simulacion: devuelve las cajas como colas.
    """
    try:
        return {"queues": get_queues()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/queues/{queue_id}")
async def get_queue(queue_id: str):
    """
    Compatibilidad con la simulacion: obtiene una caja/cola por ID.
    """
    try:
        queue = next((q for q in get_queues() if str(q["id"]) == str(queue_id)), None)
        if queue is None:
            raise HTTPException(status_code=404, detail="Cola no encontrada")
        return queue
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cajas")
async def get_cajas():
    try:
        with DatabaseMSQ() as db:
            return {"cajas": db.obtener_cajas()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/cajas/{id_caja}")
async def get_caja(id_caja: str):
    try:
        with DatabaseMSQ() as db:
            caja = db.obtener_caja(id_caja)
        if caja is None:
            raise HTTPException(status_code=404, detail="Caja no encontrada")
        return caja
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/instantaneas")
async def get_instantaneas(limite: Annotated[int, Query(ge=1, le=1000)] = 10):
    try:
        with DatabaseMSQ() as db:
            return {"instantaneas": db.obtener_instantaneas(limite=limite)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metricas")
async def get_metricas(
    id_caja: str | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    limite: Annotated[int, Query(ge=1, le=10000)] = 1000,
    solo_global: bool = False,
):
    try:
        with DatabaseMSQ() as db:
            metricas = db.obtener_metricas(
                id_caja=id_caja,
                desde=desde,
                hasta=hasta,
                limite=limite,
                solo_global=solo_global,
            )
        return {"metricas": metricas}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/empleados")
async def get_empleados(activos: bool = False):
    try:
        with DatabaseMSQ() as db:
            return {"empleados": db.listar_empleados(activos=activos)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/empleados/{id_empleado}")
async def get_empleado(id_empleado: int):
    try:
        with DatabaseMSQ() as db:
            empleado = db.obtener_empleado(id_empleado)
        if empleado is None:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        return empleado
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/turnos")
async def get_turnos(dia_semana: str | None = None, turno: str | None = None):
    try:
        with DatabaseMSQ() as db:
            return {"turnos": db.obtener_turnos(dia_semana=dia_semana, turno=turno)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
