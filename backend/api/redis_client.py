import json
from functools import lru_cache
from typing import Any

from redis.asyncio import Redis

from config import CONFIG


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    redis_config = CONFIG["DATABASE"]
    return Redis(
        host=redis_config["redis_host"],
        port=redis_config["redis_port"],
        db=redis_config.get("redis_db", 0),
        decode_responses=True,
    )


def get_video_channel() -> str:
    return CONFIG["DATABASE"].get("redis_video_channel", "msq:video:events")


async def publish_json(channel: str, payload: dict[str, Any]) -> int:
    message = json.dumps(payload, ensure_ascii=True)
    return await get_redis_client().publish(channel, message)


async def ping_redis() -> bool:
    return bool(await get_redis_client().ping())
