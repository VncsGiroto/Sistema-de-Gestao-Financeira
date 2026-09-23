from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth import recovery_repository as recovery_repo
from app.modules.auth import repository as refresh_repo
from app.modules.auth import tokens
from app.modules.auth.audit_models import AuditLog
from app.modules.users import repository as users_repo
from app.modules.users.passwords import hash_password, verify_password


async def _audit(session: AsyncSession, user_id: int, action: str) -> None:
    session.add(AuditLog(user_id=user_id, action=action, created_at=datetime.now(UTC)))


async def register(session: AsyncSession, name: str, email: str, password: str):
    user = await users_repo.create(session, name, email, password)
    await _audit(session, user.id, "auth.register")
    await session.commit()
    return user


async def login(session: AsyncSession, email: str, password: str):
    user = await users_repo.get_by_email(session, email.strip().lower())
    if user is None or not verify_password(password, user.password_hash):
        raise ValueError("Credenciais inválidas")
    access, ttl = tokens.create_access_token(user.id)
    refresh, refresh_hash, exp = tokens.create_refresh_token(user.id)
    await refresh_repo.store(session, user.id, tokens.sha256_hex(refresh), exp)
    await _audit(session, user.id, "auth.login")
    await session.commit()
    return user, access, refresh, ttl


async def refresh(session: AsyncSession, refresh_token: str):
    try:
        user_id = tokens.decode_token(refresh_token, "refresh")
    except ValueError as e:
        raise ValueError(str(e))
    hashed = tokens.sha256_hex(refresh_token)
    row = await refresh_repo.get_any(session, hashed)
    if row is None:
        raise ValueError("Refresh inválido")
    if row.revoked_at is not None or row.expires_at <= datetime.now(UTC):
        # reuse-detection: revoga cadeia toda
        await refresh_repo.revoke_all_for_user(session, row.user_id)
        await _audit(session, row.user_id, "auth.refresh_reuse")
        await session.commit()
        raise ValueError("Refresh revogado")
    await refresh_repo.revoke(session, row.id)
    access, ttl = tokens.create_access_token(user_id)
    new_refresh, new_hash, exp = tokens.create_refresh_token(user_id)
    await refresh_repo.store(session, user_id, tokens.sha256_hex(new_refresh), exp)
    await _audit(session, user_id, "auth.refresh")
    await session.commit()
    return access, new_refresh, ttl


async def logout(session: AsyncSession, refresh_token: str) -> int:
    hashed = tokens.sha256_hex(refresh_token)
    row = await refresh_repo.get_any(session, hashed)
    if row is None:
        return 0
    if row.revoked_at is None:
        await refresh_repo.revoke(session, row.id)
    await _audit(session, row.user_id, "auth.logout")
    await session.commit()
    return row.user_id


async def request_recovery(session: AsyncSession, email: str) -> str | None:
    """Sempre 202 na borda. Retorna o token só para log/dev; None se e-mail desconhecido."""
    user = await users_repo.get_by_email(session, email.strip().lower())
    if user is None:
        return None
    token, _ = await recovery_repo.create_for_user(session, user.id)
    await _audit(session, user.id, "auth.recover")
    await session.commit()
    return token


async def reset_password(session: AsyncSession, token: str, new_password: str) -> int:
    row = await recovery_repo.consume(session, token)
    user = await users_repo.get_by_id(session, row.user_id)
    if user is None:
        raise ValueError("Token inválido ou expirado")
    user.password_hash = hash_password(new_password)
    await recovery_repo.mark_used(session, row)
    await refresh_repo.revoke_all_for_user(session, user.id)
    await _audit(session, user.id, "auth.reset")
    await session.commit()
    return user.id


async def change_password(
    session: AsyncSession,
    user_id: int,
    current_password: str,
    new_password: str,
    keep_refresh_hash: str | None = None,
) -> None:
    user = await users_repo.get_by_id(session, user_id)
    if user is None or not verify_password(current_password, user.password_hash):
        raise ValueError("Senha atual incorreta")
    user.password_hash = hash_password(new_password)
    await session.flush()
    # revoga todos os refreshes, exceto a sessão atual (se informada)
    if keep_refresh_hash:
        from sqlalchemy import update

        from app.modules.auth.models import RefreshToken

        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.token_hash != keep_refresh_hash,
            )
            .values(revoked_at=datetime.now(UTC))
        )
    else:
        await refresh_repo.revoke_all_for_user(session, user_id)
    await _audit(session, user_id, "auth.change")
    await session.commit()
