from fastapi import FastAPI

from app.api.auth import router as auth_router

app = FastAPI(title="Realtime Chat Engine")
app.include_router(auth_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}