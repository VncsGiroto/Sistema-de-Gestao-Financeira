"""4.1 int: CRUD bills + upcoming + isolamento (backend, sem tela)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture()
async def bac(monkeypatch):
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


async def test_bills_crud_e_next_due(bac):
    ac, h = bac, await _user(bac, "bil")
    r = await ac.post(
        "/api/bills",
        json={"description": "Internet", "amount": "120.00", "kind": "FIXED", "periodicity": "MONTHLY", "due_day": 10},
        headers=h,
    )
    assert r.status_code == 201, r.text
    bill = r.json()
    assert bill["next_due"] is not None  # calculado pelo servidor

    # ONE_TIME exige next_due e rejeita periodicity
    r = await ac.post("/api/bills", json={"description": "X", "amount": "10", "kind": "ONE_TIME"}, headers=h)
    assert r.status_code == 422
    r = await ac.post(
        "/api/bills",
        json={"description": "Única", "amount": "10", "kind": "ONE_TIME", "next_due": "2026-10-05"},
        headers=h,
    )
    assert r.status_code == 201 and r.json()["next_due"] == "2026-10-05"

    # recorrente sem due_day → 422; due_day fora da faixa → 422 (pydantic)
    r = await ac.post(
        "/api/bills",
        json={"description": "Y", "amount": "10", "kind": "RECURRING", "periodicity": "MONTHLY"},
        headers=h,
    )
    assert r.status_code == 422
    r = await ac.post(
        "/api/bills",
        json={"description": "Y", "amount": "10", "kind": "RECURRING", "periodicity": "MONTHLY", "due_day": 40},
        headers=h,
    )
    assert r.status_code == 422

    # get/patch/delete
    assert (await ac.get(f"/api/bills/{bill['id']}", headers=h)).status_code == 200
    r = await ac.patch(f"/api/bills/{bill['id']}", json={"description": "Internet Fibra"}, headers=h)
    assert r.status_code == 200 and r.json()["description"] == "Internet Fibra"
    assert (await ac.delete(f"/api/bills/{bill['id']}", headers=h)).status_code == 204
    assert (await ac.get(f"/api/bills/{bill['id']}", headers=h)).status_code == 404


async def test_bills_upcoming_e_isolamento(bac):
    ac = bac
    h1, h2 = await _user(bac, "o1"), await _user(bac, "o2")
    for desc, kind, extra in [
        ("Perto", "FIXED", {"periodicity": "MONTHLY", "due_day": 1}),
        ("Longe", "ONE_TIME", {"next_due": "2099-01-01"}),
    ]:
        r = await ac.post("/api/bills", json={"description": desc, "amount": "10", "kind": kind, **extra}, headers=h1)
        assert r.status_code == 201, r.text

    r = await ac.get("/api/bills/upcoming?days=60", headers=h1)
    assert r.status_code == 200
    assert {b["description"] for b in r.json()} == {"Perto"}

    # outro usuário: lista vazia + get → 404
    assert (await ac.get("/api/bills", headers=h2)).json() == []
    r = await ac.get("/api/bills", headers=h1)
    bid = r.json()[0]["id"]
    assert (await ac.get(f"/api/bills/{bid}", headers=h2)).status_code == 404
    assert (await ac.get("/api/bills", headers=h1)).status_code == 200
