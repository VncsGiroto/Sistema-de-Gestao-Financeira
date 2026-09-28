from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.finance.router import accounts as accounts_router
from app.modules.finance.router import categories as categories_router
from app.modules.finance.router import transactions as transactions_router
from app.modules.imports.router import router as imports_router
from app.modules.investments.router import router as investments_router
from app.modules.payables.router import router as payables_router

app = FastAPI(title=settings.app_name, docs_url="/api/docs", redoc_url="/api/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(accounts_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(imports_router)
app.include_router(investments_router)
app.include_router(payables_router)
app.include_router(dashboard_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}


@app.get("/api/version")
def version() -> dict:
    return {"version": "0.2.0-mvp"}
