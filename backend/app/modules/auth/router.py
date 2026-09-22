from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import unauthorized
from app.core.redis_client import get_redis
from app.modules.auth import service
from app.modules.auth.deps import get_current_user, rate_limit
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


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)):
    user = await service.register(session, body.name, body.email, str(body.password))
    return UserOut(id=user.id, name=user.name, email=user.email)


@router.post("/login", response_model=TokenPair)
async def login(body: LoginIn, request: Request, session: AsyncSession = Depends(get_session)):
    await rate_limit(request, "login", 10)
    try:
        _, access, refresh, ttl = await service.login(session, str(body.email), body.password)
    except ValueError as e:
        raise unauthorized(str(e))
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=ttl)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshIn, request: Request, session: AsyncSession = Depends(get_session)):
    await rate_limit(request, "refresh", 30)
    try:
        access, new_refresh, ttl = await service.refresh(session, body.refresh_token)
    except ValueError as e:
        raise unauthorized(str(e))
    return TokenPair(access_token=access, refresh_token=new_refresh, expires_in=ttl)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutIn,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    # deny-list do access atual (se enviado)
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        try:
            redis = get_redis()
            await redis.setex(f"denylist:access:{token[-16:]}", 900, "1")
        except Exception:
            pass
    await service.logout(session, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    # mantém a sessão atual viva: informa o hash do refresh? Não temos — revoga todos
    # exceto se o cliente enviar o refresh atual no corpo? Mantém simples: revoga todos
    # os outros via deny-list do access atual já coberta no logout; aqui revoga todos os
    # refreshes e o front faz novo login. Decisão: revoga tudo (mais seguro).
    try:
        await service.change_password(session, user.id, body.current_password, body.new_password)
    except ValueError as e:
        raise unauthorized(str(e))
    # deny-list do access atual para forçar novo login
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        try:
            redis = get_redis()
            await redis.setex(f"denylist:access:{token[-16:]}", 900, "1")
        except Exception:
            pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)
