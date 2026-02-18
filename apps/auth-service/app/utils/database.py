from __future__ import annotations

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# NOTE: this service uses SQLAlchemy async engine + asyncpg driver
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://pixtral_user:pixtral_pass@localhost:5432/auth_db",
)

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
