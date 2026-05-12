from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .redis_client import get_video_channel, ping_redis, publish_bytes, publish_json

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
    channel = get_video_channel()

    try:
        subscribers = await publish_json(channel, payload)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo publicar en Redis: {exc}")

    return {
        "message": "Evento publicado en Redis",
        "channel": channel,
        "subscribers": subscribers,
        "event": payload,
    }


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
