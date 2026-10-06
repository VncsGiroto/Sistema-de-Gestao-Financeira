from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflict
from app.modules.finance.models import Account, Category
from app.modules.investments.models import Asset, InvestmentOp
from app.modules.investments.position import position as calc_position
from app.modules.market.models import AssetPrice  # noqa: F401 — registra metadata p/ drop_all/create_all


async def _owned_category(session: AsyncSession, user_id: int, category_id: int | None):
    if category_id is None:
        return None
    res = await session.execute(select(Category).where(Category.id == category_id, Category.user_id == user_id))
    return res.scalar_one_or_none()


async def _owned_investment_account(session: AsyncSession, user_id: int, account_id: int | None):
    """Conta do usuário E do tipo INVESTMENT; None passa (legado sem vínculo)."""
    if account_id is None:
        return None
    res = await session.execute(select(Account).where(Account.id == account_id, Account.user_id == user_id))
    acc = res.scalar_one_or_none()
    if acc is None:
        raise LookupError("account")
    if acc.account_type != "INVESTMENT":
        raise ValueError("Conta vinculada deve ser do tipo Investimento")
    return acc


async def list_assets(session: AsyncSession, user_id: int, asset_class: str | None = None) -> list[Asset]:
    q = select(Asset).where(Asset.user_id == user_id)
    if asset_class:
        q = q.where(Asset.asset_class == asset_class)
    res = await session.execute(q.order_by(Asset.ticker))
    return list(res.scalars().all())


async def get_asset(session: AsyncSession, user_id: int, asset_id: int) -> Asset | None:
    res = await session.execute(select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id))
    return res.scalar_one_or_none()


async def create_asset(
    session: AsyncSession,
    user_id: int,
    ticker: str,
    name: str | None,
    asset_class: str,
    subtype: str,
    custodian: str | None,
    account_id: int | None,
    category_id: int | None,
    rate_type: str | None = None,
    rate=None,
    maturity_date=None,
) -> Asset:
    if category_id is not None and await _owned_category(session, user_id, category_id) is None:
        raise LookupError("category")
    await _owned_investment_account(session, user_id, account_id)
    validate_rate(asset_class, rate_type, rate)
    row = Asset(
        user_id=user_id,
        ticker=ticker.strip().upper(),
        name=name,
        asset_class=asset_class,
        subtype=subtype.strip().upper(),
        custodian=custodian,
        account_id=account_id,
        category_id=category_id,
        rate_type=rate_type,
        rate=rate,
        maturity_date=maturity_date,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise conflict("Ticker já cadastrado nesta conta")
    await session.refresh(row)
    return row


async def delete_asset(session: AsyncSession, row: Asset) -> None:
    await session.delete(row)
    await session.commit()


async def list_ops(session: AsyncSession, user_id: int, asset_id: int, end: date | None = None) -> list[InvestmentOp]:
    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    q = select(InvestmentOp).where(InvestmentOp.asset_id == asset_id, InvestmentOp.user_id == user_id)
    if end is not None:
        q = q.where(InvestmentOp.date <= end)
    res = await session.execute(q.order_by(InvestmentOp.date, InvestmentOp.id))
    return list(res.scalars().all())


async def _contract_quote_or_raise(session: AsyncSession, asset, on) -> Decimal:
    """Cotação do contrato na data da operação (1,0 sem posição anterior). Sem cotação → 422."""
    from app.modules.market.prices import contract_quote

    q = await contract_quote(session, asset, on)
    if q is None:
        raise ValueError("Sem cotação do contrato na data da operação")
    return q


async def add_op(
    session: AsyncSession,
    user_id: int,
    asset_id: int,
    kind: str,
    on: date,
    quantity,
    price,
    fees: Decimal,
    amount,
    account_id: int | None = None,
    category_id: int | None = None,
    full: bool = False,
) -> InvestmentOp:
    from datetime import date as today_fn

    from app.modules.finance.models import Account, Transaction
    from app.modules.investments import portfolio as pf

    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    contracted = asset.asset_class == "RENDA_FIXA" and asset.rate_type in ("CDI_PCT", "PREFIXADO")
    if kind == "REINVESTIMENTO" and fees != 0:
        raise ValueError("REINVESTIMENTO não aceita taxas")
    if full and (kind != "RESGATE" or not contracted):
        raise ValueError("Resgate total só para renda fixa com contrato")
    if contracted and on > today_fn.today():
        raise ValueError("Operação futura sem cotação do contrato")
    if kind in ("APORTE", "RESGATE", "REINVESTIMENTO") and contracted:
        # Modo valor (R$): a UI nunca envia quantidade/preço; conversão interna pela cotação.
        if quantity is not None or price is not None:
            raise ValueError("Informe apenas o valor em reais")
        if kind == "RESGATE" and full:
            if amount is not None:
                raise ValueError("Resgate total não combina com amount")
            pos0 = await get_position(session, user_id, asset_id)
            if pos0["quantity"] <= 0:
                raise ValueError("Posição zerada")
            quote0 = await _contract_quote_or_raise(session, asset, on)
            quantity, price = pos0["quantity"], quote0
            amount = (quantity * quote0).quantize(Decimal("0.01"))
        else:
            if amount is None or amount <= 0:
                raise ValueError("Informe o valor em reais")
            quote = await _contract_quote_or_raise(session, asset, on)
            quantity = (Decimal(amount) / quote).quantize(Decimal("0.00000001"))
            price = quote
            amount = (quantity * quote).quantize(Decimal("0.01"))
            if kind == "RESGATE":
                pos = await get_position(session, user_id, asset_id)
                if quantity > pos["quantity"]:
                    raise ValueError("Valor do resgate excede a posição; use Resgatar tudo para liquidar")
    if kind in ("APORTE", "RESGATE"):
        if quantity is None or price is None:
            raise ValueError("APORTE/RESGATE exigem quantity e price")
        if asset.account_id is None:
            raise ValueError("Vincule uma conta de investimento ao ativo antes de aportar ou resgatar")
        computed = (quantity * price + fees) if kind == "APORTE" else (quantity * price - fees)
        if computed <= 0:
            raise ValueError("Valor da operação deve ser positivo")
        if kind == "RESGATE":
            pos = await get_position(session, user_id, asset_id)
            if quantity > pos["quantity"]:
                raise ValueError("Quantidade maior que a posição")
            amount = computed
        else:
            amount = computed
        # Lock pessimista + caixa suficiente (concorrência real no PostgreSQL).
        acc_res = await session.execute(
            select(Account).where(Account.id == asset.account_id, Account.user_id == user_id).with_for_update()
        )
        if acc_res.scalar_one_or_none() is None:
            raise LookupError("account")
        if kind == "RESGATE":
            # Revalida após o lock: um resgate concorrente pode ter consumido a posição
            # entre a conversão em valor e aqui. `full` usa a posição fresca; parcial
            # acima da posição → 422 (nunca liquida silenciosamente).
            fresh = await get_position(session, user_id, asset_id)
            if full:
                if fresh["quantity"] <= 0:
                    raise ValueError("Posição zerada")
                quantity = fresh["quantity"]
            elif quantity > fresh["quantity"]:
                raise ValueError("Valor do resgate excede a posição; use Resgatar tudo para liquidar")
            amount = quantity * price - fees
            if amount <= 0:
                raise ValueError("Valor da operação deve ser positivo")
        if kind == "APORTE":
            from app.modules.finance import repository as finance_repo

            bal = await finance_repo.account_summaries(session, user_id, date.today())
            s = bal.get(asset.account_id, {})
            acc_row = await finance_repo.get_account(session, user_id, asset.account_id)
            cur = (
                (acc_row.initial_balance if acc_row else Decimal("0"))
                + s.get("income", Decimal("0"))
                - s.get("expense", Decimal("0"))
                + s.get("ledger_in", Decimal("0"))
                - s.get("ledger_out", Decimal("0"))
            )
            if cur < amount:
                raise ValueError("Caixa insuficiente na conta para o aporte")
    elif kind == "REINVESTIMENTO":
        # Fluxo interno: soma posição e custo, sem receita no extrato e sem caixa.
        if quantity is None or price is None:
            raise ValueError("REINVESTIMENTO exige quantity e price")
        computed = quantity * price + fees
        if computed <= 0:
            raise ValueError("Valor da operação deve ser positivo")
        amount = computed
    else:  # RENDIMENTO
        if amount is None or amount <= 0:
            raise ValueError("RENDIMENTO exige amount positivo")
    row = InvestmentOp(
        user_id=user_id, asset_id=asset_id, kind=kind, date=on, quantity=quantity, price=price, fees=fees, amount=amount
    )
    session.add(row)
    await session.flush()
    if kind in ("APORTE", "RESGATE"):
        # Caixa da corretora na mesma transação de banco (atomicidade).
        from app.modules.ledger.models import LedgerMovement

        session.add(
            LedgerMovement(
                user_id=user_id,
                from_account_id=asset.account_id if kind == "APORTE" else None,
                to_account_id=asset.account_id if kind == "RESGATE" else None,
                kind=kind,
                amount=amount,
                date=on,
                description=f"{'Aporte' if kind == 'APORTE' else 'Resgate'} {asset.ticker}",
                op_id=row.id,
                asset_id=asset_id,
            )
        )
        await session.flush()
    if kind == "RENDIMENTO":
        # espelha no extrato como INCOME rastreável (simétrico ao pay de payables)
        if account_id is None:
            raise ValueError("RENDIMENTO exige account_id")
        res = await session.execute(select(Account).where(Account.id == account_id, Account.user_id == user_id))
        if res.scalar_one_or_none() is None:
            raise LookupError("account")
        cat = category_id if category_id is not None else asset.category_id
        if cat is not None:
            cat_res = await session.execute(select(Category).where(Category.id == cat, Category.user_id == user_id))
            owned = cat_res.scalar_one_or_none()
            if owned is None:
                raise LookupError("category")
            if owned.type != "INCOME":
                raise ValueError("Categoria incompatível: o rendimento gera uma receita")
        tx = Transaction(
            user_id=user_id,
            account_id=account_id,
            category_id=cat,
            date=on,
            description=f"Rendimento {asset.ticker}",
            amount=amount,
            type="INCOME",
            source="MANUAL",
        )
        session.add(tx)
        await session.flush()
        row.transaction_id = tx.id
    await pf.upsert_snapshot(session, user_id, on)
    await session.commit()
    await session.refresh(row)
    return row


async def delete_op(session: AsyncSession, user_id: int, asset_id: int, op_id: int) -> bool:
    from app.modules.finance.models import Transaction

    res = await session.execute(
        select(InvestmentOp).where(
            InvestmentOp.id == op_id, InvestmentOp.asset_id == asset_id, InvestmentOp.user_id == user_id
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        return False
    if row.transaction_id is not None:
        tx = await session.get(Transaction, row.transaction_id)
        if tx is not None and tx.user_id == user_id:
            await session.delete(tx)
    await session.delete(row)
    await session.flush()
    from app.modules.investments import portfolio as pf

    await pf.upsert_snapshot(session, user_id)
    await session.commit()
    return True


async def get_position(session: AsyncSession, user_id: int, asset_id: int, end: date | None = None) -> dict:
    ops = await list_ops(session, user_id, asset_id, end)
    return calc_position(
        [{"kind": o.kind, "quantity": o.quantity, "price": o.price, "fees": o.fees, "amount": o.amount} for o in ops]
    )


def validate_rate(asset_class: str, rate_type: str | None, rate) -> None:
    if asset_class == "RENDA_FIXA" and rate_type is not None and rate is None:
        raise ValueError("rate_type exige rate")
    if rate_type is None and rate is not None:
        raise ValueError("rate exige rate_type")


async def set_manual_price(
    session: AsyncSession, user_id: int, asset_id: int, on, price, override: bool = False
) -> dict:
    from app.modules.investments import portfolio as pf

    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    contracted = asset.asset_class == "RENDA_FIXA" and asset.rate_type in ("CDI_PCT", "PREFIXADO")
    source = "MANUAL_OVERRIDE" if (contracted and override) else "MANUAL"
    if contracted and not override:
        raise ValueError("RF com contrato usa a cotação do contrato; preço manual só como exceção explícita")
    res = await session.execute(
        select(AssetPrice).where(AssetPrice.asset_id == asset_id, AssetPrice.date == on, AssetPrice.source == source)
    )
    row = res.scalar_one_or_none()
    if row is None:
        row = AssetPrice(user_id=user_id, asset_id=asset_id, date=on, price=price, source=source)
        session.add(row)
    else:
        row.price = price
    await session.flush()
    await pf.upsert_snapshot(session, user_id, on)
    await session.commit()
    await session.refresh(row)
    return {"id": row.id, "date": row.date, "price": row.price, "source": row.source}


async def price_history(session: AsyncSession, user_id: int, asset_id: int) -> list[dict]:
    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    res = await session.execute(select(AssetPrice).where(AssetPrice.asset_id == asset_id).order_by(AssetPrice.date))
    return [{"id": r.id, "date": r.date, "price": r.price, "source": r.source} for r in res.scalars().all()]


async def get_returns(session: AsyncSession, user_id: int, asset_id: int, end) -> dict:
    """Simples + XIRR + TWR + benchmarks. Sem preço => métricas temporais None."""
    from app.modules.investments import returns as ret
    from app.modules.market import benchmarks as bench
    from app.modules.market.prices import resolve_price

    asset = await get_asset(session, user_id, asset_id)
    if asset is None:
        raise LookupError("asset")
    # Leituras "atuais" ignoram operações futuras (aceitas p/ classes sem contrato).
    ops = [o for o in await list_ops(session, user_id, asset_id) if o.date <= end]
    if not ops:
        return {
            "start": None,
            "end": end,
            "simple": None,
            "xirr": None,
            "twr": None,
            "twr_annualized": None,
            "benchmarks": {},
        }
    start = ops[0].date

    prices = await price_history(session, user_id, asset_id)
    hist = sorted(((p["date"], Decimal(p["price"])) for p in prices), key=lambda x: x[0])

    def price_at(d):
        cands = [pr for dt, pr in hist if dt <= d]
        if cands:
            return cands[-1]
        for o in ops:
            if o.date <= d and o.price:
                return Decimal(o.price)
        return None

    pos = await get_position(session, user_id, asset_id, end)
    cur = await resolve_price(session, asset, end)
    cur_value = (cur.price * pos["quantity"]).quantize(Decimal("0.01")) if cur and pos["quantity"] > 0 else None

    # XIRR: aportes −, resgates/rendimentos +, REINVESTIMENTO excluído (fluxo interno),
    # valor atual como fluxo final.
    flows = []
    for o in ops:
        if o.kind == "REINVESTIMENTO":
            continue
        amt = Decimal(o.amount)
        flows.append((o.date, -amt if o.kind == "APORTE" else amt))
    if cur_value is not None and cur_value > 0:
        flows.append((end, cur_value))
    xirr = ret.xirr(flows)

    # TWR por cotas: value antes de cada fluxo + valor final. REINVESTIMENTO é aporte interno.
    events, qty, twr_ok = [], Decimal("0"), True
    for o in ops:
        p = price_at(o.date)
        if p is None:
            twr_ok = False
            break
        value_before = qty * p
        amt = Decimal(o.amount)
        flow = -amt if o.kind in ("RESGATE", "RENDIMENTO") else amt
        events.append({"date": o.date, "flow": flow, "value": value_before})
        if o.kind in ("APORTE", "REINVESTIMENTO"):
            qty += Decimal(o.quantity or 0)
        elif o.kind == "RESGATE":
            qty -= Decimal(o.quantity or 0)
    twr = twr_ann = None
    if twr_ok and cur_value is not None:
        events.append({"date": end, "flow": Decimal("0"), "value": cur_value})
        twr = ret.unitize(events)
        if twr is not None:
            twr_ann = ret.annualize(twr, (end - start).days)

    simple = None
    external = pos["aportes"] - pos["resgates"]
    if external > 0 and cur_value is not None:
        # Retorno sobre capital externo (reinvest é ganho, não capital).
        simple = (cur_value + pos["resgates"] + pos["rendimentos"] - pos["aportes"]) / external

    benchmarks = {
        "cdi": await bench.cdi_return(start, end),
        "ipca": await bench.ipca_return(start, end),
    }
    return {
        "start": start,
        "end": end,
        "simple": simple,
        "xirr": xirr,
        "twr": twr,
        "twr_annualized": twr_ann,
        "benchmarks": benchmarks,
    }
