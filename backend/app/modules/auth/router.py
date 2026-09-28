from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.errors import unauthorized, unavailable
from app.core.redis_client import get_redis
from app.modules.auth import service, tokens
from app.modules.auth.deps import DENY_PREFIX, get_current_user, rate_limit
from app.modules.auth.schemas import (
    ChangeIn,
    LoginIn,
    LogoutIn,
    RecoverIn,
    RefreshIn,
    RegisterIn,
    ResetIn,
    TokenPair,
    UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "fw_refresh"


def _set_refresh_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_ttl,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/auth",
    )


def _clear_refresh_cookie(resp: Response) -> None:
    resp.delete_cookie(REFRESH_COOKIE, path="/api/auth")


async def _deny_access_token(auth_header: str) -> None:
    if not auth_header.lower().startswith("bearer "):
        return
    try:
        jti = tokens.decode_claims(auth_header.split(" ", 1)[1], "access")["jti"]
    except ValueError:
        return
    try:
        await get_redis().setex(f"{DENY_PREFIX}{jti}", settings.access_ttl, "1")
    except Exception:
        if settings.is_prod:
            raise unavailable("Sessão não revogável")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)):
    user = await service.register(session, body.name, body.email, str(body.password))
    return UserOut(id=user.id, name=user.name, email=user.email)


@router.post("/login", response_model=TokenPair)
async def login(body: LoginIn, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    await rate_limit(request, "login", settings.login_rate_limit)
    try:
        _, access, refresh, ttl = await service.login(session, str(body.email), body.password)
    except ValueError as e:
        raise unauthorized(str(e))
    _set_refresh_cookie(response, refresh)
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=ttl)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshIn, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    await rate_limit(request, "refresh", 30)
    token = body.refresh_token or request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise unauthorized("Refresh ausente")
    try:
        access, new_refresh, ttl = await service.refresh(session, token)
    except ValueError as e:
        raise unauthorized(str(e))
    _set_refresh_cookie(response, new_refresh)
    return TokenPair(access_token=access, refresh_token=new_refresh, expires_in=ttl)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    await _deny_access_token(request.headers.get("authorization", ""))
    token = body.refresh_token or request.cookies.get(REFRESH_COOKIE)
    if token:
        await service.logout(session, token)
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return UserOut(id=user.id, name=user.name, email=user.email)


@router.post("/recover", status_code=status.HTTP_202_ACCEPTED)
async def recover(body: RecoverIn, request: Request, session: AsyncSession = Depends(get_session)):
    await rate_limit(request, "recover", 10)
    # anti-enumeração: mesma resposta exista ou não o e-mail
    await service.request_recovery(session, str(body.email))
    return {"message": "Se o e-mail existir, enviamos as instruções."}


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset(body: ResetIn, session: AsyncSession = Depends(get_session)):
    try:
        await service.reset_password(session, body.token, body.new_password)
    except ValueError as e:
        raise unauthorized(str(e))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/change", status_code=status.HTTP_204_NO_CONTENT)
async def change(
    body: ChangeIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    # Revoga todos os refreshes e derruba o access atual (front faz novo login).
    try:
        await service.change_password(session, user.id, body.current_password, body.new_password)
    except ValueError as e:
        raise unauthorized(str(e))
    await _deny_access_token(request.headers.get("authorization", ""))
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
