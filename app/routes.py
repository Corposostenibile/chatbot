"""
Routes per il chatbot API
Contiene tutti gli endpoint FastAPI
"""
import os
import time
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from app.config import get_settings
from app.models.database_models import SessionModel, MessageModel, SystemPromptModel
from app.services.system_prompt_service import SystemPromptService
from app.models.api_models import ChatMessage, ChatResponse, HealthCheck, SystemPromptCreate, SystemPromptUpdate
from app.database import get_db
import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.services.unified_agent import unified_agent, AIError, ParsingError, ChatbotError

# Crea il router
router = APIRouter()

# Configurazione template Jinja2
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Dashboard di monitoraggio principale"""
    try:
        # Prepara i dati del template
        settings = get_settings()

        # Renderizza il template
        return templates.TemplateResponse(
            "monitoring_dashboard.html",
            {
                "request": request,
                "app_version": settings.app_version
            }
        )

    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering della dashboard di monitoraggio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel caricamento della dashboard: {str(e)}"
        )


@router.get("/flow", response_class=HTMLResponse)
async def flow_visualization(request: Request):
    """Endpoint che espone la visualizzazione del flusso end-to-end con Jinja2 e Mermaid"""
    try:
        # Prepara i dati del template
        settings = get_settings()

        # Conta sessioni attive
        async for db in get_db():
            result = await db.execute(
                func.count(SessionModel.id)
            )
            active_sessions = result.scalar()

        # Renderizza il template
        return templates.TemplateResponse(
            "flow_visualization.html",
            {
                "request": request,
                "app_name": settings.app_name,
                "app_version": settings.app_version,
                "active_sessions": active_sessions,
                "debug": settings.debug
            }
        )

    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering del flow visualization: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel caricamento della visualizzazione del flusso: {str(e)}"
        )


@router.get("/preview", response_class=HTMLResponse)
async def preview(request: Request):
    """Endpoint per testare la rotta /chat con un'interfaccia web"""
    try:
        return templates.TemplateResponse("chat.html", {"request": request})

    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel caricamento del template di test chat: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Errore nel caricamento del template di test: {str(e)}"
        )


@router.get("/sessions", response_class=HTMLResponse)
async def sessions_dashboard(request: Request):
    """Dashboard per visualizzare tutte le sessioni salvate nel database"""
    try:
        async for db in get_db():
            # Query ORM per ottenere sessioni con conteggio messaggi
            stmt = select(
                SessionModel.id,
                SessionModel.session_id,
                SessionModel.current_lifecycle,
                SessionModel.user_info,
                SessionModel.is_conversation_finished,
                SessionModel.created_at,
                SessionModel.updated_at,
                func.count(MessageModel.id).label('message_count')
            ).outerjoin(
                MessageModel, SessionModel.id == MessageModel.session_id
            ).group_by(
                SessionModel.id,
                SessionModel.session_id,
                SessionModel.current_lifecycle,
                SessionModel.user_info,
                SessionModel.is_conversation_finished,
                SessionModel.created_at,
                SessionModel.updated_at
            ).order_by(SessionModel.updated_at.desc())

            result = await db.execute(stmt)
            sessions_data = result.fetchall()

        # Converti i risultati in dizionari
        sessions = []
        for row in sessions_data:
            sessions.append({
                'id': row.id,
                'session_id': row.session_id,
                'current_lifecycle': row.current_lifecycle,
                'user_info': row.user_info,
                'is_conversation_finished': row.is_conversation_finished,
                'created_at': row.created_at,
                'updated_at': row.updated_at,
                'message_count': row.message_count
            })

        # Prepara i dati del template
        settings = get_settings()

        return templates.TemplateResponse(
            "sessions.html",
            {
                "request": request,
                "sessions": sessions,
                "app_version": settings.app_version,
                "total_sessions": len(sessions)
            }
        )

    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering della dashboard sessioni: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel caricamento della dashboard sessioni: {str(e)}"
        )


