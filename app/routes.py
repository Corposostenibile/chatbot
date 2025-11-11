"""
Routes per il chatbot API
Contiene tutti gli endpoint FastAPI
"""
import os
import time
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import func

from app.config import Settings, get_settings
from app.models.database_models import SessionModel, MessageModel
from app.services.unified_agent import unified_agent, AIError, ParsingError, ChatbotError
from app.models.api_models import ChatMessage, ChatResponse, HealthCheck
from app.database import get_db
import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Crea il router
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def root():
    """Dashboard di monitoraggio principale"""
    try:
        # Ottieni il percorso del template
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")

        # Verifica che la directory templates esista
        if not os.path.exists(templates_dir):
            raise HTTPException(status_code=500, detail="Template directory not found")

        # Leggi il template di monitoraggio
        template_path = os.path.join(templates_dir, "monitoring_dashboard.html")

        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="Monitoring dashboard template not found")

        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Inizializza Jinja2
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.from_string(html_content)

        # Prepara i dati del template
        settings = get_settings()

        # Renderizza il template
        rendered_html = template.render(
            app_version=settings.app_version
        )

        return rendered_html

    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering della dashboard di monitoraggio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel caricamento della dashboard: {str(e)}"
        )


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


@router.get("/sessions", response_class=HTMLResponse)
async def sessions_dashboard():
    """Dashboard per visualizzare tutte le sessioni salvate nel database"""
    try:
        # Ottieni il percorso del template
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")

        # Verifica che la directory templates esista
        if not os.path.exists(templates_dir):
            raise HTTPException(status_code=500, detail="Template directory not found")

        # Leggi il template delle sessioni
        template_path = os.path.join(templates_dir, "sessions.html")

        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="Sessions template not found")

        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Inizializza Jinja2
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.from_string(html_content)

        # Ottieni tutte le sessioni con i relativi messaggi
        async for db in get_db():
            # Query per ottenere sessioni con conteggio messaggi
            result = await db.execute(
                """
                SELECT
                    s.id,
                    s.session_id,
                    s.current_lifecycle,
                    s.user_info,
                    s.created_at,
                    s.updated_at,
                    COUNT(m.id) as message_count
                FROM sessions s
                LEFT JOIN messages m ON s.id = m.session_id
                GROUP BY s.id, s.session_id, s.current_lifecycle, s.user_info, s.created_at, s.updated_at
                ORDER BY s.updated_at DESC
                """
            )
            sessions_data = result.fetchall()

        # Converti i risultati in dizionari
        sessions = []
        for row in sessions_data:
            sessions.append({
                'id': row[0],
                'session_id': row[1],
                'current_lifecycle': row[2],
                'user_info': row[3],
                'created_at': row[4],
                'updated_at': row[5],
                'message_count': row[6]
            })

        # Prepara i dati del template
        settings = get_settings()

        # Renderizza il template
        rendered_html = template.render(
            sessions=sessions,
            app_version=settings.app_version,
            total_sessions=len(sessions)
        )

        return rendered_html

    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering della dashboard sessioni: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel caricamento della dashboard sessioni: {str(e)}"
        )


@router.get("/session/{session_id}/messages", response_class=HTMLResponse)
async def session_conversation(session_id: str):
    """Visualizza la conversazione completa di una sessione specifica"""
    try:
        # Ottieni il percorso del template
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")

        # Verifica che la directory templates esista
        if not os.path.exists(templates_dir):
            raise HTTPException(status_code=500, detail="Template directory not found")

        # Leggi il template della conversazione
        template_path = os.path.join(templates_dir, "conversation.html")

        if not os.path.exists(template_path):
            raise HTTPException(status_code=404, detail="Conversation template not found")

        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Inizializza Jinja2
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.from_string(html_content)

        # Ottieni la sessione e i suoi messaggi
        async for db in get_db():
            # Ottieni informazioni sulla sessione
            session_result = await db.execute(
                """
                SELECT id, session_id, current_lifecycle, user_info, created_at, updated_at
                FROM sessions
                WHERE session_id = :session_id
                """,
                {"session_id": session_id}
            )
            session_data = session_result.fetchone()

            if not session_data:
                raise HTTPException(status_code=404, detail="Sessione non trovata")

            # Ottieni tutti i messaggi della sessione
            messages_result = await db.execute(
                """
                SELECT role, message, timestamp
                FROM messages
                WHERE session_id = :session_id
                ORDER BY timestamp ASC
                """,
                {"session_id": session_data[0]}  # Usa l'id interno della sessione
            )
            messages_data = messages_result.fetchall()

        # Converti i messaggi in dizionari
        messages = []
        for msg in messages_data:
            messages.append({
                'role': msg[0],
                'message': msg[1],
                'timestamp': msg[2]
            })

        # Converti i dati della sessione
        session_info = {
            'id': session_data[0],
            'session_id': session_data[1],
            'current_lifecycle': session_data[2],
            'user_info': session_data[3],
            'created_at': session_data[4],
            'updated_at': session_data[5],
            'message_count': len(messages)
        }

        # Prepara i dati del template
        settings = get_settings()

        # Renderizza il template
        rendered_html = template.render(
            session=session_info,
            messages=messages,
            app_version=settings.app_version
        )

        return rendered_html

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


@router.get("/api/execute/{command}")
async def execute_command(command: str):
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
