"""
Routes per il chatbot API
Contiene tutti gli endpoint FastAPI
"""
import time
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import func

from app.config import Settings, get_settings
from app.models.database_models import SessionModel
from app.services.unified_agent import unified_agent
from app.models.api_models import ChatMessage, ChatResponse, HealthCheck
from app.database import get_db
import os

# Crea il router
router = APIRouter()


@router.get("/")
async def root():
    """Endpoint root con informazioni base"""
    settings = get_settings()
    return {
        "message": "Chatbot API",
        "version": settings.app_version,
        "status": "running",
        "docs": "Visita /docs per la documentazione API",
        "flow_visualization": "Visita /flow per la visualizzazione del flusso end-to-end"
    }


@router.get("/flow", response_class=HTMLResponse)
async def flow_visualization():
    """Endpoint che espone la visualizzazione del flusso end-to-end con Jinja2 e Mermaid"""
    try:
        # Ottieni il percorso del template
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        
        # Verifica che la directory templates esista
        if not os.path.exists(templates_dir):
            raise HTTPException(status_code=500, detail="Template directory not found")
        
        # Leggi il file HTML direttamente
        template_path = os.path.join(templates_dir, "flow_visualization.html")
        
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="Flow visualization template not found")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Inizializza Jinja2
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.from_string(html_content)
        
        # Prepara i dati del template
        settings = get_settings()
        
        # Conta sessioni attive
        async for db in get_db():
            result = await db.execute(
                func.count(SessionModel.id)
            )
            active_sessions = result.scalar()
        
        # Renderizza il template
        rendered_html = template.render(
            app_name=settings.app_name,
            app_version=settings.app_version,
            active_sessions=active_sessions,
            debug=settings.debug
        )
        
        return rendered_html
    
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering del flow visualization: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Errore nel caricamento della visualizzazione del flusso: {str(e)}"
        )


@router.get("/preview", response_class=HTMLResponse)
async def preview():
    """Endpoint per testare la rotta /chat con un'interfaccia web"""
    try:
        # Ottieni il percorso del template
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        
        # Verifica che la directory templates esista
        if not os.path.exists(templates_dir):
            raise HTTPException(status_code=500, detail="Template directory not found")
        
        # Leggi il file HTML direttamente
        template_path = os.path.join(templates_dir, "chat.html")
        
        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="Chat test template not found")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return html_content
    
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel caricamento del template di test chat: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Errore nel caricamento del template di test: {str(e)}"
        )


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint per Cloud Run"""
    settings = get_settings()
    return HealthCheck(
        status="healthy",
        version=settings.app_version,
        environment="development" if settings.debug else "production"
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """
    Endpoint per la chat con agente unificato che gestisce conversazione e lifecycle
    """
    try:
        from app.main import logger

        logger.info(f"Messaggio ricevuto da sessione {chat_message.session_id}: {chat_message.message}")

        # Usa l'agente unificato
        lifecycle_response = await unified_agent.chat(
            session_id=chat_message.session_id,
            user_message=chat_message.message
        )

        # Estrai il testo per il logging
        log_text = lifecycle_response.messages

        logger.info(f"Risposta agente unificato per sessione {chat_message.session_id}: {log_text[:100]}...")

        return ChatResponse(
            messages=lifecycle_response.messages,
            session_id=chat_message.session_id,
            current_lifecycle=lifecycle_response.current_lifecycle.value,
            lifecycle_changed=lifecycle_response.lifecycle_changed,
            previous_lifecycle=lifecycle_response.previous_lifecycle.value if lifecycle_response.previous_lifecycle else None,
            next_actions=lifecycle_response.next_actions,
            ai_reasoning=lifecycle_response.ai_reasoning,
            confidence=lifecycle_response.confidence,
            debug_logs=lifecycle_response.debug_logs,
            full_logs=lifecycle_response.full_logs,
            timestamp=str(int(time.time()))
        )

    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nell'endpoint chat per sessione {chat_message.session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Errore interno del server: {str(e)}")


@router.get("/status")
async def status():
    """Endpoint per lo status dettagliato dell'applicazione"""
    settings = get_settings()

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


@router.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Endpoint per ottenere informazioni sulla sessione e lifecycle corrente"""
    try:
        session_info = await unified_agent.get_session_info(session_id)

        if not session_info:
            raise HTTPException(status_code=404, detail="Sessione non trovata")

        return session_info

    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel recupero informazioni sessione {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Errore interno del server: {str(e)}")


@router.get("/unified/health")
async def unified_agent_health_check():
    """Endpoint per verificare lo stato dell'agente unificato"""
    try:
        is_available = await unified_agent.is_available()

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
        from app.main import logger
        logger.error(f"Errore nel health check dell'agente unificato: {str(e)}")
        return {
            "status": "error",
            "message": f"Errore nel controllo: {str(e)}"
        }