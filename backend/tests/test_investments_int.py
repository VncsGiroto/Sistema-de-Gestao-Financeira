"""7.1/7.2b int: assets + ops + position + preços + isolamento."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.test_auth_int import DB_URL, REDIS_URL

pytestmark = pytest.mark.integration


async def _mk_account(ac, h, name, type_="INVESTMENT", initial="0"):
    r = await ac.post(
        "/api/accounts", json={"name": name, "account_type": type_, "initial_balance": initial}, headers=h
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _mk_asset(ac, h, ticker, account_id=None, **kw):
    body = {"ticker": ticker, "asset_class": "RENDA_VARIAVEL", "subtype": "ACAO", "account_id": account_id}
    body.update(kw)
    r = await ac.post("/api/assets", json=body, headers=h)
    return r


async def _op(ac, h, aid, body, expect=201):
    r = await ac.post(f"/api/assets/{aid}/ops", json=body, headers=h)
    assert r.status_code == expect, (body, r.text)
    return r.json()


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


async def test_vinculo_conta_e_caixa(iac):
    """Épico ii: ativo↔conta INVESTMENT; aporte/resgate movem caixa atomicamente; sem dupla contagem."""
    ac, h = iac, await _user(iac, "vinculo")
    cc = await _mk_account(ac, h, "Corrente", "CHECKING", "5000.00")
    br1 = await _mk_account(ac, h, "Corretora A")
    br2 = await _mk_account(ac, h, "Corretora B")

    # vínculo exige conta INVESTMENT do usuário
    assert (await _mk_asset(ac, h, "PETR4", cc)).status_code == 422
    assert (await _mk_asset(ac, h, "PETR4", 999999)).status_code == 404
    assert (await _mk_asset(ac, h, "PETR4", br1)).status_code == 201
    # mesmo ticker em outra corretora OK; na mesma → 409
    assert (await _mk_asset(ac, h, "PETR4", br2)).status_code == 201
    assert (await _mk_asset(ac, h, "PETR4", br1)).status_code == 409
    aid = (await _mk_asset(ac, h, "VALE3", br1)).json()["id"]

    async def balance(acc_id):
        return (await ac.get(f"/api/accounts/{acc_id}", headers=h)).json()["current_balance"]

    async def ops(body, expect=201):
        return await _op(ac, h, aid, body, expect)

    # transfere para a corretora e aporta: caixa cai, posição sobe, patrimônio neutro
    r = await ac.post(
        "/api/transfers", json={"from_account_id": cc, "to_account_id": br1, "amount": "1000.00"}, headers=h
    )
    assert r.status_code == 201, r.text
    await ops({"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"})
    assert await balance(br1) == "0.00"
    p = (await ac.get(f"/api/assets/{aid}/position", headers=h)).json()
    assert Decimal(p["quantity"]) == 10 and p["invested"] == "1000.00"

    pf = (await ac.get("/api/portfolio", headers=h)).json()
    assert pf["cash"] == "0.00" and pf["aportes"] == "1000.00"
    assert pf["total"] is None and pf["status"] == "INCOMPLETE"  # sem preço: parcial, nunca zero
    assert pf["unpriced"] == ["VALE3"]
    assert pf["history_since"] is not None  # snapshot sob evento

    # preço manual → posição avaliada; patrimônio = caixa + posições, sem dupla contagem
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-02-01", "price": "110.00"}, headers=h)
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    assert pf["positions_value"] == "1100.00" and pf["total"] == "1100.00" and pf["resultado"] == "100.00"
    assert pf["status"] == "COMPLETE"
    assert pf["unpriced"] == [] and len(pf["snapshots"]) >= 1  # upsert por dia: eventos do mesmo dia colapsam

    # resgate devolve o caixa
    await ops({"kind": "RESGATE", "date": "2026-03-01", "quantity": "4", "price": "120.00"})
    assert await balance(br1) == "480.00"

    # ativo sem conta: aporte bloqueado, posição segue calculável
    free = (await _mk_asset(ac, h, "LIVRE1")).json()["id"]
    r = await ac.post(
        f"/api/assets/{free}/ops",
        json={"kind": "APORTE", "date": "2026-01-10", "quantity": "1", "price": "10.00"},
        headers=h,
    )
    assert r.status_code == 422


async def test_reinvestimento_sem_receita(iac):
    """REINVESTIMENTO soma posição/custo, sem INCOME, sem caixa; XIRR o ignora."""
    ac, h = iac, await _user(iac, "reinv")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "FII11", br, asset_class="FUNDOS", subtype="FII")).json()["id"]

    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"})
    assert (await ac.get(f"/api/accounts/{br}", headers=h)).json()["current_balance"] == "0.00"
    await _op(ac, h, aid, {"kind": "REINVESTIMENTO", "date": "2026-02-10", "quantity": "1", "price": "100.00"})
    # sem receita no extrato e sem mexer no caixa
    r = await ac.get("/api/transactions", params={"type": "INCOME", "per_page": 50}, headers=h)
    assert r.json()["meta"]["total"] == 0
    assert (await ac.get(f"/api/accounts/{br}", headers=h)).json()["current_balance"] == "0.00"

    p = (await ac.get(f"/api/assets/{aid}/position", headers=h)).json()
    assert Decimal(p["quantity"]) == 11 and p["invested"] == "1100.00" and p["reinvestimentos"] == "100.00"
    assert p["aportes"] == "1000.00"


async def test_rf_valor_resgate_total_e_override(iac, monkeypatch):
    """RF contratada em R$: aporte/resgate convertidos, full liquida tudo, override explícito."""
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

    ac, h = iac, await _user(iac, "rfv")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "5000.00")
    asset = await _mk_asset(ac, h, "CDBV", br, asset_class="RENDA_FIXA", subtype="CDB", rate_type="CDI_PCT", rate="100")
    aid = asset.json()["id"]

    async def ops(body, expect=422):
        return await _op(ac, h, aid, body, expect)

    # modo valor: qty/price rejeitados; sem amount rejeitado; data futura rejeitada
    await ops({"kind": "APORTE", "date": "2026-09-25", "quantity": "10", "price": "10"})
    await ops({"kind": "APORTE", "date": "2026-09-25"})
    await ops({"kind": "APORTE", "date": "2099-01-01", "amount": "100"})
    await ops({"kind": "RESGATE", "date": "2026-09-26", "amount": "10", "full": True})

    await ops({"kind": "APORTE", "date": "2026-09-25", "amount": "1000.00"}, 201)
    assert (await ac.get(f"/api/accounts/{br}", headers=h)).json()["current_balance"] == "4000.00"

    # resgate parcial em reais move o caixa de volta
    await ops({"kind": "RESGATE", "date": "2026-09-26", "amount": "100.00"}, 201)

    # sem cotação com posição existente (BCB falho) → 422, sem fallback silencioso
    async def boom(start, end, timeout_s=15, client=None):
        raise bcb.BcbError("fora")

    monkeypatch.setattr(bcb, "cdi_range", boom)
    await ops({"kind": "APORTE", "date": "2026-09-28", "amount": "50.00"})
    monkeypatch.setattr(bcb, "cdi_range", fake_cdi)

    # resgate total liquida tudo: posição zerada, sem residual
    await ops({"kind": "RESGATE", "date": "2026-09-27", "full": True}, 201)
    p = (await ac.get(f"/api/assets/{aid}/position", headers=h)).json()
    assert Decimal(p["quantity"]) == 0 and p["invested"] == "0.00"

    # override explícito funciona (manual comum segue bloqueado com contrato)
    monkeypatch.setattr(bcb, "cdi_range", boom)
    px = {"date": "2026-09-28", "price": "1.05"}
    assert (await ac.post(f"/api/assets/{aid}/prices", json=px, headers=h)).status_code == 422
    r = await ac.post(f"/api/assets/{aid}/prices", json={**px, "override": True}, headers=h)
    assert r.status_code == 201 and r.json()["source"] == "MANUAL_OVERRIDE"


async def test_twr_preco_reinvestimento(iac):
    """TWR de preço: dia1 100@1, dia30 1.10 + reinvest 10@1.10, dia60 1.21 → +21%."""
    ac, h = iac, await _user(iac, "twr")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "TWR1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]

    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-10", "quantity": "100", "price": "1.00"})
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-01-30", "price": "1.10"}, headers=h)
    await _op(ac, h, aid, {"kind": "REINVESTIMENTO", "date": "2026-01-30", "quantity": "9.09090909", "price": "1.10"})
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-03-02", "price": "1.21"}, headers=h)

    r = await ac.get(f"/api/assets/{aid}/returns", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["twr"] is not None and abs(Decimal(d["twr"]) - Decimal("0.21")) < Decimal("0.005")
    assert d["xirr"] is not None and Decimal(d["xirr"]) > 0


async def test_aporte_concorrente_caixa(iac):
    """Dois aportes simultâneos contra o mesmo saldo: só um pode passar."""
    import asyncio as aio

    ac, h = iac, await _user(iac, "race")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "RACE1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]

    async def aporte():
        return await ac.post(
            f"/api/assets/{aid}/ops",
            json={"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"},
            headers=h,
        )

    r1, r2 = await aio.gather(aporte(), aporte())
    assert sorted([r1.status_code, r2.status_code]) == [201, 422]
    assert (await ac.get(f"/api/accounts/{br}", headers=h)).json()["current_balance"] == "0.00"


async def test_resgate_concorrente_posicao(iac):
    """Dois resgates que cabem sozinhos mas não juntos: só um pode passar (revalidação pós-lock)."""
    import asyncio as aio

    ac, h = iac, await _user(iac, "racer")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "RACE2", br, asset_class="FUNDOS", subtype="FII")).json()["id"]
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"})

    async def resgate():
        return await ac.post(
            f"/api/assets/{aid}/ops",
            json={"kind": "RESGATE", "date": "2026-02-10", "quantity": "8", "price": "100.00"},
            headers=h,
        )

    r1, r2 = await aio.gather(resgate(), resgate())
    assert sorted([r1.status_code, r2.status_code]) == [201, 422]
    p = (await ac.get(f"/api/assets/{aid}/position", headers=h)).json()
    assert Decimal(p["quantity"]) == 2


async def test_rendimento_tx_protegida(iac):
    """Transação espelhada por RENDIMENTO não aceita PATCH/DELETE direto; sai junto com a op."""
    ac, h = iac, await _user(iac, "rendlock")
    acc = await _mk_account(ac, h, "Corrente", "CHECKING")
    aid = (await _mk_asset(ac, h, "DIV1", None, asset_class="RENDA_VARIAVEL", subtype="ACAO")).json()["id"]
    r = await ac.post(
        f"/api/assets/{aid}/ops",
        json={"kind": "RENDIMENTO", "date": "2026-03-01", "amount": "25.00", "account_id": acc},
        headers=h,
    )
    assert r.status_code == 201, r.text
    op_id, tx_id = r.json()["id"], r.json()["transaction_id"]
    assert tx_id is not None
    assert (await ac.patch(f"/api/transactions/{tx_id}", json={"amount": "99.00"}, headers=h)).status_code == 422
    assert (await ac.patch(f"/api/transactions/{tx_id}", json={"description": "outra"}, headers=h)).status_code == 422
    assert (await ac.delete(f"/api/transactions/{tx_id}", headers=h)).status_code == 422
    assert (await ac.delete(f"/api/assets/{aid}/ops/{op_id}", headers=h)).status_code == 204
    assert (await ac.get(f"/api/transactions/{tx_id}", headers=h)).status_code == 404


async def test_carteira_rendimento_nao_e_aporte_externo(iac):
    """Rendimento em conta INVESTMENT é retorno interno: não entra no capital externo."""
    ac, h = iac, await _user(iac, "extflow")
    cc = await _mk_account(ac, h, "Corrente", "CHECKING", "5000.00")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT")
    aid = (await _mk_asset(ac, h, "EXT1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]
    r = await ac.post(
        "/api/transfers", json={"from_account_id": cc, "to_account_id": br, "amount": "1000.00"}, headers=h
    )
    assert r.status_code == 201, r.text
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"})
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-02-01", "price": "110.00"}, headers=h)
    await _op(ac, h, aid, {"kind": "RENDIMENTO", "date": "2026-02-15", "amount": "100.00", "account_id": br})
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    assert pf["net_invested"] == "1000.00"  # só a transferência externa
    assert pf["total"] == "1200.00" and pf["resultado"] == "200.00"


async def test_snapshot_retroativo_asof(iac):
    """Op retroativa gera snapshot histórico sem vazar ops/preços futuros."""
    ac, h = iac, await _user(iac, "asof")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1500.00")
    aid = (await _mk_asset(ac, h, "ASOF1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-03-01", "quantity": "10", "price": "100.00"})
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-03-01", "price": "100.00"}, headers=h)
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-01", "quantity": "5", "price": "100.00"})
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    by_date = {s["date"]: s for s in pf["snapshots"]}
    snap_jan = by_date["2026-01-01"]
    assert snap_jan["total"] is None and snap_jan["status"] == "INCOMPLETE"  # 5 cotas sem cotação: lacuna, não zero
    assert snap_jan["unpriced"] == ["ASOF1"] and snap_jan["cash"] == "1000.00"
    assert by_date["2026-03-01"]["total"] == "1500.00"


async def test_patch_account_id_com_historico(iac):
    """Ativo com operações não troca de conta vinculada (posição × caixa separariam)."""
    ac, h = iac, await _user(iac, "acctie")
    br1 = await _mk_account(ac, h, "Corretora A", "INVESTMENT", "1000.00")
    br2 = await _mk_account(ac, h, "Corretora B", "INVESTMENT")
    aid = (await _mk_asset(ac, h, "TIE1", br1, asset_class="FUNDOS", subtype="FII")).json()["id"]
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"})
    r = await ac.patch(f"/api/assets/{aid}", json={"account_id": br2}, headers=h)
    assert r.status_code == 422
    free = (await _mk_asset(ac, h, "TIE2", None, asset_class="FUNDOS", subtype="FII")).json()["id"]
    r = await ac.patch(f"/api/assets/{free}", json={"account_id": br2}, headers=h)
    assert r.status_code == 200 and r.json()["account_id"] == br2


async def test_posicao_ignora_op_futura(iac):
    """Aporte futuro (classes sem contrato aceitam) não entra na posição 'atual'."""
    from datetime import date, timedelta

    ac, h = iac, await _user(iac, "futop")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "FUT1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    await _op(ac, h, aid, {"kind": "APORTE", "date": tomorrow, "quantity": "10", "price": "100.00"})
    p = (await ac.get(f"/api/assets/{aid}/position", headers=h)).json()
    assert Decimal(p["quantity"]) == 0 and p["invested"] == "0.00"


async def test_tx_manual_em_corretora_atualiza_snapshot(iac):
    """INCOME/EXPENSE manual em conta INVESTMENT entra nos fluxos → atualiza a série."""
    from datetime import date

    ac, h = iac, await _user(iac, "snaptx")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT")
    r = await ac.post(
        "/api/transactions",
        json={
            "account_id": br,
            "date": "2026-09-05",
            "description": "APORTE EXTERNO",
            "amount": "500",
            "type": "INCOME",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    assert pf["net_invested"] == "500.00"
    assert any(s["date"] == date.today().isoformat() for s in pf["snapshots"])


async def test_snapshot_parcial_e_retomada(iac):
    """Um ativo cotado + outro sem cotação: caixa visível, total null; com preço, COMPLETE."""
    ac, h = iac, await _user(iac, "gap")
    cc = await _mk_account(ac, h, "Corrente", "CHECKING", "5000.00")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT")
    r = await ac.post(
        "/api/transfers", json={"from_account_id": cc, "to_account_id": br, "amount": "1500.00"}, headers=h
    )
    assert r.status_code == 201, r.text
    a1 = (await _mk_asset(ac, h, "COT1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]
    a2 = (await _mk_asset(ac, h, "SEM1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]
    await _op(ac, h, a1, {"kind": "APORTE", "date": "2026-04-01", "quantity": "10", "price": "100.00"})
    await _op(ac, h, a2, {"kind": "APORTE", "date": "2026-04-01", "quantity": "5", "price": "100.00"})
    await ac.post(f"/api/assets/{a1}/prices", json={"date": "2026-04-01", "price": "110.00"}, headers=h)

    pf = (await ac.get("/api/portfolio", headers=h)).json()
    assert pf["cash"] == "0.00"  # caixa continua conhecido
    assert pf["positions_value"] is None and pf["total"] is None and pf["resultado"] is None
    assert pf["status"] == "INCOMPLETE" and pf["unpriced"] == ["SEM1"]
    assert pf["xirr"] is None
    snap = [s for s in pf["snapshots"] if s["date"] == "2026-04-01"][0]
    assert snap["total"] is None and snap["status"] == "INCOMPLETE"

    # cotou tudo: linhas retomadas
    await ac.post(f"/api/assets/{a2}/prices", json={"date": "2026-04-02", "price": "120.00"}, headers=h)
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    assert pf["status"] == "COMPLETE" and pf["total"] == "1700.00" and pf["resultado"] == "200.00"


async def test_posicao_zerada_sem_preco_nao_marca_incompleto(iac):
    """Ativo resgatado por completo sem cotação: snapshot segue COMPLETE."""
    ac, h = iac, await _user(iac, "zeroq")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "ZERO1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-05-01", "quantity": "10", "price": "100.00"})
    await _op(ac, h, aid, {"kind": "RESGATE", "date": "2026-05-02", "quantity": "10", "price": "100.00"})
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    assert pf["status"] == "COMPLETE" and pf["unpriced"] == [] and pf["total"] == "1000.00"


async def test_snapshot_legacy_aparece_como_unknown(iac):
    """Linha escrita sem avaliação (defaults do model) aparece como UNKNOWN e sai do TWR."""
    from datetime import date as date_t

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.modules.investments.models import PortfolioSnapshot
    from tests.test_auth_int import DB_URL

    ac, h = iac, await _user(iac, "legacy")
    me = (await ac.get("/api/auth/me", headers=h)).json()
    engine = create_async_engine(DB_URL)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as s:
            s.add(PortfolioSnapshot(user_id=me["id"], date=date_t(2020, 1, 1), cash=100, positions_value=50, total=150))
            await s.commit()
    finally:
        await engine.dispose()
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    legacy = [s for s in pf["snapshots"] if s["date"] == "2020-01-01"][0]
    assert legacy["status"] == "UNKNOWN"
    assert pf["twr"] is None  # sem 2 pontos COMPLETE, sem TWR inventado


async def test_rendimento_categoria_incompativel(iac):
    """0.2: rendimento espelha INCOME — categoria EXPENSE (explícita ou do ativo) → 422."""
    ac, h = iac, await _user(iac, "inccat")
    r = await ac.post("/api/accounts", json={"name": "Corretora", "account_type": "CHECKING"}, headers=h)
    acc = r.json()["id"]
    r = await ac.post("/api/categories", json={"name": "Dividendos", "type": "INCOME"}, headers=h)
    div = r.json()["id"]
    r = await ac.post("/api/categories", json={"name": "Mercado", "type": "EXPENSE"}, headers=h)
    exp = r.json()["id"]
    r = await ac.post(
        "/api/assets",
        json={"ticker": "rend1", "asset_class": "RENDA_VARIAVEL", "subtype": "ACAO", "category_id": exp},
        headers=h,
    )
    aid = r.json()["id"]

    base = {"kind": "RENDIMENTO", "date": "2026-03-01", "amount": "25.00", "account_id": acc}
    assert (await ac.post(f"/api/assets/{aid}/ops", json={**base, "category_id": exp}, headers=h)).status_code == 422
    assert (await ac.post(f"/api/assets/{aid}/ops", json=base, headers=h)).status_code == 422  # default do ativo
    r = await ac.post(f"/api/assets/{aid}/ops", json={**base, "category_id": div}, headers=h)
    assert r.status_code == 201, r.text


async def test_assets_ops_position(iac):
    ac, h = iac, await _user(iac, "inv")
    acc = await _mk_account(ac, h, "Corretora", "INVESTMENT", "2000.00")
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
            "account_id": acc,
            "category_id": div,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    asset = r.json()
    assert asset["ticker"] == "PETR4"  # normalizado
    aid = asset["id"]

    # ticker duplicado na mesma conta → 409
    r = await ac.post(
        "/api/assets",
        json={"ticker": "PETR4", "asset_class": "RENDA_VARIAVEL", "subtype": "ACAO", "account_id": acc},
        headers=h,
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
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "ACAO7", br)).json()["id"]
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

    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "5000.00")
    r = await ac.post(
        "/api/assets",
        json={
            "ticker": "CDB7",
            "asset_class": "RENDA_FIXA",
            "subtype": "CDB",
            "rate_type": "CDI_PCT",
            "rate": "100",
            "account_id": br,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    assert r.json()["rate_type"] == "CDI_PCT"

    r = await ac.post(
        f"/api/assets/{aid}/ops",
        json={"kind": "APORTE", "date": "2026-09-25", "amount": "1000"},
        headers=h,
    )
    assert r.status_code == 201

    r = await ac.get(f"/api/assets/{aid}/position", headers=h)
    p = r.json()
    assert p["price_source"] == "ACCRUAL", p
    # 25, 26(sex?) ...: valor > 1000 pelo CDI 0.05%/du
    assert Decimal(p["current_value"]) > Decimal("1000")

    # snapshot do accrual persiste na operação com commit (não em leitura GET)
    r = await ac.get(f"/api/assets/{aid}/prices", headers=h)
    assert any(x["source"] == "ACCRUAL" for x in r.json()), r.text

    # IPCA_MAIS cai para manual (sem preço → nulos)
    r = await ac.post(
        "/api/assets",
        json={
            "ticker": "LCA7",
            "asset_class": "RENDA_FIXA",
            "subtype": "LCI_LCA",
            "rate_type": "IPCA_MAIS",
            "rate": "6",
            "account_id": br,
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
    rt_acc = await _mk_account(ac, h, "Corretora", "INVESTMENT", "2000.00")
    aid = (await _mk_asset(ac, h, "FUN7", rt_acc, asset_class="OUTROS", subtype="OUTRO")).json()["id"]
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


async def test_rf_primeiro_aporte_sem_bcb(iac, monkeypatch):
    """Cotação no próprio dia do aporte é 1,0 por definição: BCB fora não gera INCOMPLETE."""
    from app.modules.market import bcb

    async def boom(start, end, timeout_s=15, client=None):
        raise bcb.BcbError("fora")

    monkeypatch.setattr(bcb, "cdi_range", boom)

    ac, h = iac, await _user(iac, "rfday1")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "10000.00")
    aid = (
        await _mk_asset(ac, h, "CDBD1", br, asset_class="RENDA_FIXA", subtype="CDB", rate_type="CDI_PCT", rate="115")
    ).json()["id"]
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-03-01", "amount": "5172.45"})
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    by_date = {s["date"]: s for s in pf["snapshots"]}
    snap = by_date["2026-03-01"]
    assert snap["status"] == "COMPLETE" and snap["total"] == "10000.00"
    # Com o BCB fora, a posição *atual* (meses depois) segue sem cotação: honesto.
    assert pf["unpriced"] == ["CDBD1"]


async def test_snapshot_rebuild_para_frente(iac):
    """Evento retroativo recalcula as linhas posteriores: nada de zero obsoleto no gráfico."""
    from datetime import date

    ac, h = iac, await _user(iac, "fwd")
    cc = await _mk_account(ac, h, "Corrente", "CHECKING", "5000.00")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT")
    r = await ac.post(
        "/api/transfers", json={"from_account_id": cc, "to_account_id": br, "amount": "2000.00"}, headers=h
    )
    assert r.status_code == 201, r.text
    today = date.today().isoformat()
    by_date = {s["date"]: s for s in (await ac.get("/api/portfolio", headers=h)).json()["snapshots"]}
    assert by_date[today]["cash"] == "2000.00"

    aid = (await _mk_asset(ac, h, "FWD1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-05", "quantity": "15", "price": "100.00"})
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-01-05", "price": "100.00"}, headers=h)

    pf = (await ac.get("/api/portfolio", headers=h)).json()
    by_date = {s["date"]: s for s in pf["snapshots"]}
    assert "2026-01-05" in by_date  # linha do evento retroativo existe
    assert by_date[today]["cash"] == "500.00"  # 2000 − 1500: linha posterior recalculada
    assert by_date[today]["status"] == "COMPLETE" and by_date[today]["total"] == "2000.00"


async def test_conta_nova_ou_removida_reconstroi_serie(iac):
    """Criar/remover conta muda o caixa de todas as datas: série inteira recalculada."""
    from datetime import date

    ac, h = iac, await _user(iac, "initcash")
    await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    today = date.today().isoformat()
    by_date = {s["date"]: s for s in (await ac.get("/api/portfolio", headers=h)).json()["snapshots"]}
    assert by_date[today]["cash"] == "1000.00"

    extra = await _mk_account(ac, h, "Extra", "INVESTMENT", "500.00")
    by_date = {s["date"]: s for s in (await ac.get("/api/portfolio", headers=h)).json()["snapshots"]}
    assert by_date[today]["cash"] == "1500.00"

    assert (await ac.delete(f"/api/accounts/{extra}", headers=h)).status_code == 204
    by_date = {s["date"]: s for s in (await ac.get("/api/portfolio", headers=h)).json()["snapshots"]}
    assert by_date[today]["cash"] == "1000.00"


async def test_portfolio_rebuild_endpoint(iac):
    """POST /api/portfolio/rebuild repara linhas obsoletas sem novos eventos."""
    ac, h = iac, await _user(iac, "reb")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "REB1", br, asset_class="FUNDOS", subtype="FII")).json()["id"]
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-02-01", "quantity": "10", "price": "100.00"})
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-02-01", "price": "100.00"}, headers=h)
    r = await ac.post("/api/portfolio/rebuild", headers=h)
    assert r.status_code == 200, r.text
    assert "2026-02-01" in r.json()["rebuilt"]
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    assert pf["status"] == "COMPLETE" and pf["total"] == "1000.00"


async def test_resgate_com_ir_retido(iac):
    """0018: RESGATE com fees (IR retido): caixa recebe o líquido; posição mostra líquido est. auto."""
    ac, h = iac, await _user(iac, "irf")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "IRF1", br)).json()["id"]

    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"})
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-02-01", "price": "110.00"}, headers=h)

    p = (await ac.get(f"/api/assets/{aid}/position", headers=h)).json()
    assert p["current_value"] == "1100.00" and p["invested"] == "1000.00"
    assert p["net_rate"] == "15" and p["net_rate_source"] == "auto"
    assert p["net_tax"] == "15.00" and p["net_value"] == "1085.00"

    # bruto 4×120=480 − IR 30 → líquido 450 no caixa, com data passada
    op = await _op(
        ac, h, aid, {"kind": "RESGATE", "date": "2026-03-01", "quantity": "4", "price": "120.00", "fees": "30.00"}
    )
    assert op["amount"] == "450.00" and op["fees"] == "30.00"
    assert (await ac.get(f"/api/accounts/{br}", headers=h)).json()["current_balance"] == "450.00"
    p = (await ac.get(f"/api/assets/{aid}/position", headers=h)).json()
    assert p["resgates"] == "450.00" and Decimal(p["quantity"]) == 6


async def test_tax_rate_manual(iac):
    """0018: PATCH tax_rate sobrescreve a auto; fora de 0–100 rejeita."""
    ac, h = iac, await _user(iac, "txm")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    body = {"ticker": "TXM1", "asset_class": "RENDA_VARIAVEL", "subtype": "ACAO", "account_id": br, "tax_rate": "10"}
    aid = (await ac.post("/api/assets", json=body, headers=h)).json()["id"]
    assert (await ac.get(f"/api/assets/{aid}", headers=h)).json()["tax_rate"] == "10.00"

    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"})
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-02-01", "price": "110.00"}, headers=h)
    p = (await ac.get(f"/api/assets/{aid}/position", headers=h)).json()
    assert p["net_rate"] == "10.00" and p["net_rate_source"] == "manual"
    assert p["net_tax"] == "10.00" and p["net_value"] == "1090.00"

    r = await ac.patch(f"/api/assets/{aid}", json={"tax_rate": "101"}, headers=h)
    assert r.status_code == 422, r.text
    r = await ac.patch(f"/api/assets/{aid}", json={"tax_rate": "-1"}, headers=h)
    assert r.status_code == 422, r.text


async def test_rf_resgate_total_com_ir_e_data_passada(iac, monkeypatch):
    """0018: full + fees + data passada: líquido no caixa, posição zerada."""
    from app.modules.market import bcb

    async def fake_cdi(start, end, timeout_s=15, client=None):
        out, cur = {}, start
        while cur <= end:
            if cur.weekday() < 5:
                out[cur] = Decimal("0.05")
            cur += timedelta(days=1)
        return out

    monkeypatch.setattr(bcb, "cdi_range", fake_cdi)

    ac, h = iac, await _user(iac, "rff")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "5000.00")
    asset = await _mk_asset(ac, h, "CDBF", br, asset_class="RENDA_FIXA", subtype="CDB", rate_type="CDI_PCT", rate="100")
    aid = asset.json()["id"]

    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-09-25", "amount": "1000.00"})
    op = await _op(ac, h, aid, {"kind": "RESGATE", "date": "2026-09-27", "fees": "50.00", "full": True})
    assert op["fees"] == "50.00" and Decimal(op["amount"]) > 0
    bal = (await ac.get(f"/api/accounts/{br}", headers=h)).json()["current_balance"]
    assert Decimal(bal) == Decimal("4000.00") + Decimal(op["amount"])
    p = (await ac.get(f"/api/assets/{aid}/position", headers=h)).json()
    assert Decimal(p["quantity"]) == 0 and p["invested"] == "0.00"


async def test_snapshot_gain_sem_aporte(iac):
    """0018b: snapshots carregam gain (total − aportes líquidos); INCOMPLETE segue null."""
    ac, h = iac, await _user(iac, "gain")
    br = await _mk_account(ac, h, "Corretora", "INVESTMENT", "1000.00")
    aid = (await _mk_asset(ac, h, "GAIN1", br)).json()["id"]
    await _op(ac, h, aid, {"kind": "APORTE", "date": "2026-01-10", "quantity": "10", "price": "100.00"})
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-02-01", "price": "110.00"}, headers=h)
    await ac.post(f"/api/assets/{aid}/prices", json={"date": "2026-03-01", "price": "120.00"}, headers=h)
    pf = (await ac.get("/api/portfolio", headers=h)).json()
    by_date = {s["date"]: s for s in pf["snapshots"]}
    assert by_date["2026-01-10"]["gain"] is None  # sem preço na data: INCOMPLETE
    assert by_date["2026-02-01"]["gain"] == "0.00"  # 1º ponto COMPLETE zera
    assert by_date["2026-03-01"]["gain"] == "100.00"  # 1200 − 1100, sem fluxos
