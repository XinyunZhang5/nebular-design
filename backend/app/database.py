import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# Enum values added after a database was first created. create_all() only creates
# missing tables — it never alters an existing PostgreSQL enum type — so a database
# built before one of these values existed keeps the old type and rejects the new
# value at insert time. Applying them here keeps old and new databases in sync.
_ENUM_ADDITIONS: list[tuple[str, str]] = [
    ("friendship_status", "rejected"),
]

# Columns added after a database was first created. create_all() creates missing
# tables but never alters an existing one, so without this a database built before
# the column existed keeps the old shape and every query naming it fails.
_COLUMN_ADDITIONS: list[tuple[str, str, str]] = [
    ("projects", "name", "VARCHAR(120)"),
    ("users", "token_version", "INTEGER NOT NULL DEFAULT 0"),
]


async def init_db() -> None:
    from app import models  # noqa: F401 — ensure models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for table, column, ddl_type in _COLUMN_ADDITIONS:
            await conn.execute(
                text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl_type}")
            )

    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block, so use a
    # separate AUTOCOMMIT connection. IF NOT EXISTS makes this a no-op on a fresh
    # database, where create_all() already built the type with every value.
    autocommit_engine = engine.execution_options(isolation_level="AUTOCOMMIT")
    async with autocommit_engine.connect() as conn:
        for type_name, value in _ENUM_ADDITIONS:
            try:
                await conn.execute(
                    text(f"ALTER TYPE {type_name} ADD VALUE IF NOT EXISTS '{value}'")
                )
            except SQLAlchemyError:
                # Never block startup on this — worst case the value is already there.
                logger.warning(
                    "Could not add '%s' to enum %s; continuing.", value, type_name,
                    exc_info=True,
                )


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
