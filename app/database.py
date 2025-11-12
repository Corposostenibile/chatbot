"""
Configurazione del database
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    """Ottiene l'URL del database con il driver corretto per async"""
    url = settings.database_url

    # Se è SQLite, usa aiosqlite come driver
    if url.startswith("sqlite://"):
        # Rimuovi sqlite:// e aggiungi aiosqlite
        path = url.replace("sqlite://", "")
        return f"sqlite+aiosqlite:///{path}"

    return url


engine = create_async_engine(get_database_url(), echo=settings.debug)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()