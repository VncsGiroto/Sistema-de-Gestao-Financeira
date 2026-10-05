"""Épico ledger: transferência debita/credita sem tocar receita/despesa."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture()
async def lac(monkeypatch):
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
    import redis.asyncio as aioredis

    rc = aioredis.from_url(REDIS_URL or "redis://localhost:6379/0", decode_responses=True)
    await rc.flushdb()
    await rc.aclose()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    await engine.dispose()


async def _user(ac: AsyncClient, tag: str):
    email = f"{tag}_{uuid.uuid4().hex[:8]}@exemplo.com"
    r = await ac.post("/api/auth/register", json={"name": tag, "email": email, "password": "segredo-123"})
    assert r.status_code == 201, r.text
    r = await ac.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _account(ac, h, name, initial="0", type_="CHECKING"):
    r = await ac.post(
        "/api/accounts", json={"name": name, "account_type": type_, "initial_balance": initial}, headers=h
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _balance(ac, h, acc_id):
    r = await ac.get(f"/api/accounts/{acc_id}", headers=h)
    assert r.status_code == 200
    return r.json()["current_balance"]


async def test_transfer_debita_credita_sem_receita_despesa(lac):
    ac, h = lac, await _user(lac, "tr")
    a = await _account(ac, h, "Corrente", "1000.00")
    b = await _account(ac, h, "Corretora", "0", "INVESTMENT")

    r = await ac.post(
        "/api/transfers",
        json={"from_account_id": a["id"], "to_account_id": b["id"], "amount": "300.00", "description": "Aporte mensal"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    mv = r.json()
    assert mv["kind"] == "TRANSFER" and mv["amount"] == "300.00"

    assert await _balance(ac, h, a["id"]) == "700.00"
    assert await _balance(ac, h, b["id"]) == "300.00"

    # sem efeito em receita/despesa
    r = await ac.get("/api/dashboard", headers=h)
    assert r.status_code == 200
    assert r.json()["income"]["total"] == "0" and r.json()["expense"]["total"] == "0"

    # lista por conta + exclusão reverte os dois lados
    r = await ac.get("/api/transfers", params={"account_id": b["id"]}, headers=h)
    assert r.status_code == 200 and len(r.json()) == 1
    assert (await ac.delete(f"/api/transfers/{mv['id']}", headers=h)).status_code == 204
    assert await _balance(ac, h, a["id"]) == "1000.00"
    assert await _balance(ac, h, b["id"]) == "0.00"


async def test_transfer_validacoes(lac):
    ac, h = lac, await _user(lac, "trv")
    a = await _account(ac, h, "CA", "100.00")
    b = await _account(ac, h, "CB", "0")

    base = {"from_account_id": a["id"], "to_account_id": b["id"], "amount": "10.00"}
    same = {"from_account_id": b["id"], "to_account_id": b["id"], "amount": "10.00"}
    assert (await ac.post("/api/transfers", json=same, headers=h)).status_code == 422
    assert (await ac.post("/api/transfers", json={**base, "amount": "0"}, headers=h)).status_code == 422
    assert (await ac.post("/api/transfers", json={**base, "amount": "-5"}, headers=h)).status_code == 422
    assert (await ac.post("/api/transfers", json={**base, "from_account_id": 999999}, headers=h)).status_code == 404
    assert (await ac.delete("/api/transfers/999999", headers=h)).status_code == 404


async def test_transfer_isolamento(lac):
    ac = lac
    ha, hb = await _user(ac, "o1"), await _user(ac, "o2")
    a = await _account(ac, ha, "A1", "50.00")
    b = await _account(ac, ha, "B1", "0")
    r = await ac.post(
        "/api/transfers", json={"from_account_id": a["id"], "to_account_id": b["id"], "amount": "10.00"}, headers=ha
    )
    mv = r.json()["id"]

    assert (await ac.get("/api/transfers", headers=hb)).json() == []
    assert (await ac.delete(f"/api/transfers/{mv}", headers=hb)).status_code == 404
    # conta do outro usuário como destino → 404 sem vazar
    c = await _account(ac, hb, "C2", "0")
    r = await ac.post(
        "/api/transfers", json={"from_account_id": a["id"], "to_account_id": c["id"], "amount": "10.00"}, headers=ha
    )
    assert r.status_code == 404
