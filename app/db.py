from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Normalise driver prefix (Supabase hands out postgresql://)
_url = settings.database_url
for _prefix in ("postgresql://", "postgres://", "postgresql+psycopg://", "postgresql+psycopg2://"):
    if _url.startswith(_prefix):
        _url = "postgresql+asyncpg://" + _url[len(_prefix):]
        break

# asyncpg doesn't read sslmode from the URL — strip it and pass ssl=True instead
_parsed = urlparse(_url)
_qs = parse_qs(_parsed.query)
_needs_ssl = bool(_qs.pop("sslmode", None)) or "supabase.co" in (_parsed.hostname or "")
_clean_qs = urlencode({k: v[0] for k, v in _qs.items()})
_url = urlunparse(_parsed._replace(query=_clean_qs))

_connect_args = {"ssl": True} if _needs_ssl else {}

engine = create_async_engine(_url, echo=False, pool_pre_ping=True, connect_args=_connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
