from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.rooms import router as rooms_router
from app.api.messages import router as messages_router

app = FastAPI(title="Realtime Chat Engine")
app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(messages_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}