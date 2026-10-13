import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.messages import router as messages_router
from app.api.rooms import router as rooms_router
from app.core.redis import redis_client
from app.ws.chat import router as ws_router
from app.ws.pubsub import run_subscriber


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: background task shuru karo
    subscriber_task = asyncio.create_task(run_subscriber())
    yield
    # shutdown: task rokko, Redis connection band karo
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass
    await redis_client.aclose()


app = FastAPI(title="Realtime Chat Engine", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(messages_router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}