"""3.1 int: upload → polling VALIDATED → itens NEW; FAILED legível; isolamento."""

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
async def oac(monkeypatch):
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


async def _account(ac: AsyncClient, h: dict) -> int:
    r = await ac.post("/api/accounts", json={"name": "Conta", "account_type": "CHECKING"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _wait_validated(ac: AsyncClient, imp_id: int, h: dict, timeout_s: int = 20):
    for _ in range(int(timeout_s * 5)):
        r = await ac.get(f"/api/imports/{imp_id}", headers=h)
        assert r.status_code == 200
        if r.json()["status"] in ("VALIDATED", "FAILED"):
            return r.json()
        await asyncio.sleep(0.2)
    raise TimeoutError("import não saiu de RECEIVED/PROCESSING")


async def test_upload_parse_e_itens(oac):
    ac, h = oac, await _user(oac, "ofx")
    acc = await _account(ac, h)
    raw = (FIX / "minimo.ofx").read_bytes()

    r = await ac.post(
        "/api/imports/ofx", data={"account_id": str(acc)}, files={"file": ("extrato.ofx", raw)}, headers=h
    )
    assert r.status_code == 202, r.text
    imp_id = r.json()["import_id"]

    final = await _wait_validated(ac, imp_id, h)
    assert final["status"] == "VALIDATED", final
    assert final["total_rows"] == 3

    r = await ac.get(f"/api/imports/{imp_id}/items", headers=h)
    assert r.status_code == 200
    by_verdict = {}
    for it in r.json():
        by_verdict.setdefault(it["verdict"], []).append(it)
    assert len(by_verdict.get("NEW", [])) == 2
    assert len(by_verdict.get("INVALID", [])) == 1
    assert by_verdict["NEW"][0]["payload"]["external_id"] == "20260910001"
    # 4.x: campo decision exposto (None antes de qualquer review)
    assert all(it["decision"] is None for it in r.json())

    # lista resumida
    r = await ac.get("/api/imports", headers=h)
    assert r.status_code == 200 and len(r.json()) == 1

    # re-upload: novo import_id (idempotência de conteúdo vem no 3.2)
    r = await ac.post(
        "/api/imports/ofx", data={"account_id": str(acc)}, files={"file": ("extrato.ofx", raw)}, headers=h
    )
    assert r.status_code == 202 and r.json()["import_id"] != imp_id


async def test_commit_e_filtro_import_id(oac):
    """4.x: commit liga txs ao import; ?import_id= retorna exatamente o lote."""
    ac, h = oac, await _user(oac, "impid")
    acc = await _account(ac, h)
    raw = (FIX / "minimo.ofx").read_bytes()
    r = await ac.post(
        "/api/imports/ofx", data={"account_id": str(acc)}, files={"file": ("extrato.ofx", raw)}, headers=h
    )
    imp_id = r.json()["import_id"]
    assert (await _wait_validated(ac, imp_id, h))["status"] == "VALIDATED"

    r = await ac.post(f"/api/imports/{imp_id}/commit", headers=h)
    assert r.status_code == 200 and r.json()["imported_rows"] == 2, r.text

    r = await ac.get("/api/transactions", params={"import_id": imp_id, "per_page": 50}, headers=h)
    assert r.status_code == 200 and len(r.json()["data"]) == 2
    assert all(t["source"] == "OFX" for t in r.json()["data"])


async def test_arquivo_invalido_e_regras(oac):
    ac, h = oac, await _user(oac, "bad")
    acc = await _account(ac, h)

    # extensão errada → 422
    r = await ac.post("/api/imports/ofx", data={"account_id": str(acc)}, files={"file": ("x.txt", b"abc")}, headers=h)
    assert r.status_code == 422

    # conta de outro usuário → 404
    h2 = await _user(oac, "outro")
    r = await ac.post(
        "/api/imports/ofx",
        data={"account_id": str(acc)},
        files={"file": ("e.ofx", (FIX / "minimo.ofx").read_bytes())},
        headers=h2,
    )
    assert r.status_code == 404

    # conteúdo malformado → FAILED legível
    r = await ac.post(
        "/api/imports/ofx",
        data={"account_id": str(acc)},
        files={"file": ("q.ofx", (FIX / "invalido.ofx").read_bytes())},
        headers=h,
    )
    assert r.status_code == 202
    final = await _wait_validated(ac, r.json()["import_id"], h)
    assert final["status"] == "FAILED" and final["error"]

    # import de outro usuário → 404
    r = await ac.post(
        "/api/imports/ofx",
        data={"account_id": str(acc)},
        files={"file": ("e.ofx", (FIX / "minimo.ofx").read_bytes())},
        headers=h,
    )
    imp_id = r.json()["import_id"]
    await _wait_validated(ac, imp_id, h)
    assert (await ac.get(f"/api/imports/{imp_id}", headers=h2)).status_code == 404
    assert (await ac.get(f"/api/imports/{imp_id}/items", headers=h2)).status_code == 404


async def test_upload_c6_headers_exoticos(oac):
    """Regressão: OFX estilo C6 (`UTF - 8`, timezone, sem MEMO) valida e classifica."""
    ac, h = oac, await _user(oac, "c6")
    acc = await _account(ac, h)
    raw = (FIX / "c6.ofx").read_bytes()
    r = await ac.post("/api/imports/ofx", data={"account_id": str(acc)}, files={"file": ("c6.ofx", raw)}, headers=h)
    assert r.status_code == 202, r.text
    final = await _wait_validated(ac, r.json()["import_id"], h)
    assert final["status"] == "VALIDATED", final
    assert final["total_rows"] == 4
    imp_id = (await ac.get("/api/imports", headers=h)).json()[0]["id"]
    r = await ac.get(f"/api/imports/{imp_id}/items", headers=h)
    exts = {it["payload"].get("external_id") for it in r.json() if it["verdict"] == "NEW"}
    assert "TESTC6FIT0001" in exts and "TESTC6FIT0003" in exts


def _grande_ofx(n: int = 5000) -> bytes:
    head = (FIX / "minimo.ofx").read_text().split("<BANKTRANLIST>")[
        0
    ] + "<BANKTRANLIST>\n<DTSTART>20260101\n<DTEND>20261231\n"
    rows = "".join(
        f"<STMTTRN>\n<TRNTYPE>DEBIT\n<DTPOSTED>20260615\n<TRNAMT>-{i % 900 + 1}.00\n"
        f"<FITID>G{i:06d}\n<NAME>LOJA {i}\n<MEMO>COMPRA {i}\n</STMTTRN>\n"
        for i in range(n)
    )
    tail = (
        "</BANKTRANLIST>\n<LEDGERBAL>\n<BALAMT>0\n<DTASOF>20261231\n</LEDGERBAL>\n"
        "</STMTRS>\n</STMTTRNRS>\n</BANKMSGSRSV1>\n</OFX>\n"
    )
    return (head + rows + tail).encode()


async def test_upload_grande_rapido(oac):
    import time

    ac, h = oac, await _user(oac, "big")
    acc = await _account(ac, h)
    raw = _grande_ofx(5000)
    t0 = time.monotonic()
    r = await ac.post("/api/imports/ofx", data={"account_id": str(acc)}, files={"file": ("g.ofx", raw)}, headers=h)
    assert r.status_code == 202, r.text
    final = await _wait_validated(ac, r.json()["import_id"], h, timeout_s=60)
    dt = time.monotonic() - t0
    assert final["status"] == "VALIDATED" and final["total_rows"] == 5000
    assert dt < 60, f"lento: {dt:.1f}s"
