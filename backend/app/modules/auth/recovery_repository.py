import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth import tokens
from app.modules.auth.recovery_models import PasswordReset

log = logging.getLogger("financeway.auth")


async def invalidate_open_for_user(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user_id, PasswordReset.used_at.is_(None))
        .values(used_at=tokens._now())
    )


async def create_for_user(session: AsyncSession, user_id: int) -> tuple[str, PasswordReset]:
    from datetime import UTC, datetime

    await invalidate_open_for_user(session, user_id)
    token, exp = tokens.create_recovery_token(user_id)
    row = PasswordReset(
        user_id=user_id,
        token_hash=tokens.sha256_hex(token),
        expires_at=exp,
        created_at=datetime.now(UTC),
    )
    session.add(row)
    await session.flush()
    # dev: token visível no log (sem SMTP no MVP)
    log.warning("recovery token user_id=%s token=%s", user_id, token)
    return token, row


async def consume(session: AsyncSession, token: str) -> PasswordReset:
    try:
        user_id = tokens.decode_token(token, "recovery")
    except ValueError as e:
        raise ValueError(str(e))
    res = await session.execute(select(PasswordReset).where(PasswordReset.token_hash == tokens.sha256_hex(token)))
    row = res.scalar_one_or_none()
    if row is None or row.used_at is not None or row.expires_at <= tokens._now() or row.user_id != user_id:
        raise ValueError("Token inválido ou expirado")
    return row


async def mark_used(session: AsyncSession, row: PasswordReset) -> None:
    row.used_at = tokens._now()
    await session.flush()
