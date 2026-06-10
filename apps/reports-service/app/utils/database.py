from __future__ import annotations

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

# IMPORTANT:
# - Cette URL doit être ASYNC (postgresql+asyncpg) pour fonctionner avec AsyncSession.
# - Si tu mets une URL sync (postgresql+psycopg2), ce module ne marchera pas.
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://pixtral_user:pixtral_pass@localhost:5432/reports_db",
)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "3")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "5")),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
