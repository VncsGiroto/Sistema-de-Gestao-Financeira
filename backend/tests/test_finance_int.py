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


async def test_account_saldo_atual(app_client):
    """1.1: atual = inicial + receitas − despesas, com totais e última data."""
    ac = app_client
    _, ha = await _user(ac, "saldo")
    r = await ac.post(
        "/api/accounts",
        json={"name": "Corrente", "account_type": "CHECKING", "initial_balance": "100.00"},
        headers=ha,
    )
    assert r.status_code == 201, r.text
    acc = r.json()
    assert acc["current_balance"] == "100.00" and acc["total_income"] == "0" and acc["total_expense"] == "0"
    assert acc["last_transaction_date"] is None

    async def tx(date, desc, amt, t):
        r = await ac.post(
            "/api/transactions",
            json={"account_id": acc["id"], "date": date, "description": desc, "amount": amt, "type": t},
            headers=ha,
        )
        assert r.status_code == 201, r.text

    await tx("2026-09-05", "SAL", "500.00", "INCOME")
    await tx("2026-09-10", "MERCADO", "200.00", "EXPENSE")
    await tx("2026-09-12", "FREELA", "50.00", "INCOME")

    r = await ac.get(f"/api/accounts/{acc['id']}", headers=ha)
    assert r.status_code == 200, r.text
    got = r.json()
    assert got["current_balance"] == "450.00"  # 100 + 550 − 200
    assert got["total_income"] == "550.00" and got["total_expense"] == "200.00"
    assert got["last_transaction_date"] == "2026-09-12"

    r = await ac.get("/api/accounts", headers=ha)
    assert r.status_code == 200 and r.json()[0]["current_balance"] == "450.00"


async def test_account_types_enum(app_client):
    """0012: CREDIT_CARD removido (→422), INVESTMENT aceito (→201)."""
    ac = app_client
    _, ha = await _user(ac, "erin")

    r = await ac.post("/api/accounts", json={"name": "Cartão", "account_type": "CREDIT_CARD"}, headers=ha)
    assert r.status_code == 422, r.text

    r = await ac.post("/api/accounts", json={"name": "Corretora", "account_type": "INVESTMENT"}, headers=ha)
    assert r.status_code == 201, r.text
    acc_id = r.json()["id"]

    r = await ac.patch(f"/api/accounts/{acc_id}", json={"account_type": "CREDIT_CARD"}, headers=ha)
    assert r.status_code == 422, r.text


async def test_account_type_travado_com_vinculo(app_client):
    """Conta com ativo vinculado ou ledger não troca de tipo (reclassificaria a carteira)."""
    ac = app_client
    _, ha = await _user(ac, "tieacc")
    r = await ac.post("/api/accounts", json={"name": "Corretora", "account_type": "INVESTMENT"}, headers=ha)
    br = r.json()["id"]
    r = await ac.post(
        "/api/assets", json={"ticker": "TIEA", "asset_class": "FUNDOS", "subtype": "FII", "account_id": br}, headers=ha
    )
    assert r.status_code == 201, r.text
    r = await ac.patch(f"/api/accounts/{br}", json={"account_type": "CHECKING"}, headers=ha)
    assert r.status_code == 422
    # sem vínculo, troca livre
    r = await ac.post("/api/accounts", json={"name": "Livre", "account_type": "CHECKING"}, headers=ha)
    livre = r.json()["id"]
    r = await ac.patch(f"/api/accounts/{livre}", json={"account_type": "SAVINGS"}, headers=ha)
    assert r.status_code == 200 and r.json()["account_type"] == "SAVINGS"


async def test_saldo_atual_ignora_lancamento_futuro(app_client):
    """Saldo 'atual' corta em hoje: receita futura não entra no current_balance."""
    from datetime import date, timedelta

    ac = app_client
    _, ha = await _user(ac, "fut")
    r = await ac.post(
        "/api/accounts", json={"name": "Corrente", "account_type": "CHECKING", "initial_balance": "100.00"}, headers=ha
    )
    acc = r.json()["id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    r = await ac.post(
        "/api/transactions",
        json={"account_id": acc, "date": tomorrow, "description": "FUTURO", "amount": "500.00", "type": "INCOME"},
        headers=ha,
    )
    assert r.status_code == 201, r.text
    got = (await ac.get(f"/api/accounts/{acc}", headers=ha)).json()
    assert got["current_balance"] == "100.00"


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
