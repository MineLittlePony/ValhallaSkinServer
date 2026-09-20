from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

engine = create_async_engine(
    settings.get_database_url(),
    pool_size=20,
)
SessionLocal = async_sessionmaker[AsyncSession](engine)
