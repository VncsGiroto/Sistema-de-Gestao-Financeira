"""5.1 int: dashboard com massa conhecida + filtros + isolamento."""

import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture()
async def dash(monkeypatch):
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
    await ac.post("/api/auth/register", json={"name": tag, "email": email, "password": "segredo-123"})
    r = await ac.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_dashboard_massa_conhecida(dash):
    ac, h = dash, await _user(dash, "db")
    r = await ac.post(
        "/api/accounts", json={"name": "C1", "account_type": "CHECKING", "initial_balance": "1000.00"}, headers=h
    )
    assert r.status_code == 201, r.text
    acc = r.json()["id"]
    r = await ac.post("/api/categories", json={"name": "Moradia", "type": "EXPENSE"}, headers=h)
    mor = r.json()["id"]
    r = await ac.post("/api/categories", json={"name": "Salário", "type": "INCOME"}, headers=h)
    sal = r.json()["id"]

    for a, c, d, desc, amt, t in [
        (acc, sal, "2026-09-05", "SAL", "8000", "INCOME"),
        (acc, None, "2026-09-06", "FREELA", "1500", "INCOME"),
        (acc, mor, "2026-09-10", "ALUGUEL", "-2000", "EXPENSE"),
        (acc, mor, "2026-08-10", "ALUGUEL ANT", "-2000", "EXPENSE"),
    ]:
        body = {"account_id": a, "date": d, "description": desc, "amount": amt, "type": t}
        if c:
            body["category_id"] = c
        r = await ac.post("/api/transactions", json=body, headers=h)
        assert r.status_code == 201, r.text

    r = await ac.get("/api/dashboard", params={"from": "2026-09-01", "to": "2026-09-30"}, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()

    def D(v):
        return Decimal(str(v))

    assert D(d["income"]["total"]) == Decimal("9500")
    assert D(d["expense"]["total"]) == Decimal("2000")
    assert D(d["balance"]) == Decimal("6500")  # cumulativo: 1000 + 9500 - 4000 (inclui ALUGUEL ANT de ago)
    assert {c["name"]: D(c["total"]) for c in d["income"]["by_category"]} == {
        "Salário": Decimal("8000"),
        "Sem categoria": Decimal("1500"),
    }
    assert {c["name"]: D(c["total"]) for c in d["expense"]["by_category"]} == {"Moradia": Decimal("2000")}
    assert len(d["evolution"]) == 1 and d["evolution"][0]["month"] == "2026-09"
    assert D(d["evolution"][0]["income"]) == Decimal("9500") and D(d["evolution"][0]["expense"]) == Decimal("2000")

    # filtro conta inexistente → 404; sem token → 401
    assert (await ac.get("/api/dashboard", params={"account_id": 999999}, headers=h)).status_code == 404
    assert (await ac.get("/api/dashboard", params={"from": "2026-09-01", "to": "2026-09-30"})).status_code == 401

    # outro usuário vê zerado
    h2 = await _user(dash, "zz")
    r = await ac.get("/api/dashboard", params={"from": "2026-09-01", "to": "2026-09-30"}, headers=h2)
    assert Decimal(str(r.json()["balance"])) == 0 and Decimal(str(r.json()["income"]["total"])) == 0
