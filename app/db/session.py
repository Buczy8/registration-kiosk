from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import get_database_url

engine = create_async_engine(get_database_url(), pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False, 
    bind=engine,
    class_=AsyncSession
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as db:
        yield db