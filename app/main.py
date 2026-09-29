from fastapi import FastAPI

app = FastAPI(title="Realtime Chat Engine")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}