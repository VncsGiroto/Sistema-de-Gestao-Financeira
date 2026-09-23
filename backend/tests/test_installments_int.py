"""4.2 int: CRUD installments + schedule + isolamento (backend, sem tela)."""

import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture()
async def iac(monkeypatch):
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
    r = await ac.post("/api/auth/register", json={"name": f"User {tag}", "email": email, "password": "segredo-123"})
    assert r.status_code == 201, r.text
    r = await ac.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_installments_crud_schedule(iac):
    ac, h = iac, await _user(iac, "parc")
    r = await ac.post("/api/accounts", json={"name": "Cartão", "account_type": "CREDIT_CARD"}, headers=h)
    acc = r.json()["id"]

    r = await ac.post(
        "/api/installments",
        json={
            "description": "Notebook",
            "total_amount": "6000.00",
            "num_installments": 12,
            "first_due_date": "2026-09-10",
            "account_id": acc,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    inst = r.json()
    assert inst["installment_amount"] == "500.00"

    # schedule soma == total
    r = await ac.get(f"/api/installments/{inst['id']}/schedule", headers=h)
    assert r.status_code == 200
    sched = r.json()
    assert len(sched) == 12
    assert sum(Decimal(s["amount"]) for s in sched) == Decimal("6000.00")
    assert sched[0]["due_date"] == "2026-09-10" and sched[-1]["due_date"] == "2027-08-10"

    # validações: 1 parcela, total zero, conta inexistente
    for body in [
        {"description": "X", "total_amount": "100", "num_installments": 1, "first_due_date": "2026-09-10"},
        {"description": "X", "total_amount": "0", "num_installments": 2, "first_due_date": "2026-09-10"},
        {
            "description": "X",
            "total_amount": "100",
            "num_installments": 2,
            "first_due_date": "2026-09-10",
            "account_id": 999999,
        },
    ]:
        assert (await ac.post("/api/installments", json=body, headers=h)).status_code in (404, 422)

    # patch descrição + delete
    r = await ac.patch(f"/api/installments/{inst['id']}", json={"description": "Notebook Pro"}, headers=h)
    assert r.status_code == 200 and r.json()["description"] == "Notebook Pro"
    assert (await ac.delete(f"/api/installments/{inst['id']}", headers=h)).status_code == 204
    assert (await ac.get(f"/api/installments/{inst['id']}", headers=h)).status_code == 404


async def test_installments_isolamento(iac):
    ac = iac
    h1, h2 = await _user(iac, "a"), await _user(iac, "b")
    r = await ac.post(
        "/api/installments",
        json={"description": "Curso", "total_amount": "1000.00", "num_installments": 3, "first_due_date": "2026-09-10"},
        headers=h1,
    )
    iid = r.json()["id"]
    assert (await ac.get("/api/installments", headers=h2)).json() == []
    assert (await ac.get(f"/api/installments/{iid}", headers=h2)).status_code == 404
    assert (await ac.get(f"/api/installments/{iid}/schedule", headers=h2)).status_code == 404
