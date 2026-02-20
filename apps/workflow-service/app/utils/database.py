from __future__ import annotations

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# IMPORTANT:
# - workflow-service utilise des endpoints async => il faut AsyncSession + create_async_engine
# - DATABASE_URL doit être en postgresql+asyncpg://...
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://pixtral_user:pixtral_pass@postgres:5432/workflow_db",
)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db
