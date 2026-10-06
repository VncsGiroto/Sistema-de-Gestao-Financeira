"""Movimentações unificadas: uma linha por evento, sem duplicar nem converter."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture()
async def mac(monkeypatch):
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


async def _fluxo_completo(ac, h):
    """Corrente 5000 → transfere 1000 → aporte 1000 → preço 110 → rendimento 100 → reinvest 50."""
    r = await ac.post(
        "/api/accounts", json={"name": "Corrente", "account_type": "CHECKING", "initial_balance": "5000.00"}, headers=h
    )
    cc = r.json()["id"]
    r = await ac.post("/api/accounts", json={"name": "Corretora", "account_type": "INVESTMENT"}, headers=h)
    br = r.json()["id"]
    r = await ac.post(
        "/api/assets",
        json={"ticker": "FII11", "asset_class": "FUNDOS", "subtype": "FII", "account_id": br},
        headers=h,
    )
    aid = r.json()["id"]
    r = await ac.post(
        "/api/transfers", json={"from_account_id": cc, "to_account_id": br, "amount": "1000.00"}, headers=h
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]
    for body in [
        {"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"},
        {"kind": "RENDIMENTO", "date": "2026-02-10", "amount": "100.00", "account_id": br},
        {"kind": "REINVESTIMENTO", "date": "2026-02-10", "quantity": "0.5", "price": "100.00"},
    ]:
        r = await ac.post(f"/api/assets/{aid}/ops", json=body, headers=h)
        assert r.status_code == 201, (body, r.text)
    r = await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-02-15", "price": "110.00"}, headers=h)
    assert r.status_code == 201, r.text
    return cc, br, aid, tid


async def test_uma_linha_por_evento(mac):
    ac, h = mac, await _user(mac, "uni")
    cc, br, aid, tid = await _fluxo_completo(ac, h)

    r = await ac.get("/api/movements", params={"per_page": 100}, headers=h)
    assert r.status_code == 200, r.text
    items = r.json()["data"]
    kinds = sorted(i["kind"] for i in items)
    # transferência, aporte, rendimento (1x, como receita), reinvestimento (neutro)
    assert kinds == ["APORTE", "REINVESTIMENTO", "RENDIMENTO", "TRANSFER"]
    by_kind = {i["kind"]: i for i in items}
    assert by_kind["TRANSFER"]["direction"] == "neutral"  # consolidado: nem in nem out
    assert by_kind["TRANSFER"]["cash_impact"] == "0.00"
    assert by_kind["APORTE"]["direction"] == "out" and by_kind["APORTE"]["cash_impact"] == "-1000.00"
    assert by_kind["RENDIMENTO"]["direction"] == "in" and by_kind["RENDIMENTO"]["cash_impact"] == "100.00"
    assert by_kind["REINVESTIMENTO"]["direction"] == "neutral" and by_kind["REINVESTIMENTO"]["cash_impact"] == "0.00"
    assert by_kind["RENDIMENTO"]["editable"] is False and by_kind["RENDIMENTO"]["origin"] == "operation"
    assert by_kind["REINVESTIMENTO"]["editable"] is False and by_kind["REINVESTIMENTO"]["ticker"] == "FII11"
    assert by_kind["TRANSFER"]["editable"] is True and by_kind["TRANSFER"]["origin"] == "transfer"

    # saldos: transferência move dos dois lados; aporte consome; sem receita/despesa fantasma
    assert (await ac.get(f"/api/accounts/{cc}", headers=h)).json()["current_balance"] == "4000.00"
    assert (await ac.get(f"/api/accounts/{br}", headers=h)).json()["current_balance"] == "100.00"
    d = (await ac.get("/api/dashboard", params={"from": "2026-01-01", "to": "2026-12-31"}, headers=h)).json()
    from decimal import Decimal as D

    assert D(d["income"]["total"]) == D("100.00") and D(d["expense"]["total"]) == 0
    r = await ac.get("/api/transactions", params={"type": "EXPENSE", "per_page": 50}, headers=h)
    assert r.json()["meta"]["total"] == 0


async def test_filtro_conta_mostra_os_dois_lados(mac):
    ac, h = mac, await _user(mac, "side")
    cc, br, aid, tid = await _fluxo_completo(ac, h)

    r = await ac.get("/api/movements", params={"account_id": cc, "per_page": 100}, headers=h)
    got = {i["kind"]: i for i in r.json()["data"]}
    assert got["TRANSFER"]["direction"] == "out"  # origem
    assert set(got) == {"TRANSFER"}  # ops/reinvestimento são da corretora

    r = await ac.get("/api/movements", params={"account_id": br, "per_page": 100}, headers=h)
    got = {i["kind"]: i for i in r.json()["data"]}
    assert got["TRANSFER"]["direction"] == "in"  # destino
    assert got["APORTE"]["direction"] == "out"
    assert got["RENDIMENTO"]["direction"] == "in"
    assert got["REINVESTIMENTO"]["direction"] == "neutral"  # visível, sem mexer no saldo

    # conta inexistente → 404; kind inválido → 422
    assert (await ac.get("/api/movements", params={"account_id": 999999}, headers=h)).status_code == 404
    assert (await ac.get("/api/movements", params={"kind": "PIX"}, headers=h)).status_code == 422


async def test_paginacao_ordenacao_isolamento_e_csv(mac):
    ac, h = mac, await _user(mac, "page")
    cc, br, aid, tid = await _fluxo_completo(ac, h)

    p1 = (await ac.get("/api/movements", params={"per_page": 2, "page": 1}, headers=h)).json()
    p2 = (await ac.get("/api/movements", params={"per_page": 2, "page": 2}, headers=h)).json()
    assert p1["meta"]["total"] == 4 and p2["meta"]["total"] == 4
    assert [i["id"] for i in p1["data"]] != [i["id"] for i in p2["data"]]
    dates = [i["date"] for i in p1["data"] + p2["data"]]
    assert dates == sorted(dates, reverse=True)

    h2 = await _user(mac, "outro")
    assert (await ac.get("/api/movements", headers=h2)).json()["meta"]["total"] == 0

    r = await ac.get("/api/movements/export/csv", headers=h)
    assert r.status_code == 200 and "RENDIMENTO" in r.text and "REINVESTIMENTO" in r.text
