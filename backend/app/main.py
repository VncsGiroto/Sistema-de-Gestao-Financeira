from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title=settings.app_name, docs_url="/api/docs", redoc_url="/api/redoc")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/version")
def version() -> dict:
    return {"version": "0.1.0-mvp-etapa1"}