@router.get("/session/{session_id}/messages", response_class=HTMLResponse)
async def session_conversation(session_id: str, request: Request):
    """Visualizza la conversazione completa di una sessione specifica"""
    try:
        async for db in get_db():
            # Query ORM per ottenere la sessione
            session_stmt = select(SessionModel).where(SessionModel.session_id == session_id)
            session_result = await db.execute(session_stmt)
            session_data = session_result.scalar_one_or_none()

            if not session_data:
                raise HTTPException(status_code=404, detail="Sessione non trovata")

            # Query ORM per ottenere tutti i messaggi della sessione
            messages_stmt = select(MessageModel).where(
                MessageModel.session_id == session_data.id
            ).order_by(MessageModel.timestamp.asc())

            messages_result = await db.execute(messages_stmt)
            messages_data = messages_result.scalars().all()

        # Converti i messaggi in dizionari
        messages = []
        for msg in messages_data:
            messages.append({
                'role': msg.role,
                'message': msg.message,
                'timestamp': msg.timestamp
            })

        # Converti i dati della sessione
        session_info = {
            'id': session_data.id,
            'session_id': session_data.session_id,
            'current_lifecycle': session_data.current_lifecycle,
            'user_info': session_data.user_info,
            'is_conversation_finished': session_data.is_conversation_finished,
            'created_at': session_data.created_at,
            'updated_at': session_data.updated_at,
            'message_count': len(messages)
        }

        # Prepara i dati del template
        settings = get_settings()

        return templates.TemplateResponse(
            "conversation.html",
            {
                "request": request,
                "session": session_info,
                "messages": messages,
                "app_version": settings.app_version
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering della conversazione sessione {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel caricamento della conversazione: {str(e)}"
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

        # Verifica se la conversazione è finita
        async for db in get_db():
            from sqlalchemy import select
            result = await db.execute(
                select(SessionModel).where(SessionModel.session_id == chat_message.session_id)
            )
            session = result.scalar_one_or_none()

            if session and session.is_conversation_finished:
                logger.warning(f"Tentativo di invio messaggio a conversazione finita per sessione {chat_message.session_id}")
                raise HTTPException(
                    status_code=403,
                    detail="Conversazione terminata. Non è più possibile inviare messaggi."
                )

        # Usa l'agente unificato
        lifecycle_response = await unified_agent.chat(
            session_id=chat_message.session_id,
            user_message=chat_message.message
        )

        # Estrai il testo per il logging
        if isinstance(lifecycle_response.messages, str):
            log_text = lifecycle_response.messages
        else:
            log_text = " ".join([msg.get("text", "") for msg in lifecycle_response.messages])

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

    except AIError as e:
        from app.main import logger
        logger.error(f"Errore AI nell'endpoint chat per sessione {chat_message.session_id}: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except ParsingError as e:
        from app.main import logger
        logger.error(f"Errore parsing nell'endpoint chat per sessione {chat_message.session_id}: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except ChatbotError as e:
        from app.main import logger
        logger.error(f"Errore chatbot nell'endpoint chat per sessione {chat_message.session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore generico nell'endpoint chat per sessione {chat_message.session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/system-prompts", response_class=HTMLResponse)
async def system_prompts_dashboard(request: Request):
    """Dashboard per gestire i system prompts"""
    try:
        prompts = await SystemPromptService.get_all_prompts()
        
        # Converti in dizionari per il template
        prompts_data = []
        for prompt in prompts:
            prompts_data.append({
                'id': prompt.id,
                'name': prompt.name,
                'content': prompt.content[:200] + "..." if len(prompt.content) > 200 else prompt.content,
                'is_active': prompt.is_active,
                'version': prompt.version,
                'description': prompt.description,
                'created_at': prompt.created_at,
                'updated_at': prompt.updated_at
            })
        
        settings = get_settings()
        
        return templates.TemplateResponse(
            "system_prompts.html",
            {
                "request": request,
                "prompts": prompts_data,
                "app_version": settings.app_version
            }
        )
        
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering della dashboard system prompts: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel caricamento della dashboard: {str(e)}"
        )


# API endpoints per gestire i system prompts
@router.get("/api/system-prompts")
async def get_system_prompts():
    """Ottiene tutti i system prompts"""
    try:
        prompts = await SystemPromptService.get_all_prompts()
        return [
            {
                'id': p.id,
                'name': p.name,
                'content': p.content,
                'is_active': p.is_active,
                'version': p.version,
                'description': p.description,
                'created_at': p.created_at.isoformat(),
                'updated_at': p.updated_at.isoformat()
            }
            for p in prompts
        ]
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel recupero dei system prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/system-prompts/{prompt_id}")
async def get_system_prompt(prompt_id: int):
    """Ottiene un system prompt specifico"""
    try:
        async for db in get_db():
            result = await db.execute(
                select(SystemPromptModel).where(SystemPromptModel.id == prompt_id)
            )
            prompt = result.scalar_one_or_none()
            
            if not prompt:
                raise HTTPException(status_code=404, detail="Prompt non trovato")
            
            return {
                'id': prompt.id,
                'name': prompt.name,
                'content': prompt.content,
                'is_active': prompt.is_active,
                'version': prompt.version,
                'description': prompt.description,
                'created_at': prompt.created_at.isoformat(),
                'updated_at': prompt.updated_at.isoformat()
            }
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel recupero del system prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    """Ottiene il system prompt attivo"""
    try:
        content = await SystemPromptService.get_active_prompt()
        if not content:
            raise HTTPException(status_code=404, detail="Nessun prompt attivo trovato")
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel recupero del prompt attivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/system-prompts")
async def create_system_prompt(prompt: SystemPromptCreate):
    """Crea un nuovo system prompt"""
    try:
        created_prompt = await SystemPromptService.create_prompt(
            name=prompt.name,
            content=prompt.content,
            version=prompt.version,
            description=prompt.description
        )
        if not created_prompt:
            raise HTTPException(status_code=400, detail="Errore nella creazione del prompt")
        
        return {
            'id': created_prompt.id,
            'name': created_prompt.name,
            'content': created_prompt.content,
            'is_active': created_prompt.is_active,
            'version': created_prompt.version,
            'description': created_prompt.description,
            'created_at': created_prompt.created_at.isoformat(),
            'updated_at': created_prompt.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nella creazione del system prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/system-prompts/{prompt_id}")
async def update_system_prompt(prompt_id: int, prompt: SystemPromptUpdate):
    """Aggiorna un system prompt esistente"""
    try:
        success = await SystemPromptService.update_prompt(
            prompt_id=prompt_id,
            name=prompt.name,
            content=prompt.content,
            version=prompt.version,
            description=prompt.description
        )
        if not success:
            raise HTTPException(status_code=404, detail="Prompt non trovato")
        
        return {"message": "Prompt aggiornato con successo"}
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nell'aggiornamento del system prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/system-prompts/{prompt_id}/activate")
async def activate_system_prompt(prompt_id: int):
    """Attiva un system prompt"""
    try:
        success = await SystemPromptService.set_active_prompt(prompt_id)
        if not success:
            raise HTTPException(status_code=404, detail="Prompt non trovato")
        
        return {"message": "Prompt attivato con successo"}
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nell'attivazione del system prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/system-prompts/{prompt_id}")
async def delete_system_prompt(prompt_id: int):
    """Elimina un system prompt"""
    try:
        success = await SystemPromptService.delete_prompt(prompt_id)
        if not success:
            raise HTTPException(status_code=404, detail="Prompt non trovato")
        
        return {"message": "Prompt eliminato con successo"}
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nell'eliminazione del system prompt {prompt_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    """Endpoint API per eseguire comandi del server script"""
    try:
        from app.main import logger

        # Mappa dei comandi disponibili
        available_commands = {
            "server-status": ["./server", "server-status"],
            "monitor-health": ["./server", "monitor-health"],
            "ssl-check": ["./server", "ssl-check"],
            "dependencies-check": ["./server", "dependencies-check"],
            "dependencies-lock": ["./server", "dependencies-lock"]
        }

        if command not in available_commands:
            raise HTTPException(status_code=400, detail=f"Comando non disponibile: {command}")

        logger.info(f"Eseguendo comando API: {command}")

        # Esegui il comando in un thread separato per non bloccare l'event loop
        def run_command():
            try:
                # Usa la directory del container dove è copiato il file server
                container_dir = "/app"
                result = subprocess.run(
                    available_commands[command],
                    capture_output=True,
                    text=True,
                    cwd=container_dir,
                    timeout=30  # Timeout più lungo per comandi complessi
                )
                return {
                    "success": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e)
                }

        # Esegui in thread pool
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, run_command)

        if not result["success"]:
            logger.error(f"Comando {command} fallito: {result.get('stderr', result.get('error', 'Errore sconosciuto'))}")
            raise HTTPException(
                status_code=500,
                detail=f"Comando fallito: {result.get('stderr', result.get('error', 'Errore sconosciuto'))}"
            )

        logger.info(f"Comando {command} eseguito con successo")
        return {
            "command": command,
            "success": True,
            "output": result["stdout"],
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nell'esecuzione del comando API {command}: {str(e)}")
