from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Supabase hands out postgresql:// — normalise to asyncpg driver
_url = settings.database_url
for _prefix in ("postgresql://", "postgres://", "postgresql+psycopg://", "postgresql+psycopg2://"):
    if _url.startswith(_prefix):
        _url = "postgresql+asyncpg://" + _url[len(_prefix):]
        break

engine = create_async_engine(_url, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
