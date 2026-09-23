"""2.1: accounts/categories com scoping por usuário (cross-user → 404, sem vazar existência)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture()
async def app_client(monkeypatch):
    if not DB_URL:
        pytest.skip("TEST_DATABASE_URL ausente")
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("REDIS_URL", REDIS_URL or "redis://localhost:6379/0")
    import app.core.db as dbmod
    from app.core.db import Base
    from app.main import app

    engine = create_async_engine(DB_URL, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    dbmod.engine = engine
    dbmod.SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    # isola rate-limit/deny-list entre testes
    import redis.asyncio as aioredis

    rc = aioredis.from_url(REDIS_URL or "redis://localhost:6379/0", decode_responses=True)
    await rc.flushdb()
    await rc.aclose()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    await engine.dispose()


async def _user(ac: AsyncClient, tag: str) -> tuple[str, dict]:
    email = f"{tag}_{uuid.uuid4().hex[:8]}@exemplo.com"
    r = await ac.post("/api/auth/register", json={"name": tag, "email": email, "password": "segredo-123"})
    assert r.status_code == 201, r.text
    r = await ac.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    assert r.status_code == 200
    return r.json()["access_token"], {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_accounts_crud_e_isolamento(app_client):
    ac = app_client
    _, ha = await _user(ac, "alice")
    _, hb = await _user(ac, "bob")

    r = await ac.post(
        "/api/accounts",
        json={"name": "Corrente", "bank": "Nubank", "account_type": "CHECKING", "initial_balance": "100.50"},
        headers=ha,
    )
    assert r.status_code == 201, r.text
    acc = r.json()
    assert acc["initial_balance"] == "100.50"

    # tipo inválido → 422
    r = await ac.post("/api/accounts", json={"name": "X", "account_type": "OURO"}, headers=ha)
    assert r.status_code == 422

    # bob não vê nada de alice: lista vazia + get/patch/delete → 404
    r = await ac.get("/api/accounts", headers=hb)
    assert r.status_code == 200 and r.json() == []
    r = await ac.get(f"/api/accounts/{acc['id']}", headers=hb)
    assert r.status_code == 404, r.text
    r = await ac.patch(f"/api/accounts/{acc['id']}", json={"name": "Hack"}, headers=hb)
    assert r.status_code == 404, r.text
    r = await ac.delete(f"/api/accounts/{acc['id']}", headers=hb)
    assert r.status_code == 404, r.text

    # alice opera normal: get, patch, delete
    r = await ac.get(f"/api/accounts/{acc['id']}", headers=ha)
    assert r.status_code == 200
    r = await ac.patch(f"/api/accounts/{acc['id']}", json={"name": "Corrente 2"}, headers=ha)
    assert r.status_code == 200 and r.json()["name"] == "Corrente 2"
    r = await ac.delete(f"/api/accounts/{acc['id']}", headers=ha)
    assert r.status_code == 204
    r = await ac.get(f"/api/accounts/{acc['id']}", headers=ha)
    assert r.status_code == 404

    # sem token → 401
    r = await ac.get("/api/accounts")
    assert r.status_code == 401


async def test_categories_crud_e_uniqueness(app_client):
    ac = app_client
    _, ha = await _user(ac, "carol")
    _, hb = await _user(ac, "dave")

    r = await ac.post("/api/categories", json={"name": "Alimentação", "type": "EXPENSE"}, headers=ha)
    assert r.status_code == 201, r.text
    cat = r.json()

    # mesmo nome+tipo → 409; mesmo nome outro tipo → ok
    r = await ac.post("/api/categories", json={"name": "Alimentação", "type": "EXPENSE"}, headers=ha)
    assert r.status_code == 409
    r = await ac.post("/api/categories", json={"name": "Alimentação", "type": "INCOME"}, headers=ha)
    assert r.status_code == 201

    # filtro por tipo
    r = await ac.get("/api/categories?type=INCOME", headers=ha)
    assert r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["type"] == "INCOME"

    # dave isolado: lista vazia + get → 404
    r = await ac.get("/api/categories", headers=hb)
    assert r.json() == []
    r = await ac.get(f"/api/categories/{cat['id']}", headers=hb)
    assert r.status_code == 404

    # patch + delete da dona
    r = await ac.patch(f"/api/categories/{cat['id']}", json={"name": "Comida"}, headers=ha)
    assert r.status_code == 200 and r.json()["name"] == "Comida"
    r = await ac.delete(f"/api/categories/{cat['id']}", headers=ha)
    assert r.status_code == 204
