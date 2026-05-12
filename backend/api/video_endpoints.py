from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Response, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .redis_client import (
    get_bytes,
    get_video_channel,
    get_video_latest_key,
    ping_redis,
    publish_bytes,
    set_bytes,
    subscribe_bytes,
)

router = APIRouter()


class VideoEvent(BaseModel):
    camera_id: str = Field(default="simulador-3d", examples=["simulador-3d"])
    zone: str = Field(default="Caja_Principal_Simulada", examples=["Caja_1"])
    frame_id: int | None = Field(default=None, ge=0)
    people_count: int = Field(ge=0, examples=[5])
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/redis/health")
async def redis_health():
    """
    Comprueba que la API puede conectar con Redis.
    """
    try:
        return {"redis": "ok", "channel": get_video_channel(), "connected": await ping_redis()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo conectar con Redis: {exc}")


@router.post("/video/events", status_code=202)
async def publish_video_event(event: VideoEvent):
    """
    Recibe una medicion/frame del simulador y lo publica en Redis Pub/Sub.
    """
    payload = event.model_dump(mode="json")
    payload_bytes = event.model_dump_json().encode("utf-8")
    channel = get_video_channel()

    try:
        await set_bytes(get_video_latest_key(), payload_bytes)
        subscribers = await publish_bytes(channel, payload_bytes)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo publicar en Redis: {exc}")

    return {
        "message": "Evento publicado en Redis",
        "channel": channel,
        "subscribers": subscribers,
        "event": payload,
    }


@router.get("/video/events/latest")
async def get_latest_video_event():
    """
    Devuelve el ultimo evento de video guardado en Redis como bytes.
    """
    try:
        payload = await get_bytes(get_video_latest_key())
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo leer de Redis: {exc}")

    if payload is None:
        raise HTTPException(status_code=404, detail="No hay eventos de video publicados")

    return Response(content=payload, media_type="application/octet-stream")


@router.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    """
    WebSocket para recibir eventos continuos del simulador y reenviarlos a Redis.
    """
    await websocket.accept()
    channel = get_video_channel()

    try:
        while True:
            payload = await websocket.receive_bytes()
            await set_bytes(get_video_latest_key(), payload)
            subscribers = await publish_bytes(channel, payload)
            await websocket.send_bytes(
                f"Evento publicado en Redis; channel={channel}; subscribers={subscribers}".encode(
                    "utf-8"
                )
            )
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.close(code=1011, reason=f"Error publicando en Redis: {exc}")


@router.websocket("/ws/video/events")
async def video_events_stream(websocket: WebSocket):
    """
    WebSocket de salida para reenviar a clientes los eventos binarios publicados en Redis.
    """
    await websocket.accept()
    channel = get_video_channel()

    try:
        async for payload in subscribe_bytes(channel):
            await websocket.send_bytes(payload)
    except WebSocketDisconnect:
        return
    except Exception as exc:
        await websocket.close(code=1011, reason=f"Error leyendo de Redis: {exc}")
