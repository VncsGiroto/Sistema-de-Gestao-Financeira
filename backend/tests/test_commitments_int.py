"""Agenda de compromissos sobre payables + isolamento (int)."""

import uuid
from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
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
    await ac.post("/api/auth/register", json={"name": f"User {tag}", "email": email, "password": "segredo-123"})
    r = await ac.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_commitments_agenda(cac):
    ac, h = cac, await _user(cac, "ag")
    today = date.today()
    in_h = (today + timedelta(days=10)).isoformat()

    r = await ac.post(
        "/api/payables",
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
        "/api/payables",
        json={"description": "Longe", "amount": "10", "kind": "ONE_TIME", "next_due": "2099-01-01"},
        headers=h,
    )
    assert r.status_code == 201

    r = await ac.post(
        "/api/payables",
        json={
            "description": "Nb",
            "kind": "INSTALLMENT",
            "total_amount": "1200.00",
            "num_installments": 12,
            "first_due_date": in_h,
        },
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
    h2 = await _user(cac, "z2")
    r = await ac.get("/api/dashboard/commitments", headers=h2)
    assert r.json() == {"total": "0", "items": [], "unassigned_total": "0"}


async def test_commitments_recorrencia_expandida_e_filtro_conta(cac):
    """1.2+1.3: mensal em 100d aparece 3×; filtro por conta + sem-conta vai p/ unassigned."""
    ac, h = cac, await _user(cac, "agx")
    today = date.today()
    in5 = (today + timedelta(days=5)).isoformat()

    async def account(name):
        r = await ac.post("/api/accounts", json={"name": name, "account_type": "CHECKING"}, headers=h)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    acc1, acc2 = await account("C1"), await account("C2")

    async def payable(body):
        r = await ac.post("/api/payables", json=body, headers=h)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    net_body = {"description": "Net", "kind": "FIXED", "amount": "100", "periodicity": "MONTHLY", "due_day": 1}
    await payable({**net_body, "account_id": acc1})
    await payable({"description": "Livre", "kind": "FIXED", "amount": "50", "periodicity": "MONTHLY", "due_day": 1})
    await payable({"description": "Unica", "kind": "ONE_TIME", "amount": "10", "next_due": in5, "account_id": acc2})

    r = await ac.get("/api/dashboard/commitments", params={"horizon_days": 100}, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    net = [i for i in d["items"] if i["description"].startswith("Net")]
    assert len(net) == 3  # next_due + 2 ocorrências mensais
    assert d["unassigned_total"] == "0"  # sem filtro, tudo entra nos itens
    assert float(d["total"]) == sum(float(i["amount"]) for i in d["items"])

    r = await ac.get("/api/dashboard/commitments", params={"horizon_days": 100, "account_id": acc1}, headers=h)
    d1 = r.json()
    assert {i["description"].split(" (")[0] for i in d1["items"]} == {"Net"}
    assert d1["unassigned_total"] == "150.00"  # 3× Livre, sem conta: fora da projeção, sinalizado

    r = await ac.get("/api/dashboard/commitments", params={"horizon_days": 100, "account_id": acc2}, headers=h)
    d2 = r.json()
    assert [i["description"] for i in d2["items"]] == ["Unica"]

    assert (await ac.get("/api/dashboard/commitments", params={"account_id": 999999}, headers=h)).status_code == 404
