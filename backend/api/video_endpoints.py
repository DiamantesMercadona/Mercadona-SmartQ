from fastapi import APIRouter, Body, HTTPException, Response, WebSocket, WebSocketDisconnect

from .redis_client import (
    get_latest_video_payload,
    get_video_channel,
    ping_redis,
    publish_video_payload,
    subscribe_video_payloads,
)

router = APIRouter()


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
async def publish_video_event(payload: bytes = Body(media_type="application/octet-stream")):
    """
    Recibe bytes del simulador/camara y los publica en Redis Pub/Sub.
    """
    channel = get_video_channel()

    if not payload:
        raise HTTPException(status_code=400, detail="El payload binario no puede estar vacio")

    try:
        subscribers = await publish_video_payload(payload)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo publicar en Redis: {exc}")

    return {
        "message": "Evento publicado en Redis",
        "channel": channel,
        "subscribers": subscribers,
        "bytes": len(payload),
    }


@router.get("/video/events/latest")
async def get_latest_video_event():
    """
    Devuelve el ultimo evento de video guardado en Redis como bytes.
    """
    try:
        payload = await get_latest_video_payload()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"No se pudo leer de Redis: {exc}")

    if payload is None:
        raise HTTPException(status_code=404, detail="No hay eventos de video publicados")

    return Response(content=payload, media_type="application/octet-stream")


@router.websocket("/ws/video")
async def video_stream(websocket: WebSocket):
    """
    WebSocket de entrada: recibe bytes del simulador y los reenvia a Redis.
    """
    await websocket.accept()
    channel = get_video_channel()

    try:
        while True:
            payload = await websocket.receive_bytes()
            subscribers = await publish_video_payload(payload)
            await websocket.send_bytes(
                f"ok channel={channel} subscribers={subscribers} bytes={len(payload)}".encode("utf-8")
            )
    except WebSocketDisconnect:
        return
    except RuntimeError:
        await websocket.close(code=1003, reason="Solo se aceptan mensajes binarios")
    except Exception as exc:
        await websocket.close(code=1011, reason=f"Error publicando en Redis: {exc}")


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
