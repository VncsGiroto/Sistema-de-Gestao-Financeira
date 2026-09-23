"""Agenda de compromissos + auditoria de valor (int)."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture()
async def cac(monkeypatch):
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


async def test_commitments_agenda(cac):
    ac, h = cac, await _user(cac, "ag")
    today = date.today()
    in_h = (today + timedelta(days=10)).isoformat()

    r = await ac.post(
        "/api/bills",
        json={
            "description": "Internet",
            "amount": "120.00",
            "kind": "FIXED",
            "periodicity": "MONTHLY",
            "due_day": today.day,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    r = await ac.post(
        "/api/bills",
        json={"description": "Longe", "amount": "10", "kind": "ONE_TIME", "next_due": "2099-01-01"},
        headers=h,
    )
    assert r.status_code == 201

    r = await ac.post(
        "/api/installments",
        json={"description": "Nb", "total_amount": "1200.00", "num_installments": 12, "first_due_date": in_h},
        headers=h,
    )
    assert r.status_code == 201, r.text

    r = await ac.get("/api/dashboard/commitments", params={"horizon_days": 60}, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    kinds = {i["kind"] for i in d["items"]}
    assert kinds == {"bill", "installment"}
    assert all(i["due_date"] != "2099-01-01" for i in d["items"])  # Longe fora do horizonte
    dates = [i["due_date"] for i in d["items"]]
    assert dates == sorted(dates)
    assert float(d["total"]) == sum(float(i["amount"]) for i in d["items"])

    # isolamento: outro usuário vê vazio
    h2 = await _user(cac, "zz")
    r = await ac.get("/api/dashboard/commitments", headers=h2)
    assert r.json() == {"total": "0", "items": []}


async def test_bill_amount_audit(cac):
    from app.core.db import SessionLocal
    from app.modules.auth.audit_models import AuditLog

    ac, h = cac, await _user(cac, "au")
    r = await ac.post(
        "/api/bills",
        json={"description": "Luz", "amount": "180.00", "kind": "VARIABLE", "periodicity": "MONTHLY", "due_day": 10},
        headers=h,
    )
    bid = r.json()["id"]

    r = await ac.patch(f"/api/bills/{bid}", json={"amount": "220.00"}, headers=h)
    assert r.status_code == 200 and r.json()["amount"] == "220.00"

    async with SessionLocal() as session:
        rows = list(
            (await session.execute(select(AuditLog).where(AuditLog.action == "bill.amount_changed"))).scalars().all()
        )
    assert len(rows) == 1
    assert rows[0].meta == {"old": "180.00", "new": "220.00"}

    # patch sem amount não audita
    await ac.patch(f"/api/bills/{bid}", json={"description": "Luz Fibra"}, headers=h)
    async with SessionLocal() as session:
        n = len(
            list(
                (await session.execute(select(AuditLog).where(AuditLog.action == "bill.amount_changed")))
                .scalars()
                .all()
            )
        )
    assert n == 1
