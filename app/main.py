"""
Applicazione FastAPI principale per il Chatbot
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from .config import Settings, settings


# Modelli Pydantic
class ChatMessage(BaseModel):
    """Modello per i messaggi del chat"""
    message: str
    user_id: str = "anonymous"


class ChatResponse(BaseModel):
    """Modello per le risposte del chat"""
    response: str
    user_id: str
    timestamp: str


class HealthCheck(BaseModel):
    """Modello per l'health check"""
    status: str
    version: str
    environment: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestione del ciclo di vita dell'applicazione"""
    # Startup
    logger.info(f"Avvio {settings.app_name} v{settings.app_version}")
    logger.info(f"Ambiente: {'development' if settings.debug else 'production'}")
    
    yield
    
    # Shutdown
    logger.info("Spegnimento dell'applicazione")


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
def get_settings():
    return settings


@app.get("/", response_model=Dict[str, str])
async def root():
    """Endpoint root"""
    return {
        "message": f"Benvenuto in {settings.app_name}!",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Documentazione non disponibile in produzione"
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
async def chat_endpoint(
    message: ChatMessage,
    config: Settings = Depends(get_settings)
):
    """
    Endpoint principale per il chat
    
    Questo è un esempio base - qui puoi integrare il tuo modello AI
    """
    try:
        # Esempio di logica del chatbot (sostituisci con il tuo modello AI)
        user_message = message.message.lower()
        
        if "ciao" in user_message or "hello" in user_message:
            bot_response = f"Ciao! Come posso aiutarti oggi?"
        elif "come stai" in user_message:
            bot_response = "Sto bene, grazie! Sono qui per aiutarti."
        elif "aiuto" in user_message or "help" in user_message:
            bot_response = "Sono un chatbot di esempio. Puoi farmi domande e cercherò di rispondere!"
        else:
            bot_response = f"Hai detto: '{message.message}'. Questa è una risposta di esempio!"
        
        # Log del messaggio (utile per debugging)
        logger.info(f"Messaggio da {message.user_id}: {message.message}")
        
        from datetime import datetime
        return ChatResponse(
            response=bot_response,
            user_id=message.user_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Errore nel processare il messaggio: {str(e)}")
        raise HTTPException(status_code=500, detail="Errore interno del server")


@app.get("/status")
async def status():
    """Endpoint di stato per monitoraggio"""
    return {
        "status": "running",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
        "port": settings.port
    }


# Handler per errori globali
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handler globale per le eccezioni"""
    logger.error(f"Errore non gestito: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Errore interno del server"}
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