from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Any

from .redis_client import (
    get_latest_video_payload,
    get_video_channel,
    ping_redis,
    publish_video_payload,
    subscribe_video_payloads,
    subscribe_bytes,
)

router = APIRouter()


# ---------------------------------------------------------
# MODELO DE EVENTO DE VIDEO
# ---------------------------------------------------------

class VideoEvent(BaseModel):
    camera_id: str = Field(default="simulador-3d", examples=["simulador-3d"])
    zone: str = Field(default="Caja_Principal_Simulada", examples=["Caja_1"])
    frame_id: int | None = Field(default=None, ge=0)
    people_count: int = Field(ge=0, examples=[5])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------
# REDIS HEALTH
# ---------------------------------------------------------

@router.get("/redis/health")
async def redis_health():
    try:
        return {
            "redis": "ok",
            "channel": get_video_channel(),
            "connected": await ping_redis()
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo conectar con Redis: {exc}")


# ---------------------------------------------------------
# VIDEO: PUBLICAR EVENTO
# ---------------------------------------------------------

@router.post("/video/events", status_code=202)
async def publish_video_event(event: VideoEvent):
    """
    Recibe una medición/frame del simulador y lo publica en Redis Pub/Sub.
    """
    payload = event.model_dump(mode="json")
    payload_bytes = event.model_dump_json().encode("utf-8")
    channel = get_video_channel()

    if not payload:
        raise HTTPException(status_code=400, detail="El payload binario no puede estar vacío")

    try:
        subscribers = await publish_video_payload(payload)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo publicar en Redis: {exc}")

    return {
        "message": "Evento publicado en Redis",
        "channel": channel,
        "subscribers": subscribers,
        "bytes": len(payload_bytes),
    }


# ---------------------------------------------------------
# VIDEO: OBTENER ÚLTIMO EVENTO
# ---------------------------------------------------------

@router.get("/video/events/latest")
async def get_latest_video_event():
    try:
        payload = await get_latest_video_payload()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo leer de Redis: {exc}")

    if payload is None:
        raise HTTPException(status_code=404, detail="No hay eventos de video publicados")

    return Response(content=payload, media_type="application/octet-stream")


# ---------------------------------------------------------
# VIDEO: WEBSOCKET ENTRADA
# ---------------------------------------------------------

@router.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    """
    WebSocket para recibir frames binarios y publicarlos en Redis.
    """
    await websocket.accept()
    channel = get_video_channel()

    try:
        while True:
            payload = await websocket.receive_bytes()
            subscribers = await publish_video_payload(payload)

            await websocket.send_bytes(
                f"Evento publicado en Redis; channel={channel}; subscribers={subscribers}".encode("utf-8")
            )

    except WebSocketDisconnect:
        return
    except RuntimeError:
        await websocket.close(code=1003, reason="Solo se aceptan mensajes binarios")
    except Exception as exc:
        await websocket.close(code=1011, reason=f"Error publicando en Redis: {exc}")


# ---------------------------------------------------------
# VIDEO: WEBSOCKET SALIDA
# ---------------------------------------------------------

@router.websocket("/ws/video/events")
async def video_events_stream(websocket: WebSocket):
    """
    WebSocket de salida para reenviar a clientes los eventos binarios publicados en Redis.
    """
    await websocket.accept()

    try:
        async for payload in subscribe_video_payloads(include_latest=True):
            await websocket.send_bytes(payload)

    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.close(code=1011, reason=f"Error leyendo de Redis: {exc}")


# ---------------------------------------------------------
# NUEVO: WEBSOCKET PULSERA
# ---------------------------------------------------------

@router.websocket("/ws/pulsera")
async def pulsera_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        async for payload in subscribe_bytes("canal_pulsera"):
            await websocket.send_bytes(payload)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.close(code=1011, reason=f"Error leyendo eventos de pulsera: {exc}")


# ---------------------------------------------------------
# NUEVO: WEBSOCKET DISPLAY
# ---------------------------------------------------------

@router.websocket("/ws/display")
async def display_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        async for payload in subscribe_bytes("canal_display"):
            await websocket.send_bytes(payload)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.close(code=1011, reason=f"Error leyendo eventos de display: {exc}")
