from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken


async def store(session: AsyncSession, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
    row = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at, created_at=datetime.now(UTC))
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_active(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    res = await session.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    return res.scalar_one_or_none()


async def get_any(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    res = await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    return res.scalar_one_or_none()


async def revoke(session: AsyncSession, token_id: int) -> None:
    await session.execute(update(RefreshToken).where(RefreshToken.id == token_id).values(revoked_at=datetime.now(UTC)))
    await session.commit()


async def revoke_all_for_user(session: AsyncSession, user_id: int) -> int:
    res = await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
    return res.rowcount or 0
