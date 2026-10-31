import re
import socket
import ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _build_url(raw: str) -> tuple[str, dict]:
    # SQLite (used in tests) — skip all Postgres-specific rewriting
    if raw.startswith("sqlite"):
        return raw, {}

    # Normalise driver prefix
    url = raw
    for prefix in ("postgresql://", "postgres://", "postgresql+psycopg://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            url = "postgresql+asyncpg://" + url[len(prefix):]
            break

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    needs_ssl = bool(qs.pop("sslmode", None)) or "supabase" in (parsed.hostname or "")
    url = urlunparse(parsed._replace(query=urlencode({k: v[0] for k, v in qs.items()})))
    parsed = urlparse(url)

    # If direct Supabase host (db.<ref>.supabase.co) has no IPv4, rewrite to pooler
    host = parsed.hostname or ""
    m = re.match(r"^db\.([a-z0-9]+)\.supabase\.co$", host)
    if m:
        try:
            socket.getaddrinfo(host, 5432, socket.AF_INET)
        except socket.gaierror:
            # No IPv4 — switch to Supabase connection pooler
            ref = m.group(1)
            pooler_regions = [
                "aws-0-ap-south-1", "aws-0-us-east-1", "aws-0-us-west-1",
                "aws-0-eu-central-1", "aws-0-ap-southeast-1",
            ]
            pooler_host = next(
                (f"{r}.pooler.supabase.com" for r in pooler_regions
                 if _resolves_ipv4(f"{r}.pooler.supabase.com")),
                f"{pooler_regions[0]}.pooler.supabase.com",
            )
            # Pooler needs username as postgres.<ref>
            new_user = f"postgres.{ref}" if not (parsed.username or "").endswith(f".{ref}") else parsed.username
            url = urlunparse(parsed._replace(
                netloc=f"{new_user}:{parsed.password}@{pooler_host}:6543",
            ))
            needs_ssl = True

    return url, {"ssl": _ssl_ctx()} if needs_ssl else {}


def _resolves_ipv4(host: str) -> bool:
    try:
        socket.getaddrinfo(host, None, socket.AF_INET)
        return True
    except socket.gaierror:
        return False


_url, _connect_args = _build_url(settings.database_url)

engine = create_async_engine(_url, echo=False, pool_pre_ping=True, connect_args=_connect_args)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
