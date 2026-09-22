import time

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import too_many, unauthorized
from app.core.redis_client import get_redis
from app.modules.auth import tokens
from app.modules.users import repository as users_repo

_bearer = HTTPBearer(auto_error=False)


async def rate_limit(request: Request, key: str, limit: int, window_s: int = 60) -> None:
    redis = get_redis()
    redis_key = f"rl:{key}:{request.client.host if request.client else 'unknown'}"
    try:
        count = await redis.incr(redis_key)
        if count == 1:
            await redis.expire(redis_key, window_s)
        if count > limit:
            raise too_many()
    except Exception as e:
        if "Too Many" in str(type(e).__name__) or getattr(e, "status_code", None) == 429:
            raise
        # Redis fora? fail-open em dev, fail-closed seria ideal em prod.
        # Mantém fail-open p/ Etapa 1 não travar sem redis.
        return


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
):
    if creds is None or not creds.credentials:
        raise unauthorized("Token ausente")
    try:
        user_id = tokens.decode_token(creds.credentials, "access")
    except ValueError as e:
        raise unauthorized(str(e))
    # deny-list logout
    redis = get_redis()
    try:
        if await redis.get(f"denylist:access:{creds.credentials[-16:]}"):
            raise unauthorized("Sessão encerrada")
    except Exception:
        pass
    user = await users_repo.get_by_id(session, user_id)
    if user is None:
        raise unauthorized("Usuário não encontrado")
    # esconde expiração timing: checagem simples de expiração já feita no decode
    _ = time.time()
    return user
