import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# importa models para autogenerate/ensure metadata
import app.modules.auth.audit_models  # noqa: F401
import app.modules.auth.models  # noqa: F401
import app.modules.auth.recovery_models  # noqa: F401
import app.modules.finance.models  # noqa: F401
import app.modules.imports.models  # noqa: F401
import app.modules.investments.models  # noqa: F401
import app.modules.ledger.models  # noqa: F401
import app.modules.market.models  # noqa: F401
import app.modules.payables.models  # noqa: F401
import app.modules.users.models  # noqa: F401
from alembic import context
from app.core.config import settings
from app.core.db import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
