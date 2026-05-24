import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from .database import DatabaseMSQ, update_queue
from .redis_client import set_bytes, publish_bytes

router = APIRouter()


class QueueUpdate(BaseModel):
    length: int = Field(default=0, ge=0)
    status: str


class CajaCreate(BaseModel):
    id: str
    estado: str
    id_empleado: int | None = None


class CajaUpdate(BaseModel):
    estado: str | None = None
    id_empleado: int | None = None


class InstantaneaCreate(BaseModel):
    estado_cajas: dict[str, list[str]]


class MetricaCreate(BaseModel):
    tiempo_medio_espera_segundos: float = Field(ge=0)
    id_caja: str | None = None
    fuente: str = "api"
    registrada_en: str | None = None


class EmpleadoCreate(BaseModel):
    nombre: str
    apellidos: str
    id_pulsera: str | None = None


class EmpleadoUpdate(BaseModel):
    nombre: str | None = None
    apellidos: str | None = None
    id_pulsera: str | None = None
    activo: bool | None = None


class LoginRequest(BaseModel):
    usuario: str
    contrasena: str


class UsuarioCreate(BaseModel):
    usuario: str
    contrasena: str


class TurnoUpdate(BaseModel):
    dia_semana: str
    turno: str
    orden: list[dict[str, Any]] = Field(default_factory=list)


class PulseraEvent(BaseModel):
    pulsera_id: str
    evento: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DisplayEvent(BaseModel):
    mensaje: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@router.post("/queues/{queue_id}")
async def update_queue_endpoint(queue_id: str, update: QueueUpdate):
    """
    Compatibilidad con la simulacion: actualiza el estado de una caja/cola.
    """
    try:
        if not update_queue(queue_id, update.length, update.status):
            raise HTTPException(status_code=404, detail="Cola no encontrada")
        return {"message": "Cola actualizada correctamente"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/cajas", status_code=status.HTTP_201_CREATED)
async def crear_caja(caja: CajaCreate):
    try:
        with DatabaseMSQ() as db:
            db.crear_caja(caja.id, caja.estado, caja.id_empleado)
            creada = db.obtener_caja(caja.id)
        return {"message": "Caja creada correctamente", "caja": creada}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"No se pudo crear la caja: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/cajas/{id_caja}")
async def actualizar_caja(id_caja: str, update: CajaUpdate):
    data = update.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    try:
        with DatabaseMSQ() as db:
            actualizado = db.actualizar_caja(id=id_caja, **data)
            caja = db.obtener_caja(id_caja) if actualizado else None
        if not actualizado:
            raise HTTPException(status_code=404, detail="Caja no encontrada")
        return {"message": "Caja actualizada correctamente", "caja": caja}
    except HTTPException:
        raise
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"No se pudo actualizar la caja: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/cajas/{id_caja}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_caja(id_caja: str):
    try:
        with DatabaseMSQ() as db:
            eliminado = db.eliminar_caja(id_caja)
        if not eliminado:
            raise HTTPException(status_code=404, detail="Caja no encontrada")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/instantaneas", status_code=status.HTTP_201_CREATED)
async def crear_instantanea(instantanea: InstantaneaCreate):
    try:
        with DatabaseMSQ() as db:
            instantanea_id = db.registrar_instantanea(instantanea.estado_cajas)
        return {"message": "Instantanea registrada correctamente", "id": instantanea_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/metricas", status_code=status.HTTP_201_CREATED)
async def crear_metrica(metrica: MetricaCreate):
    try:
        with DatabaseMSQ() as db:
            metrica_id = db.registrar_metrica(**metrica.model_dump())
        return {"message": "Metrica registrada correctamente", "id": metrica_id}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"No se pudo registrar la metrica: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/empleados", status_code=status.HTTP_201_CREATED)
async def crear_empleado(empleado: EmpleadoCreate):
    try:
        with DatabaseMSQ() as db:
            empleado_id = db.crear_empleado(**empleado.model_dump())
            creado = db.obtener_empleado(empleado_id)
        return {"message": "Empleado creado correctamente", "empleado": creado}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"No se pudo crear el empleado: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.patch("/empleados/{id_empleado}")
async def actualizar_empleado(id_empleado: int, update: EmpleadoUpdate):
    data = update.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    try:
        with DatabaseMSQ() as db:
            actualizado = db.actualizar_empleado(id_empleado=id_empleado, **data)
            empleado = db.obtener_empleado(id_empleado) if actualizado else None
        if not actualizado:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        return {"message": "Empleado actualizado correctamente", "empleado": empleado}
    except HTTPException:
        raise
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"No se pudo actualizar el empleado: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/empleados/{id_empleado}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_empleado(id_empleado: int):
    try:
        with DatabaseMSQ() as db:
            eliminado = db.eliminar_empleado(id_empleado)
        if not eliminado:
            raise HTTPException(status_code=404, detail="Empleado no encontrado")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/usuarios", status_code=status.HTTP_201_CREATED)
async def crear_usuario(usuario: UsuarioCreate):
    try:
        with DatabaseMSQ() as db:
            usuario_id = db.crear_usuario(usuario.usuario, usuario.contrasena)
        return {"message": "Usuario creado correctamente", "id": usuario_id}
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"No se pudo crear el usuario: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/auth/login")
async def login(credentials: LoginRequest):
    try:
        with DatabaseMSQ() as db:
            usuario = db.autenticar_usuario(credentials.usuario, credentials.contrasena)
        if usuario is None:
            raise HTTPException(status_code=401, detail="Credenciales invalidas")
        return {"message": "Autenticacion correcta", "usuario": usuario}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/usuarios/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_usuario(id_usuario: int):
    try:
        with DatabaseMSQ() as db:
            eliminado = db.eliminar_usuario(id_usuario)
        if not eliminado:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/turnos")
async def actualizar_turnos(turnos: list[TurnoUpdate]):
    try:
        with DatabaseMSQ() as db:
            db.actualizar_turnos([turno.model_dump() for turno in turnos])
            actualizados = db.obtener_turnos()
        return {"message": "Turnos actualizados correctamente", "turnos": actualizados}
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Falta el campo requerido: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
