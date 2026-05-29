from contextlib import suppress
from functools import lru_cache
from typing import AsyncIterator
import sys
from pathlib import Path

# Manejar importaciones relativas y absolutas
try:
    from ..config import CONFIG
except ImportError:
    BACKEND_DIR = Path(__file__).resolve().parent.parent
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from config import CONFIG

_USE_FAKE_REDIS = CONFIG["DATABASE"]["use_fake_redis"]


@lru_cache(maxsize=1)
def get_redis_client():
    if _USE_FAKE_REDIS:
        import fakeredis.aioredis
        return fakeredis.aioredis.FakeRedis()

    from redis.asyncio import Redis
    redis_config = CONFIG["DATABASE"]
    return Redis(
        host=redis_config["redis_host"],
        port=redis_config["redis_port"],
        db=redis_config.get("redis_db", 0),
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )


def get_video_channel() -> str:
    return CONFIG["DATABASE"].get("redis_video_channel", "msq:video:events")


def get_video_latest_key() -> str:
    return f"{get_video_channel()}:latest"


async def publish_bytes(channel: str, payload: bytes) -> int:
    return await get_redis_client().publish(channel, payload)


async def set_bytes(key: str, payload: bytes) -> bool:
    return bool(await get_redis_client().set(key, payload))


async def get_bytes(key: str) -> bytes | None:
    payload = await get_redis_client().get(key)
    if payload is None:
        return None
    if isinstance(payload, bytes):
        return payload
    return str(payload).encode("utf-8")


async def publish_video_payload(payload: bytes) -> int:
    """
    Guarda el ultimo frame/evento y lo publica en el canal Redis de video.
    """
    await set_bytes(get_video_latest_key(), payload)
    return await publish_bytes(get_video_channel(), payload)


async def get_latest_video_payload() -> bytes | None:
    return await get_bytes(get_video_latest_key())


async def subscribe_bytes(channel: str) -> AsyncIterator[bytes]:
    pubsub = get_redis_client().pubsub()
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue

            payload = message.get("data")
            if isinstance(payload, bytes):
                yield payload
            elif isinstance(payload, str):
                yield payload.encode("utf-8")
    finally:
        with suppress(Exception):
            await pubsub.unsubscribe(channel)
        close = getattr(pubsub, "aclose", pubsub.close)
        with suppress(Exception):
            await close()


async def subscribe_video_payloads(include_latest: bool = False) -> AsyncIterator[bytes]:
    """
    Escucha el canal Redis de video y produce siempre bytes para WebSocket.
    """
    if include_latest:
        latest = await get_latest_video_payload()
        if latest is not None:
            yield latest

    async for payload in subscribe_bytes(get_video_channel()):
        yield payload


async def ping_redis() -> bool:
    return bool(await get_redis_client().ping())
