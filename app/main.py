"""
Applicazione FastAPI principale per il Chatbot
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from .config import Settings, settings
from .services.gemini_service import gemini_service


# Modelli Pydantic
class ChatMessage(BaseModel):
    """Modello per i messaggi del chat"""
    message: str
    user_id: str = "anonymous"
    context: Optional[Dict[str, Any]] = None


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
    Endpoint principale per il chat con integrazione Gemini 2.5 Pro
    """
    try:
        # Verifica se il servizio Gemini è disponibile
        if not gemini_service.is_available():
            logger.warning("Servizio Gemini non disponibile, usando risposta di fallback")
            
            # Fallback alla logica precedente se Gemini non è disponibile
            user_message = message.message.lower()
            
            if "ciao" in user_message or "hello" in user_message:
                bot_response = f"Ciao! Come posso aiutarti oggi? (Nota: Gemini non è configurato)"
            elif "come stai" in user_message:
                bot_response = "Sto bene, grazie! Sono qui per aiutarti. (Nota: Gemini non è configurato)"
            elif "aiuto" in user_message or "help" in user_message:
                bot_response = "Sono un chatbot. Configura Gemini API key per funzionalità avanzate!"
            else:
                bot_response = f"Hai detto: '{message.message}'. Configura GEMINI_API_KEY per risposte AI!"
        else:
            # Usa il servizio Gemini per generare la risposta
            logger.info(f"Invio messaggio a Gemini da utente {message.user_id}")
            
            gemini_response = await gemini_service.chat(
                message=message.message,
                context=message.context
            )
            
            if gemini_response["success"]:
                bot_response = gemini_response["response"]
                logger.info("Risposta ricevuta da Gemini con successo")
            else:
                logger.error(f"Errore da Gemini: {gemini_response['error']}")
                bot_response = f"Mi dispiace, ho riscontrato un errore: {gemini_response['error']}"
        
        # Log del messaggio (utile per debugging)
        logger.info(f"Messaggio da {message.user_id}: {message.message[:100]}...")
        
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


@app.get("/gemini/health")
async def gemini_health_check():
    """Endpoint per verificare lo stato del servizio Gemini"""
    try:
        health_status = await gemini_service.health_check()
        return health_status
    except Exception as e:
        logger.error(f"Errore nel health check di Gemini: {str(e)}")
        return {
            "status": "error",
            "message": f"Errore nel controllo: {str(e)}"
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