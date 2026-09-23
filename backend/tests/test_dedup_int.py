"""3.2 int: EXACT + FUZZY → review → commit idempotente + isolamento."""

import asyncio
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration
FIX = Path(__file__).parent / "fixtures"


@pytest.fixture()
async def dac(monkeypatch):
    if not DB_URL:
        pytest.skip("TEST_DATABASE_URL ausente")
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("REDIS_URL", REDIS_URL or "redis://localhost:6379/0")
    from app.main import app

    import app.core.db as dbmod
    from app.core.db import Base

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


async def _upload(ac, h, acc: int, fname: str) -> int:
    r = await ac.post("/api/imports/ofx", data={"account_id": str(acc)},
                      files={"file": (fname, (FIX / fname).read_bytes())}, headers=h)
    assert r.status_code == 202, r.text
    return r.json()["import_id"]


async def _wait(ac, imp_id: int, h: dict, want: str = "VALIDATED"):
    for _ in range(100):
        r = await ac.get(f"/api/imports/{imp_id}", headers=h)
        assert r.status_code == 200
        if r.json()["status"] in ("VALIDATED", "FAILED", "IMPORTED"):
            assert r.json()["status"] == want, r.json()
            return r.json()
        await asyncio.sleep(0.2)
    raise TimeoutError("sem VALIDATED")


async def _manual(ac, h, acc: int, d: str, desc: str, amt: str, t: str):
    r = await ac.post("/api/transactions",
                      json={"account_id": acc, "date": d, "description": desc, "amount": amt, "type": t},
                      headers=h)
    assert r.status_code == 201, r.text
    return r.json()


async def test_exact_fuzzy_review_commit(dac):
    ac, h = dac, await _user(dac, "dd")
    r = await ac.post("/api/accounts", json={"name": "Conta", "account_type": "CHECKING"}, headers=h)
    acc = r.json()["id"]

    # base manual para os fuzzies
    await _manual(ac, h, acc, "2026-09-10", "IFOOD JANTAR", "-45.90", "EXPENSE")
    await _manual(ac, h, acc, "2026-09-05", "SALARIO EMPRESA ABC", "7850.00", "INCOME")
    await _manual(ac, h, acc, "2026-09-12", "SPOTIFY", "-32.90", "EXPENSE")

    # minimo: tudo NEW → commit direto importa 2 (1 INVALID pula)
    m = await _upload(ac, h, acc, "minimo.ofx")
    await _wait(ac, m, h)
    r = await ac.post(f"/api/imports/{m}/commit", headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == {"imported_rows": 2, "duplicate_rows": 0, "skipped": 1}

    # duplicado: D1 EXACT (FITID do minimo), D2 NEW
    d = await _upload(ac, h, acc, "duplicado.ofx")
    await _wait(ac, d, h)
    r = await ac.get(f"/api/imports/{d}/items", headers=h)
    by_v = {it["verdict"]: it for it in r.json()}
    assert set(by_v) == {"EXACT_DUPLICATE", "NEW"}
    assert by_v["EXACT_DUPLICATE"]["matched_transaction_id"]

    # commit sem review → 409
    assert (await ac.post(f"/api/imports/{d}/commit", headers=h)).status_code == 409

    # review: descarta o EXACT → commit importa só o NEW
    ex_id = by_v["EXACT_DUPLICATE"]["id"]
    r = await ac.post(f"/api/imports/{d}/review", json={"decisions": [{"item_id": ex_id, "decision": "DISCARD_IMPORTED"}]}, headers=h)
    assert r.status_code == 200 and r.json() == {"decided": 1}
    r = await ac.post(f"/api/imports/{d}/commit", headers=h)
    assert r.status_code == 200 and r.json() == {"imported_rows": 1, "duplicate_rows": 1, "skipped": 0}
    # idempotente
    r = await ac.post(f"/api/imports/{d}/commit", headers=h)
    assert r.status_code == 200 and r.json()["imported_rows"] == 1

    # fuzzy: 2 FUZZY + 1 NEW (NETFLIX x SPOTIFY não casa)
    f = await _upload(ac, h, acc, "fuzzy.ofx")
    await _wait(ac, f, h)
    r = await ac.get(f"/api/imports/{f}/items?verdict=FUZZY_CANDIDATE", headers=h)
    assert r.status_code == 200 and len(r.json()) == 2, r.text
    assert all(it["payload"].get("score", 0) >= 0.70 for it in r.json())

    fz = {it["payload"]["external_id"]: it["id"] for it in r.json()}
    r = await ac.post(f"/api/imports/{f}/review", json={"decisions": [
        {"item_id": fz["FZ000001"], "decision": "KEEP_BOTH"},
        {"item_id": fz["FZ000002"], "decision": "DISCARD_IMPORTED"},
    ]}, headers=h)
    assert r.status_code == 200
    r = await ac.post(f"/api/imports/{f}/commit", headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == {"imported_rows": 2, "duplicate_rows": 1, "skipped": 0}

    # confere no extrato: FZ000001 entrou com FITID original (FUZZY KEEP mantém)
    r = await ac.get("/api/transactions", params={"q": "IFOOD JANTAR", "per_page": 50}, headers=h)
    assert r.json()["meta"]["total"] == 2  # manual + importada


async def test_review_commit_isolamento(dac):
    ac = dac
    h1, h2 = await _user(dac, "u1"), await _user(dac, "u2")
    r = await ac.post("/api/accounts", json={"name": "Conta", "account_type": "CHECKING"}, headers=h1)
    acc = r.json()["id"]
    imp = await _upload(ac, h1, acc, "minimo.ofx")
    await _wait(ac, imp, h1)

    assert (await ac.post(f"/api/imports/{imp}/review", json={"decisions": [{"item_id": 1, "decision": "DISCARD_IMPORTED"}]}, headers=h2)).status_code == 404
    assert (await ac.post(f"/api/imports/{imp}/commit", headers=h2)).status_code == 404

    # review de item NEW → 422; decision inválida → 422
    r = await ac.get(f"/api/imports/{imp}/items?verdict=NEW", headers=h1)
    nid = r.json()[0]["id"]
    assert (await ac.post(f"/api/imports/{imp}/review", json={"decisions": [{"item_id": nid, "decision": "DISCARD_IMPORTED"}]}, headers=h1)).status_code == 422
    assert (await ac.post(f"/api/imports/{imp}/review", json={"decisions": [{"item_id": nid, "decision": "X"}]}, headers=h1)).status_code == 422
