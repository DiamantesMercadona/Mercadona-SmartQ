import json
from functools import lru_cache
from typing import Any, AsyncIterator

from redis.asyncio import Redis

from config import CONFIG


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    redis_config = CONFIG["DATABASE"]
    return Redis(
        host=redis_config["redis_host"],
        port=redis_config["redis_port"],
        db=redis_config.get("redis_db", 0),
        decode_responses=False,
    )


def get_video_channel() -> str:
    return CONFIG["DATABASE"].get("redis_video_channel", "msq:video:events")


def get_video_latest_key() -> str:
    return f"{get_video_channel()}:latest"


async def publish_json(channel: str, payload: dict[str, Any]) -> int:
    message = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    return await get_redis_client().publish(channel, message)


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
        await pubsub.unsubscribe(channel)
        await pubsub.close()


async def ping_redis() -> bool:
    return bool(await get_redis_client().ping())
