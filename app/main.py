"""
Applicazione FastAPI principale per il Chatbot
"""

import os
import time
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from .config import Settings, settings
from app.models.lifecycle import LifecycleResponse
from .services.unified_agent import unified_agent
from .database import engine, Base


# Modelli Pydantic
class ChatMessage(BaseModel):
    """Modello per i messaggi del chat"""
    message: str
    user_id: str = "anonymous"
    session_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Modello per le risposte del chat"""
    response: str
    session_id: str
    current_lifecycle: str
    lifecycle_changed: bool = False
    previous_lifecycle: Optional[str] = None
    next_actions: List[str] = []
    ai_reasoning: Optional[str] = None
    timestamp: str


class HealthCheck(BaseModel):
    """Modello per l'health check"""
    status: str
    version: str
    environment: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestisce il ciclo di vita dell'applicazione"""
    # Startup
    logger.info("🚀 Avvio dell'applicazione chatbot")
    logger.info(f"Versione: {settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Crea le tabelle del database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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


@app.get("/")
async def root():
    """Endpoint root con informazioni base"""
    return {
        "message": "Chatbot API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint per Cloud Run"""
    return HealthCheck(
        status="healthy",
        version=settings.app_version,
        environment="development" if settings.debug else "production"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """
    Endpoint per la chat con agente unificato che gestisce conversazione e lifecycle
    """
    try:
        logger.info(f"Messaggio ricevuto da sessione {chat_message.session_id}: {chat_message.message}")
        
        # Usa l'agente unificato
        lifecycle_response = await unified_agent.chat(
            session_id=chat_message.session_id,
            user_message=chat_message.message
        )
        
        logger.info(f"Risposta agente unificato per sessione {chat_message.session_id}: {lifecycle_response.message[:100]}...")
        
        return ChatResponse(
            response=lifecycle_response.message,
            session_id=chat_message.session_id,
            current_lifecycle=lifecycle_response.current_lifecycle.value,
            lifecycle_changed=lifecycle_response.lifecycle_changed,
            previous_lifecycle=lifecycle_response.previous_lifecycle.value if lifecycle_response.previous_lifecycle else None,
            next_actions=lifecycle_response.next_actions,
            ai_reasoning=lifecycle_response.ai_reasoning,
            timestamp=str(int(time.time()))
        )
        
    except Exception as e:
        logger.error(f"Errore nell'endpoint chat per sessione {chat_message.session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Errore interno del server: {str(e)}")


@app.get("/status")
async def status():
    """Endpoint per lo status dettagliato dell'applicazione"""
    from sqlalchemy import func
    from app.models.database_models import SessionModel
    
    async for db in get_db():
        result = await db.execute(
            func.count(SessionModel.id)
        )
        active_sessions = result.scalar()
    
    unified_agent_available = await unified_agent.is_available()
    
    return {
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "debug": settings.debug
        },
        "services": {
            "unified_agent": {
                "status": "healthy" if unified_agent_available else "unhealthy",
                "ai_client_available": unified_agent_available,
                "active_sessions": active_sessions
            }
        }
    }


@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Endpoint per ottenere informazioni sulla sessione e lifecycle corrente"""
    try:
        session_info = unified_agent.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(status_code=404, detail="Sessione non trovata")
        
        return session_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore nel recupero informazioni sessione {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Errore interno del server: {str(e)}")


@app.get("/unified/health")
async def unified_agent_health_check():
    """Endpoint per verificare lo stato dell'agente unificato"""
    try:
        is_available = await unified_agent.is_available()
        
        from sqlalchemy import func
        from app.models.database_models import SessionModel
        
        async for db in get_db():
            result = await db.execute(
                func.count(SessionModel.id)
            )
            active_sessions = result.scalar()
        
        return {
            "status": "healthy" if is_available else "unhealthy",
            "service": "unified_agent",
            "timestamp": datetime.now().isoformat(),
            "details": {
                "ai_client_available": is_available,
                "active_sessions": active_sessions
            }
        }
    except Exception as e:
        logger.error(f"Errore nel health check dell'agente unificato: {str(e)}")
        return {
            "status": "error",
            "message": f"Errore nel controllo: {str(e)}"
        }


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