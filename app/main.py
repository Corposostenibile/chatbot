"""
Applicazione FastAPI principale per il Chatbot
"""

import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from .config import Settings, settings
from app.models.lifecycle import LifecycleResponse
from .services.unified_agent import unified_agent
from .database import engine, Base
from .routes import router


async def wait_for_db(max_retries: int = 10, delay: int = 2):
    """Attende che il database sia disponibile con retry"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Tentativo di connessione al database ({attempt + 1}/{max_retries})...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Connessione al database riuscita")
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"⏳ Database non pronto, attesa {delay}s... ({attempt + 1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"❌ Impossibile connettersi al database dopo {max_retries} tentativi: {e}")
                raise
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestisce il ciclo di vita dell'applicazione"""
    # Startup
    logger.info("🚀 Avvio dell'applicazione chatbot")
    logger.info(f"Versione: {settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Crea le tabelle del database con retry
    await wait_for_db()
    logger.info("✅ Tabelle del database create")
    
    # Verifica la disponibilità dei servizi
    if await unified_agent.is_available():
        logger.info("✅ Agente unificato disponibile")
    else:
        logger.warning("⚠️ Agente unificato non disponibile")
    
    yield
    
    # Shutdown
    logger.info("🛑 Spegnimento dell'applicazione")


# Creazione dell'app FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Un chatbot moderno costruito con FastAPI",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Configurazione template Jinja2
templates = Jinja2Templates(directory="app/templates")

# Includi le routes
app.include_router(router)

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency per ottenere le impostazioni
def get_settings() -> Settings:
    """Dependency per ottenere le impostazioni"""
    return settings


# Gestione degli errori globali
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Gestisce le eccezioni HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.now().isoformat()}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Gestisce le eccezioni generali"""
    logger.error(f"Errore non gestito: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Errore interno del server",
            "timestamp": datetime.now().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )