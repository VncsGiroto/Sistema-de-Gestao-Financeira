from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.modules.auth.audit_models import AuditLog
from app.modules.finance.models import Transaction
from app.modules.imports.duplicate_detector import Candidate, is_fuzzy
from app.modules.imports.models import Import, ImportItem
from app.modules.imports.normalizer import NormalizedTx, OfxImporter


async def _classify(session, imp: Import, norm: NormalizedTx) -> tuple[str, dict, int | None]:
    """Retorna (verdict, payload_extra, matched_id)."""
    res = await session.execute(
        select(Transaction.id).where(
            Transaction.user_id == imp.user_id,
            Transaction.source == norm.source,
            Transaction.external_id == norm.external_id,
        )
    )
    row = res.first()
    if row:
        return "EXACT_DUPLICATE", {}, row[0]
    window = settings.dedup_window_days
    res = await session.execute(
        select(Transaction).where(
            Transaction.user_id == imp.user_id,
            Transaction.account_id == norm.account_id,
            Transaction.date >= norm.date - timedelta(days=window),
            Transaction.date <= norm.date + timedelta(days=window),
            Transaction.amount == Decimal(norm.amount),
        )
    )
    best: tuple[float, Transaction] | None = None
    for tx in res.scalars().all():
        ok, score = is_fuzzy(
            norm.account_id, norm.date, norm.description, Decimal(norm.amount),
            Candidate(id=tx.id, account_id=tx.account_id, date=tx.date, description=tx.description, amount=tx.amount),
            window_days=window,
        )
        if ok and (best is None or score > best[0]):
            best = (score, tx)
    if best:
        return "FUZZY_CANDIDATE", {"score": best[0]}, best[1].id
    return "NEW", {}, None


async def process_import(import_id: int) -> None:
    """Roda em BackgroundTask com sessão própria (a sessão do request já fechou)."""
    from app.core.db import SessionLocal  # lazy: respeita SessionLocal trocado em testes

    importer = OfxImporter()
    async with SessionLocal() as session:
        imp = await session.get(Import, import_id)
        if imp is None or imp.status not in ("RECEIVED",):
            return
        imp.status = "PROCESSING"
        await session.commit()
        try:
            with open(imp.file_path, "rb") as fh:
                raw = fh.read()
            raws = importer.parse(raw)
            imp.total_rows = len(raws)
            exact = 0
            for i, r in enumerate(raws):
                norm = importer.normalize(r, imp.account_id)
                if norm is None:
                    verdict, payload, matched = "INVALID", {"raw": {"memo": r.memo, "name": r.name}}, None
                else:
                    verdict, extra, matched = await _classify(session, imp, norm)
                    payload = norm.model_dump(mode="json") | {"raw": {"memo": r.memo, "name": r.name}} | extra
                    if verdict == "EXACT_DUPLICATE":
                        exact += 1
                session.add(ImportItem(import_id=imp.id, row_no=i + 1, payload=payload, verdict=verdict, matched_transaction_id=matched))
            imp.duplicate_rows = exact
            imp.status = "VALIDATED"
            imp.processed_at = datetime.now(UTC)
            session.add(AuditLog(user_id=imp.user_id, action="import.validated", created_at=datetime.now(UTC)))
            await session.commit()
        except Exception as e:
            imp.status = "FAILED"
            imp.error = str(e)[:500]
            imp.processed_at = datetime.now(UTC)
            await session.commit()


class ReviewError(ValueError):
    pass


class CommitBlocked(ValueError):
    pass


async def review(session, user_id: int, import_id: int, decisions: list[dict]) -> int:
    from app.modules.imports.models import ImportItem
    from sqlalchemy import select

    imp = await session.get(Import, import_id)
    if imp is None or imp.user_id != user_id:
        raise LookupError("import")
    if imp.status != "VALIDATED":
        raise ReviewError("Import não está aguardando revisão")
    n = 0
    for d in decisions:
        item_id, decision = d.get("item_id"), d.get("decision")
        if decision not in ("KEEP_BOTH", "DISCARD_IMPORTED"):
            raise ReviewError(f"decision inválida: {decision}")
        res = await session.execute(
            select(ImportItem).where(ImportItem.id == item_id, ImportItem.import_id == import_id)
        )
        item = res.scalar_one_or_none()
        if item is None:
            raise ReviewError(f"item {item_id} não pertence ao import")
        if item.verdict not in ("EXACT_DUPLICATE", "FUZZY_CANDIDATE"):
            raise ReviewError(f"item {item_id} não precisa de revisão ({item.verdict})")
        item.decision = decision
        item.decided_at = datetime.now(UTC)
        n += 1
    session.add(AuditLog(user_id=user_id, action="dedup.decide", created_at=datetime.now(UTC)))
    await session.commit()
    return n


async def commit(session, user_id: int, import_id: int) -> dict:
    from datetime import date as date_t
    from decimal import Decimal

    from sqlalchemy import select

    from app.modules.imports.models import ImportItem

    imp = await session.get(Import, import_id)
    if imp is None or imp.user_id != user_id:
        raise LookupError("import")
    if imp.status == "IMPORTED":
        return {"imported_rows": imp.imported_rows, "duplicate_rows": imp.duplicate_rows, "skipped": 0}
    if imp.status != "VALIDATED":
        raise CommitBlocked("Import ainda não validado")
    res = await session.execute(select(ImportItem).where(ImportItem.import_id == import_id).order_by(ImportItem.row_no))
    items = list(res.scalars().all())
    pending = [i for i in items if i.verdict in ("EXACT_DUPLICATE", "FUZZY_CANDIDATE") and not i.decision]
    if pending:
        raise CommitBlocked(f"{len(pending)} itens aguardando revisão")
    imported, dups, skipped = 0, 0, 0
    seen_external: set[str] = set()
    for it in items:
        if it.verdict == "INVALID":
            skipped += 1
            continue
        if it.verdict in ("EXACT_DUPLICATE", "FUZZY_CANDIDATE"):
            if it.decision == "DISCARD_IMPORTED":
                dups += 1
                continue
            # KEEP_BOTH: só sufixa quando há conflito certo (EXACT); FUZZY mantém o FITID
            base_ext = it.payload.get("external_id")
            ext = f"{base_ext}#keep{it.row_no}" if it.verdict == "EXACT_DUPLICATE" else base_ext
        else:
            if it.matched_transaction_id:
                continue  # já convertido (idempotência intra-lote)
            ext = it.payload.get("external_id")
        if ext in seen_external:
            dups += 1  # duplicado dentro do próprio lote
            continue
        seen_external.add(ext)
        tx = Transaction(
            user_id=user_id, account_id=imp.account_id,
            category_id=None,
            date=date_t.fromisoformat(it.payload["date"]),
            description=it.payload["description"][:500],
            amount=Decimal(it.payload["amount"]),
            type=it.payload["type"], source="OFX", external_id=ext, import_id=imp.id,
        )
        session.add(tx)
        await session.flush()
        it.matched_transaction_id = tx.id
        imported += 1
    imp.imported_rows = imported
    imp.duplicate_rows = dups
    imp.status = "IMPORTED"
    imp.processed_at = datetime.now(UTC)
    session.add(AuditLog(user_id=user_id, action="import.commit", created_at=datetime.now(UTC)))
    await session.commit()
    return {"imported_rows": imported, "duplicate_rows": dups, "skipped": skipped}
