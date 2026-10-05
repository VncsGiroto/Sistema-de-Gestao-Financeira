"""2.2: transactions CRUD + filtros + paginação + CSV + regras de delete."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture()
async def tac(monkeypatch):
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


async def _setup(ac: AsyncClient, h: dict):
    r = await ac.post("/api/accounts", json={"name": "C1", "account_type": "CHECKING"}, headers=h)
    assert r.status_code == 201, r.text
    acc = r.json()["id"]
    r = await ac.post("/api/accounts", json={"name": "C2", "account_type": "CASH"}, headers=h)
    acc2 = r.json()["id"]
    r = await ac.post("/api/categories", json={"name": "Mercado", "type": "EXPENSE"}, headers=h)
    cat = r.json()["id"]
    r = await ac.post("/api/categories", json={"name": "Salário", "type": "INCOME"}, headers=h)
    cat_inc = r.json()["id"]
    return acc, acc2, cat, cat_inc


async def test_tx_crud_e_validacoes(tac):
    ac, h = tac, await _user(tac, "tx")
    acc, _, cat, _ = await _setup(ac, h)

    r = await ac.post(
        "/api/transactions",
        json={
            "account_id": acc,
            "category_id": cat,
            "date": "2026-09-10",
            "description": "SUPERMERCADO",
            "amount": "250.50",
            "type": "EXPENSE",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    tx = r.json()
    assert tx["source"] == "MANUAL"

    # amount zero ou negativo → 422
    r = await ac.post(
        "/api/transactions",
        json={"account_id": acc, "date": "2026-09-10", "description": "Z", "amount": "0", "type": "EXPENSE"},
        headers=h,
    )
    assert r.status_code == 422
    r = await ac.post(
        "/api/transactions",
        json={"account_id": acc, "date": "2026-09-10", "description": "N", "amount": "-5", "type": "EXPENSE"},
        headers=h,
    )
    assert r.status_code == 422
    r = await ac.patch(f"/api/transactions/{tx['id']}", json={"amount": "-5"}, headers=h)
    assert r.status_code == 422

    # conta inexistente / de outro usuário → 404
    r = await ac.post(
        "/api/transactions",
        json={"account_id": 999999, "date": "2026-09-10", "description": "X", "amount": "10", "type": "EXPENSE"},
        headers=h,
    )
    assert r.status_code == 404

    # patch + get + delete
    r = await ac.patch(f"/api/transactions/{tx['id']}", json={"description": "MERCADO X"}, headers=h)
    assert r.status_code == 200 and r.json()["description"] == "MERCADO X"
    r = await ac.get(f"/api/transactions/{tx['id']}", headers=h)
    assert r.status_code == 200
    r = await ac.delete(f"/api/transactions/{tx['id']}", headers=h)
    assert r.status_code == 204
    r = await ac.get(f"/api/transactions/{tx['id']}", headers=h)
    assert r.status_code == 404


async def test_tx_filtros_paginacao_csv(tac):
    ac, h = tac, await _user(tac, "flt")
    acc, acc2, cat, cat_inc = await _setup(ac, h)
    seed = [
        (acc, cat, "2026-09-05", "MERCADO A", "100", "EXPENSE"),
        (acc, cat, "2026-09-15", "MERCADO B", "200", "EXPENSE"),
        (acc2, cat_inc, "2026-09-15", "SALARIO", "8000", "INCOME"),
        (acc, cat, "2026-08-20", "ANTIGO", "50", "EXPENSE"),
    ]
    for a, c, d, desc, amt, t in seed:
        r = await ac.post(
            "/api/transactions",
            json={"account_id": a, "category_id": c, "date": d, "description": desc, "amount": amt, "type": t},
            headers=h,
        )
        assert r.status_code == 201, r.text

    async def total(**qs):
        r = await ac.get("/api/transactions", params={**qs, "per_page": 50}, headers=h)
        assert r.status_code == 200
        return r.json()["meta"]["total"], r.json()["data"]

    assert (await total())[0] == 4
    assert (await total(**{"from": "2026-09-01", "to": "2026-09-30"}))[0] == 3
    assert (await total(category_id=cat))[0] == 3
    assert (await total(type="INCOME"))[0] == 1
    assert (await total(account_id=acc2))[0] == 1
    assert (await total(q="mercado"))[0] == 2
    assert (await total(min="10", max="150"))[0] == 2

    # paginação
    r = await ac.get("/api/transactions", params={"page": 1, "per_page": 2}, headers=h)
    assert r.json()["meta"] == {"page": 1, "per_page": 2, "total": 4}
    assert len(r.json()["data"]) == 2

    # CSV com ; e filtro aplicado
    r = await ac.get("/api/transactions/export/csv", params={"type": "EXPENSE"}, headers=h)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.lstrip("\ufeff").strip().splitlines()  # BOM proposital p/ Excel BR
    assert lines[0] == "id;date;description;amount;type;account;category;source"
    assert len(lines) == 4  # header + 3 despesas
    assert "MERCADO A" in r.text


async def test_tx_bulk_categorize(tac):
    """4.x: aplica em massa com compatibilidade; incompatíveis/inexistentes são contados."""
    ac, h = tac, await _user(tac, "bulk")
    acc, _, cat_exp, cat_inc = await _setup(ac, h)

    async def mk(desc, amt, t, cat=None):
        body = {"account_id": acc, "date": "2026-09-10", "description": desc, "amount": amt, "type": t}
        if cat:
            body["category_id"] = cat
        r = await ac.post("/api/transactions", json=body, headers=h)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    e1 = await mk("A", "10", "EXPENSE")
    e2 = await mk("B", "20", "EXPENSE", cat_exp)
    i1 = await mk("C", "30", "INCOME")

    r = await ac.post(
        "/api/transactions/categorize", json={"ids": [e1, e2, i1, 999999], "category_id": cat_exp}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"updated": 2, "skipped_type": 1, "skipped_missing": 1}

    r = await ac.get(f"/api/transactions/{e1}", headers=h)
    assert r.json()["category_id"] == cat_exp

    # categoria de outro usuário → 404; sem ids → 422
    _, hb = acc, await _user(tac, "bulk2")
    r = await ac.post("/api/transactions/categorize", json={"ids": [e1], "category_id": cat_exp}, headers=hb)
    assert r.status_code == 404
    r = await ac.post("/api/transactions/categorize", json={"ids": [], "category_id": cat_exp}, headers=h)
    assert r.status_code == 422


async def test_tx_categoria_tipo_compativel(tac):
    """0.2: categoria de tipo divergente → 422 no create e no PATCH."""
    ac, h = tac, await _user(tac, "cat")
    acc, _, cat_exp, cat_inc = await _setup(ac, h)

    async def create(tx_type, cat):
        return await ac.post(
            "/api/transactions",
            json={
                "account_id": acc,
                "category_id": cat,
                "date": "2026-09-10",
                "description": "T",
                "amount": "10",
                "type": tx_type,
            },
            headers=h,
        )

    assert (await create("INCOME", cat_exp)).status_code == 422
    assert (await create("EXPENSE", cat_inc)).status_code == 422
    assert (await create("INCOME", cat_inc)).status_code == 201
    r = await create("EXPENSE", cat_exp)
    assert r.status_code == 201, r.text
    tx = r.json()["id"]

    # PATCH só o tipo → estado final incompatível → 422
    assert (await ac.patch(f"/api/transactions/{tx}", json={"type": "INCOME"}, headers=h)).status_code == 422
    # PATCH só a categoria → incompatível → 422
    assert (await ac.patch(f"/api/transactions/{tx}", json={"category_id": cat_inc}, headers=h)).status_code == 422
    # PATCH tipo+categoria consistentes → 200
    r = await ac.patch(f"/api/transactions/{tx}", json={"type": "INCOME", "category_id": cat_inc}, headers=h)
    assert r.status_code == 200 and r.json()["category_id"] == cat_inc
    # remover categoria sempre permitido
    r = await ac.patch(f"/api/transactions/{tx}", json={"category_id": None}, headers=h)
    assert r.status_code == 200 and r.json()["category_id"] is None


async def test_tx_isolamento_e_regras_delete(tac):
    ac = tac
    ha, hb = await _user(ac, "own"), await _user(ac, "out")
    acc, _, cat, _ = await _setup(ac, ha)

    r = await ac.post(
        "/api/transactions",
        json={
            "account_id": acc,
            "category_id": cat,
            "date": "2026-09-10",
            "description": "X",
            "amount": "10",
            "type": "EXPENSE",
        },
        headers=ha,
    )
    tx = r.json()["id"]

    # outro usuário: tudo 404 + lista vazia
    assert (await ac.get("/api/transactions", headers=hb)).json()["data"] == []
    assert (await ac.get(f"/api/transactions/{tx}", headers=hb)).status_code == 404
    assert (await ac.delete(f"/api/transactions/{tx}", headers=hb)).status_code == 404

    # conta com tx → 409; categoria com tx → 204 e tx.category_id vira NULL
    assert (await ac.delete(f"/api/accounts/{acc}", headers=ha)).status_code == 409
    assert (await ac.delete(f"/api/categories/{cat}", headers=ha)).status_code == 204
    r = await ac.get(f"/api/transactions/{tx}", headers=ha)
    assert r.status_code == 200 and r.json()["category_id"] is None

    # sem txs a conta exclui normal
    r = await ac.post("/api/accounts", json={"name": "Vazia", "account_type": "CASH"}, headers=ha)
    assert (await ac.delete(f"/api/accounts/{r.json()['id']}", headers=ha)).status_code == 204
