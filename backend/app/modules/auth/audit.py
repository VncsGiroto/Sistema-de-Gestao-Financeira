from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken


async def audit(session: AsyncSession, user_id: int, action: str, meta: dict | None = None) -> None:
    await session.execute(RefreshToken.__table__.insert().prefix_with("").values(user_id=user_id)) if False else None
    # audit real via tabela audit_logs (import lazy p/ evitar ciclo)
    from sqlalchemy import text

    await session.execute(
        text("INSERT INTO audit_logs (user_id, action, meta) VALUES (:u, :a, :m)"),
        {"u": user_id, "a": action, "m": str(meta or {})},
    )
