import asyncio
import json
import logging
import uuid

from app.core.redis import redis_client
from app.ws.manager import manager

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "room:"


async def publish_to_room(room_id: uuid.UUID, message: dict) -> None:
    await redis_client.publish(f"{CHANNEL_PREFIX}{room_id}", json.dumps(message))


async def run_subscriber() -> None:
    """Runs for the whole life of the server. Listens to every room channel
    and forwards each message to the connections held by THIS instance."""
    while True:
        pubsub = redis_client.pubsub()
        try:
            await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
            async for item in pubsub.listen():
                if item["type"] != "pmessage":
                    continue  # skip subscribe confirmations
                try:
                    room_id = uuid.UUID(item["channel"].removeprefix(CHANNEL_PREFIX))
                    payload = json.loads(item["data"])
                except (ValueError, json.JSONDecodeError):
                    logger.warning("Ignoring malformed pubsub message: %s", item)
                    continue
                await manager.broadcast_to_room(room_id, payload)
        except Exception:
            logger.exception("Redis subscriber error, retrying in 1s")
            await asyncio.sleep(1)
        finally:
            await pubsub.aclose()