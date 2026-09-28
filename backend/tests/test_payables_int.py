"""Payables int: CRUD 4 kinds + upcoming + schedule + pay + isolamento."""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture()
async def pac(monkeypatch):
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


async def _account(ac, h) -> int:
    r = await ac.post("/api/accounts", json={"name": "Conta", "account_type": "CHECKING"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _category(ac, h, name="Moradia") -> int:
    r = await ac.post("/api/categories", json={"name": name, "type": "EXPENSE"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_crud_4_kinds(pac):
    ac, h = pac, await _user(pac, "k1")
    today = date.today()

    r = await ac.post(
        "/api/payables",
        json={
            "description": "Financiamento",
            "kind": "FIXED",
            "amount": "1500",
            "periodicity": "MONTHLY",
            "due_day": 10,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    fixed = r.json()
    assert fixed["next_due"] is not None

    r = await ac.post(
        "/api/payables",
        json={"description": "Luz", "kind": "RECURRING", "amount": "180", "periodicity": "MONTHLY", "due_day": 10},
        headers=h,
    )
    assert r.status_code == 201, r.text

    r = await ac.post(
        "/api/payables",
        json={
            "description": "Notebook",
            "kind": "INSTALLMENT",
            "total_amount": "6000",
            "num_installments": 12,
            "first_due_date": "2026-09-10",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    inst = r.json()
    assert inst["installment_amount"] == "500.00"

    r = await ac.post(
        "/api/payables",
        json={"description": "Jantar", "kind": "ONE_TIME", "amount": "120", "next_due": "2026-10-05"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    one = r.json()

    # shapes inválidos → 422
    bad = [
        {"description": "X", "kind": "FIXED", "amount": "10", "periodicity": "MONTHLY"},  # sem due_day
        {"description": "X", "kind": "ONE_TIME", "amount": "10"},  # sem next_due
        {"description": "X", "kind": "ONE_TIME", "amount": "10", "next_due": "2026-10-05", "due_day": 5},
        {
            "description": "X",
            "kind": "INSTALLMENT",
            "total_amount": "100",
            "num_installments": 2,
            "first_due_date": "2026-09-10",
            "amount": "50",
        },
        {
            "description": "X",
            "kind": "RECURRING",
            "amount": "10",
            "periodicity": "MONTHLY",
            "due_day": 10,
            "next_due": "2026-10-10",
        },
    ]
    for body in bad:
        assert (await ac.post("/api/payables", json=body, headers=h)).status_code == 422, body

    # filtro por kind + get + patch + delete
    r = await ac.get("/api/payables", params={"kind": "ONE_TIME"}, headers=h)
    assert r.status_code == 200 and len(r.json()) == 1
    assert (
        await ac.patch(f"/api/payables/{one['id']}", json={"description": "Jantar X"}, headers=h)
    ).status_code == 200
    assert (await ac.patch(f"/api/payables/{fixed['id']}", json={"amount": "1600"}, headers=h)).status_code == 200
    assert (await ac.delete(f"/api/payables/{one['id']}", headers=h)).status_code == 204
    assert (await ac.get(f"/api/payables/{one['id']}", headers=h)).status_code == 404
    _ = today


async def test_upcoming_schedule(pac):
    ac, h = pac, await _user(pac, "k2")
    r = await ac.post(
        "/api/payables",
        json={"description": "Perto", "kind": "FIXED", "amount": "10", "periodicity": "MONTHLY", "due_day": 1},
        headers=h,
    )
    assert r.status_code == 201, r.text
    r = await ac.post(
        "/api/payables",
        json={"description": "Longe", "kind": "ONE_TIME", "amount": "10", "next_due": "2099-01-01"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    r = await ac.post(
        "/api/payables",
        json={
            "description": "Parc",
            "kind": "INSTALLMENT",
            "total_amount": "1200",
            "num_installments": 12,
            "first_due_date": (date.today() + timedelta(days=5)).isoformat(),
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    r = await ac.get("/api/payables/upcoming", params={"days": 60}, headers=h)
    assert r.status_code == 200
    assert {p["description"] for p in r.json()} == {"Perto", "Parc"}

    r = await ac.get(f"/api/payables/{pid}/schedule", headers=h)
    assert r.status_code == 200 and len(r.json()) == 12
    assert all(not s["paid"] for s in r.json())
    assert sum(Decimal(s["amount"]) for s in r.json()) == Decimal("1200")

    # schedule em não-parcela → 422
    r = await ac.get("/api/payables", params={"kind": "FIXED"}, headers=h)
    assert (await ac.get(f"/api/payables/{r.json()[0]['id']}/schedule", headers=h)).status_code == 422


async def test_pay_recorrente_e_unica(pac):
    ac, h = pac, await _user(pac, "k3")
    acc, cat = await _account(ac, h), await _category(ac, h)

    r = await ac.post(
        "/api/payables",
        json={
            "description": "Internet",
            "kind": "FIXED",
            "amount": "120",
            "periodicity": "MONTHLY",
            "due_day": 10,
            "category_id": cat,
        },
        headers=h,
    )
    pid, old_next = r.json()["id"], r.json()["next_due"]

    # FIXED com valor divergente → 422
    r = await ac.post(f"/api/payables/{pid}/pay", json={"account_id": acc, "amount": "100"}, headers=h)
    assert r.status_code == 422

    r = await ac.post(f"/api/payables/{pid}/pay", json={"account_id": acc}, headers=h)
    assert r.status_code == 200, r.text
    out = r.json()
    assert len(out["transactions"]) == 1
    assert out["transactions"][0]["amount"] == "120.00"
    assert out["payable"]["next_due"] != old_next  # avançou

    # transação existe no extrato com source PAYABLE e categoria herdada
    txid = out["transactions"][0]["id"]
    r = await ac.get(f"/api/transactions/{txid}", headers=h)
    assert r.status_code == 200 and r.json()["category_id"] == cat

    # RECURRING atualiza estimativa ao pagar outro valor
    r = await ac.post(
        "/api/payables",
        json={"description": "Luz", "kind": "RECURRING", "amount": "180", "periodicity": "MONTHLY", "due_day": 10},
        headers=h,
    )
    rid = r.json()["id"]
    r = await ac.post(f"/api/payables/{rid}/pay", json={"account_id": acc, "amount": "210"}, headers=h)
    assert r.status_code == 200 and r.json()["payable"]["amount"] == "210.00"

    # ONE_TIME: paga uma vez; segunda → 409... (409 não existe: PayableError → 422)
    r = await ac.post(
        "/api/payables",
        json={"description": "Show", "kind": "ONE_TIME", "amount": "90", "next_due": "2026-11-01"},
        headers=h,
    )
    oid = r.json()["id"]
    assert (await ac.post(f"/api/payables/{oid}/pay", json={"account_id": acc}, headers=h)).status_code == 200
    assert (await ac.post(f"/api/payables/{oid}/pay", json={"account_id": acc}, headers=h)).status_code == 422


async def test_pay_parcela_com_desconto(pac):
    ac, h = pac, await _user(pac, "k4")
    acc = await _account(ac, h)
    r = await ac.post(
        "/api/payables",
        json={
            "description": "Curso",
            "kind": "INSTALLMENT",
            "total_amount": "1000",
            "num_installments": 3,
            "first_due_date": "2026-09-10",
        },
        headers=h,
    )
    pid = r.json()["id"]

    # default: próxima não-paga
    r = await ac.post(f"/api/payables/{pid}/pay", json={"account_id": acc}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["payable"]["paid_ns"] == [1]

    # antecipa 2+3 com 150 de desconto, rateado
    r = await ac.post(
        f"/api/payables/{pid}/pay",
        json={"account_id": acc, "ns": [2, 3], "discount": "150.00", "date": "2026-09-12"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    txs = r.json()["transactions"]
    assert len(txs) == 2
    total_net = sum(Decimal(t["amount"]) for t in txs)
    # 1000 - 333.33 (paga) - 150 (desconto) = 516.67
    assert total_net == Decimal("516.67"), total_net
    assert r.json()["payable"]["paid_ns"] == [1, 2, 3]

    # pagar de novo → 422 (tudo pago); n inválido → 422
    assert (await ac.post(f"/api/payables/{pid}/pay", json={"account_id": acc}, headers=h)).status_code == 422

    # schedule marca pagas
    r = await ac.get(f"/api/payables/{pid}/schedule", headers=h)
    assert all(s["paid"] for s in r.json())


async def test_pay_isolamento(pac):
    ac = pac
    h1, h2 = await _user(pac, "o1"), await _user(pac, "o2")
    acc = await _account(ac, h1)
    r = await ac.post(
        "/api/payables",
        json={"description": "Xx", "kind": "ONE_TIME", "amount": "10", "next_due": "2026-10-01"},
        headers=h1,
    )
    pid = r.json()["id"]
    assert (await ac.get("/api/payables", headers=h2)).json() == []
    assert (await ac.get(f"/api/payables/{pid}", headers=h2)).status_code == 404
    assert (await ac.post(f"/api/payables/{pid}/pay", json={"account_id": acc}, headers=h2)).status_code == 404
