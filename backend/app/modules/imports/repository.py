from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.imports.models import Import, ImportItem


async def get_import(session: AsyncSession, user_id: int, import_id: int) -> Import | None:
    res = await session.execute(
        select(Import).where(Import.id == import_id, Import.user_id == user_id)
    )
    return res.scalar_one_or_none()


async def list_imports(session: AsyncSession, user_id: int, limit: int = 50) -> list[Import]:
    res = await session.execute(
        select(Import).where(Import.user_id == user_id).order_by(Import.id.desc()).limit(limit)
    )
    return list(res.scalars().all())


async def count_items(session: AsyncSession, import_id: int) -> dict:
    res = await session.execute(
        select(ImportItem.verdict, func.count())
        .where(ImportItem.import_id == import_id)
        .group_by(ImportItem.verdict)
    )
    return {verdict: n for verdict, n in res.all()}


async def list_items(session: AsyncSession, user_id: int, import_id: int, verdict: str | None = None):
    imp = await get_import(session, user_id, import_id)
    if imp is None:
        return None
    q = select(ImportItem).where(ImportItem.import_id == import_id).order_by(ImportItem.row_no)
    if verdict:
        q = q.where(ImportItem.verdict == verdict)
    res = await session.execute(q)
    return list(res.scalars().all())
