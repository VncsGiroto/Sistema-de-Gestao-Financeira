"""7.1/7.2b int: assets + ops + position + preços + isolamento."""

import uuid
from datetime import timedelta

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
    await ac.post("/api/auth/register", json={"name": f"User {tag}", "email": email, "password": "segredo-123"})
    r = await ac.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_assets_ops_position(iac):
    ac, h = iac, await _user(iac, "inv")
    r = await ac.post("/api/accounts", json={"name": "Corretora", "account_type": "CHECKING"}, headers=h)
    acc = r.json()["id"]
    r = await ac.post("/api/categories", json={"name": "Dividendos", "type": "INCOME"}, headers=h)
    div = r.json()["id"]
    r = await ac.post(
        "/api/assets",
        json={
            "ticker": "petr4",
            "name": "Petrobras PN",
            "asset_class": "RENDA_VARIAVEL",
            "subtype": "ACAO",
            "custodian": "XP",
            "category_id": div,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    asset = r.json()
    assert asset["ticker"] == "PETR4"  # normalizado
    aid = asset["id"]

    # ticker duplicado → 409
    r = await ac.post(
        "/api/assets", json={"ticker": "PETR4", "asset_class": "RENDA_VARIAVEL", "subtype": "ACAO"}, headers=h
    )
    assert r.status_code == 409

    # classe inválida → 422
    r = await ac.post("/api/assets", json={"ticker": "X", "asset_class": "IMOVEL", "subtype": "CASA"}, headers=h)
    assert r.status_code == 422

    async def op(body):
        r = await ac.post(f"/api/assets/{aid}/ops", json=body, headers=h)
        assert r.status_code == 201, (body, r.text)
        return r.json()

    await op({"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "40.00"})
    await op({"kind": "APORTE", "date": "2026-02-10", "quantity": "10", "price": "60.00", "fees": "10.00"})
    # RENDIMENTO sem conta → 422; com conta → 201 + INCOME no extrato (categoria default do ativo)
    r = await ac.post(
        f"/api/assets/{aid}/ops", json={"kind": "RENDIMENTO", "date": "2026-03-01", "amount": "25.00"}, headers=h
    )
    assert r.status_code == 422
    r = await ac.post(
        f"/api/assets/{aid}/ops",
        json={"kind": "RENDIMENTO", "date": "2026-03-01", "amount": "25.00", "account_id": acc},
        headers=h,
    )
    assert r.status_code == 201, r.text
    div_tx = r.json()["transaction_id"]
    r = await ac.get(f"/api/transactions/{div_tx}", headers=h)
    assert r.status_code == 200 and r.json()["type"] == "INCOME"
    assert r.json()["category_id"] == div and r.json()["amount"] == "25.00"
    # resgate além da posição → 422
    r = await ac.post(
        f"/api/assets/{aid}/ops",
        json={"kind": "RESGATE", "date": "2026-03-05", "quantity": "99", "price": "50"},
        headers=h,
    )
    assert r.status_code == 422
    await op({"kind": "RESGATE", "date": "2026-03-05", "quantity": "4", "price": "50.00"})

    r = await ac.get(f"/api/assets/{aid}/position", headers=h)
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["quantity"] == "16" and p["average_price"] == "50.50"  # (400+610)/20
    assert p["invested"] == "808.00" and p["aportes"] == "1010.00"
    assert p["resgates"] == "200.00" and p["rendimentos"] == "25.00"
    assert p["current_price"] is None  # 7.2 preenche

    # filtro por classe
    r = await ac.get("/api/assets", params={"asset_class": "RENDA_VARIAVEL"}, headers=h)
    assert len(r.json()) == 1
    r = await ac.get("/api/assets", params={"asset_class": "CRIPTO"}, headers=h)
    assert r.json() == []

    # ativo com ops não exclui → 409; após limpar ops, exclui (tx do rendimento vai junto)
    assert (await ac.delete(f"/api/assets/{aid}", headers=h)).status_code == 409
    r = await ac.get(f"/api/assets/{aid}/ops", headers=h)
    for o in r.json():
        assert (await ac.delete(f"/api/assets/{aid}/ops/{o['id']}", headers=h)).status_code == 204
    assert (await ac.delete(f"/api/assets/{aid}", headers=h)).status_code == 204
    assert (await ac.get(f"/api/transactions/{div_tx}", headers=h)).status_code == 404


async def test_assets_isolamento(iac):
    ac = iac
    h1, h2 = await _user(iac, "u1"), await _user(iac, "u2")
    r = await ac.post(
        "/api/assets", json={"ticker": "VALE3", "asset_class": "RENDA_VARIAVEL", "subtype": "ACAO"}, headers=h1
    )
    aid = r.json()["id"]
    assert (await ac.get("/api/assets", headers=h2)).json() == []
    assert (await ac.get(f"/api/assets/{aid}", headers=h2)).status_code == 404
    assert (await ac.get(f"/api/assets/{aid}/position", headers=h2)).status_code == 404


async def test_manual_price_enriquece_position(iac):
    ac, h = iac, await _user(iac, "mn")
    r = await ac.post(
        "/api/assets", json={"ticker": "ACAO7", "asset_class": "RENDA_VARIAVEL", "subtype": "ACAO"}, headers=h
    )
    aid = r.json()["id"]
    r = await ac.post(
        f"/api/assets/{aid}/ops",
        json={"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "40"},
        headers=h,
    )
    assert r.status_code == 201

    # sem preço: nulos
    r = await ac.get(f"/api/assets/{aid}/position", headers=h)
    assert r.json()["current_price"] is None and r.json()["pnl"] is None

    # preço manual do dia: valoriza (REV order: define preço e relê)
    r = await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-09-28", "price": "50.00"}, headers=h)
    assert r.status_code == 201, r.text
    r = await ac.get(f"/api/assets/{aid}/prices", headers=h)
    assert len(r.json()) == 1 and r.json()[0]["source"] == "MANUAL"

    # position usa o preço manual mais recente <= hoje (sem brapi: MANUAL direto)
    r = await ac.get(f"/api/assets/{aid}/position", headers=h)
    p = r.json()
    assert p["current_price"] == "50.00000000" and p["price_source"] == "MANUAL"
    assert p["current_value"] == "500.00" and p["pnl"] == "100.00" and p["profitability"] == "0.2500"


async def test_rf_accrual_com_cdi_mockado(iac, monkeypatch):
    from decimal import Decimal

    from app.modules.market import bcb

    async def fake_cdi(start, end, timeout_s=15, client=None):
        out, cur = {}, start
        while cur <= end:
            if cur.weekday() < 5:
                out[cur] = Decimal("0.05")
            cur += timedelta(days=1)
        return out

    monkeypatch.setattr(bcb, "cdi_range", fake_cdi)

    ac, h = iac, await _user(iac, "rf")

    # contrato inválido: rate sem rate_type → 422
    r = await ac.post(
        "/api/assets", json={"ticker": "CDB7", "asset_class": "RENDA_FIXA", "subtype": "CDB", "rate": "110"}, headers=h
    )
    assert r.status_code == 422

    r = await ac.post(
        "/api/assets",
        json={"ticker": "CDB7", "asset_class": "RENDA_FIXA", "subtype": "CDB", "rate_type": "CDI_PCT", "rate": "100"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    assert r.json()["rate_type"] == "CDI_PCT"

    r = await ac.post(
        f"/api/assets/{aid}/ops",
        json={"kind": "APORTE", "date": "2026-09-25", "quantity": "100", "price": "10"},
        headers=h,
    )
    assert r.status_code == 201

    r = await ac.get(f"/api/assets/{aid}/position", headers=h)
    p = r.json()
    assert p["price_source"] == "ACCRUAL", p
    # 25, 26(sex?) ...: valor > 1000 pelo CDI 0.05%/du
    assert Decimal(p["current_value"]) > Decimal("1000")

    # IPCA_MAIS cai para manual (sem preço → nulos)
    r = await ac.post(
        "/api/assets",
        json={
            "ticker": "LCA7",
            "asset_class": "RENDA_FIXA",
            "subtype": "LCI_LCA",
            "rate_type": "IPCA_MAIS",
            "rate": "6",
        },
        headers=h,
    )
    assert r.status_code == 201
    aid2 = r.json()["id"]
    await ac.post(
        f"/api/assets/{aid2}/ops",
        json={"kind": "APORTE", "date": "2026-09-25", "quantity": "10", "price": "100"},
        headers=h,
    )
    r = await ac.get(f"/api/assets/{aid2}/position", headers=h)
    assert r.json()["current_price"] is None


async def test_returns_com_benchmarks_mockados(iac, monkeypatch):
    from decimal import Decimal

    from app.modules.market import benchmarks as bench

    async def fake_cdi(s, e):
        return Decimal("0.05")

    async def fake_ipca(s, e):
        return Decimal("0.02")

    monkeypatch.setattr(bench, "cdi_return", fake_cdi)
    monkeypatch.setattr(bench, "ipca_return", fake_ipca)

    ac, h = iac, await _user(iac, "rt")
    r = await ac.post("/api/accounts", json={"name": "Corretora", "account_type": "CHECKING"}, headers=h)
    rt_acc = r.json()["id"]
    r = await ac.post("/api/assets", json={"ticker": "FUN7", "asset_class": "OUTROS", "subtype": "OUTRO"}, headers=h)
    aid = r.json()["id"]
    for body in [
        {"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100"},
        {"kind": "RENDIMENTO", "date": "2026-06-01", "amount": "50", "account_id": rt_acc},
    ]:
        assert (await ac.post(f"/api/assets/{aid}/ops", json=body, headers=h)).status_code == 201
    assert (
        await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-09-28", "price": "120"}, headers=h)
    ).status_code == 201

    r = await ac.get(f"/api/assets/{aid}/returns", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["start"] == "2026-01-10"
    # simples: (1200 + 50 - 1000)/1000 = 0.25
    assert Decimal(str(d["simple"])) == Decimal("0.25")
    assert d["xirr"] is not None and Decimal(str(d["xirr"])) > 0
    assert d["twr"] is not None and d["twr_annualized"] is not None
    assert d["benchmarks"] == {"cdi": "0.05", "ipca": "0.02"}

    # sem operações: tudo nulo, sem quebrar
    r = await ac.post("/api/assets", json={"ticker": "VAZ7", "asset_class": "OUTROS", "subtype": "OUTRO"}, headers=h)
    r = await ac.get(f"/api/assets/{r.json()['id']}/returns", headers=h)
    assert r.status_code == 200 and r.json()["simple"] is None and r.json()["xirr"] is None
