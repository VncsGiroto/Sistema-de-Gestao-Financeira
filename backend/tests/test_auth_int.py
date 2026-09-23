"""Integração: exige Postgres+Redis reais (docker compose up).

Roda com: TEST_DATABASE_URL=postgresql+asyncpg://finance:finance@localhost:5432/financeway \
          TEST_REDIS_URL=redis://localhost:6379/0 pytest -m integration
"""

import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

pytestmark = pytest.mark.integration

DB_URL = os.getenv("TEST_DATABASE_URL", "")
REDIS_URL = os.getenv("TEST_REDIS_URL", "")


@pytest.fixture()
async def client(monkeypatch):
    if not DB_URL:
        pytest.skip("TEST_DATABASE_URL ausente")
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv("REDIS_URL", REDIS_URL or "redis://localhost:6379/0")
    # importa app (e todos os models) ANTES do drop_all para o metadata estar completo
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


async def test_register_login_me_refresh_logout(client):
    email = f"u_{uuid.uuid4().hex[:8]}@exemplo.com"
    r = await client.post("/api/auth/register", json={"name": "Teste", "email": email, "password": "segredo-123"})
    assert r.status_code == 201, r.text

    # duplicado → 409
    r2 = await client.post("/api/auth/register", json={"name": "Teste", "email": email, "password": "segredo-123"})
    assert r2.status_code == 409

    r = await client.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    assert r.status_code == 200, r.text
    access, refresh = r.json()["access_token"], r.json()["refresh_token"]

    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200

    r = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200, r.text
    new_access, new_refresh = r.json()["access_token"], r.json()["refresh_token"]

    # reuso do refresh antigo → 401 (reuse-detection)
    r = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401

    # logout com o novo refresh
    r = await client.post(
        "/api/auth/logout",
        json={"refresh_token": new_refresh},
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert r.status_code in (204, 200)

    # login errado → 401
    r = await client.post("/api/auth/login", json={"email": email, "password": "errada-x"})
    assert r.status_code == 401


async def test_cookie_flow(client):
    """Refresh via cookie HttpOnly (sem corpo): login → refresh → logout → refresh negado."""
    email = f"c_{uuid.uuid4().hex[:8]}@exemplo.com"
    await client.post("/api/auth/register", json={"name": "Cook", "email": email, "password": "segredo-123"})
    r = await client.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    assert r.status_code == 200
    assert "fw_refresh" in r.cookies
    assert "httponly" in r.headers.get("set-cookie", "").lower()

    r = await client.post("/api/auth/refresh", json={})
    assert r.status_code == 200, r.text
    new_access = r.json()["access_token"]

    r = await client.post("/api/auth/logout", json={}, headers={"Authorization": f"Bearer {new_access}"})
    assert r.status_code == 204

    # cookie limpo + refresh revogado → 401
    assert "fw_refresh" not in client.cookies
    r = await client.post("/api/auth/refresh", json={"refresh_token": "token-invalido-123"})
    assert r.status_code == 401
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert r.status_code == 401  # access do logout caiu na deny-list (jti)


async def test_recover_reset_change(client):
    import app.modules.auth.service as svc

    email = f"r_{uuid.uuid4().hex[:8]}@exemplo.com"
    r = await client.post("/api/auth/register", json={"name": "Rec", "email": email, "password": "segredo-123"})
    assert r.status_code == 201, r.text

    # recover existente e inexistente → mesmo 202 (anti-enumeração)
    r = await client.post("/api/auth/recover", json={"email": email})
    assert r.status_code == 202, r.text
    r = await client.post("/api/auth/recover", json={"email": "nao-existe@exemplo.com"})
    assert r.status_code == 202, r.text

    # obtém token via serviço (em prod viria do e-mail/log)
    from app.core.db import SessionLocal

    async with SessionLocal() as session:
        token = await svc.request_recovery(session, email)
    assert token, "token de recovery esperado"

    # reset com token inválido → 401
    r = await client.post("/api/auth/reset", json={"token": "token-invalido-123", "new_password": "nova-senha-1"})
    assert r.status_code == 401

    # login válido antes do reset (para ter refresh antigo)
    r = await client.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    assert r.status_code == 200
    old_refresh = r.json()["refresh_token"]

    r = await client.post("/api/auth/reset", json={"token": token, "new_password": "nova-senha-1"})
    assert r.status_code == 204, r.text

    # reuso do mesmo token → 401
    r = await client.post("/api/auth/reset", json={"token": token, "new_password": "outra-senha-2"})
    assert r.status_code == 401

    # senha antiga não entra; nova entra; refresh antigo revogado
    r = await client.post("/api/auth/login", json={"email": email, "password": "segredo-123"})
    assert r.status_code == 401
    r = await client.post("/api/auth/login", json={"email": email, "password": "nova-senha-1"})
    assert r.status_code == 200, r.text
    access, refresh = r.json()["access_token"], r.json()["refresh_token"]
    r = await client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 401

    # change com senha atual errada → 401
    r = await client.patch(
        "/api/auth/change",
        json={"current_password": "errada", "new_password": "nova-senha-2"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 401

    # change correto → 204 e força novo login (access antigo cai na deny-list)
    r = await client.patch(
        "/api/auth/change",
        json={"current_password": "nova-senha-1", "new_password": "nova-senha-2"},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert r.status_code == 204, r.text
    r = await client.post("/api/auth/login", json={"email": email, "password": "nova-senha-2"})
    assert r.status_code == 200
    _ = refresh
