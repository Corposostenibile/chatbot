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
from app.services.ai_model_service import AIModelService
from app.models.api_models import ChatMessage, ChatResponse, HealthCheck, SystemPromptCreate, SystemPromptUpdate
from app.models.api_models import MessageNoteCreate, MessageNoteResponse
from app.models.api_models import HumanTaskCreate, HumanTaskUpdate
from app.database import get_db
import json as json_lib
import subprocess
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.services.unified_agent import unified_agent, AIError, ParsingError, ChatbotError
from app.models.database_models import HumanTaskModel
from app.models.database_models import MessageNoteModel
from app.models.lifecycle import LifecycleStage

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
            ).order_by(MessageModel.timestamp.asc(), MessageModel.id.asc())

            messages_result = await db.execute(messages_stmt)
            messages_data = messages_result.scalars().all()

            # Also load lifecycle events to show transition markers anchored to messages
            from app.models.database_models import LifecycleEventModel
            events_stmt = select(LifecycleEventModel).where(LifecycleEventModel.session_id == session_data.id).order_by(LifecycleEventModel.created_at.asc())
            events_result = await db.execute(events_stmt)
            events_data = events_result.scalars().all()

        # Converti i messaggi in dizionari
        messages = []
        for msg in messages_data:
            messages.append({
                'id': msg.id,
                'role': msg.role,
                'message': msg.message,
                'timestamp': msg.timestamp
                , 'lifecycle': msg.lifecycle.value if msg.lifecycle else None
            })

        # Merge messages and lifecycle events into a single timeline (entries)
        entries = []
        for msg in messages:
            entries.append({
                'type': 'message',
                'id': msg['id'],
                'role': msg['role'],
                'message': msg['message'],
                'timestamp': msg['timestamp'],
                'lifecycle': msg['lifecycle']
            })

        for ev in events_data:
            entries.append({
                'type': 'lifecycle_event',
                'previous_lifecycle': ev.previous_lifecycle.value if ev.previous_lifecycle else None,
                'new_lifecycle': ev.new_lifecycle.value,
                'timestamp': ev.created_at,
                'message_id': ev.trigger_message_id
            })

        # If there are events anchored to message ids, place them right before the message with that id
        # else just sort by timestamp
        # Create a dict for quick access
        msg_index = {e['id']: i for i, e in enumerate(entries) if e['type'] == 'message'}
        anchored = []
        unanchored = []
        for e in entries:
            if e['type'] == 'lifecycle_event' and e.get('message_id'):
                idx = msg_index.get(e['message_id'])
                if idx is not None:
                    anchored.append((idx, e))
                else:
                    unanchored.append(e)
            else:
                unanchored.append(e)

        # Insert anchored events before the associated message by sorting
        anchored.sort(key=lambda x: x[0])
        # flatten anchored into unanchored list as specified
        for idx, ev in anchored:
            # place this event before the message with id
            # find message in unanchored by id
            for i, ee in enumerate(unanchored):
                if ee.get('type') == 'message' and ee.get('id') == entries[idx]['id']:
                    unanchored.insert(i, ev)
                    break

        # Finally, sort all by timestamp for chronological ordering
        entries = sorted(unanchored, key=lambda x: (x['timestamp'], 0 if x['type'] == 'lifecycle_event' else 1))

        # Converti i dati della sessione
        session_info = {
            'id': session_data.id,
            'session_id': session_data.session_id,
            'current_lifecycle': session_data.current_lifecycle.value if session_data.current_lifecycle else None,
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
                "entries": entries if 'entries' in locals() else messages,
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


@router.get("/api/models")
async def get_available_models():
    """Ottiene la lista dei modelli AI disponibili"""
    try:
        models = await AIModelService.get_all_models()
        return {
            "models": [
                {
                    "name": m.name,
                    "display_name": m.display_name or m.name,
                    "is_active": m.is_active,
                    "description": m.description
                }
                for m in models
            ]
        }
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel recupero dei modelli: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                # Restituisci una risposta che indica che la conversazione è finita senza messaggi
                return ChatResponse(
                    messages=[],  # Lista vuota per indicare che non ci sono messaggi da mostrare
                    session_id=chat_message.session_id,
                    current_lifecycle=session.current_lifecycle.value,
                    lifecycle_changed=False,
                    previous_lifecycle=None,
                    ai_reasoning="Conversazione terminata",
                    confidence=1.0,
                    debug_logs=[],
                    full_logs="",
                    timestamp=str(int(time.time())),
                    is_conversation_finished=True
                )

        # Usa l'agente unificato
        lifecycle_response = await unified_agent.chat(
            session_id=chat_message.session_id,
            user_message=chat_message.message,
            model_name=chat_message.model_name,
            batch_wait_seconds=chat_message.batch_wait_seconds
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
            # next_actions removed - no longer part of API
            ai_reasoning=lifecycle_response.ai_reasoning,
            confidence=lifecycle_response.confidence,
            debug_logs=lifecycle_response.debug_logs,
            full_logs=lifecycle_response.full_logs,
            timestamp=str(int(time.time())),
            is_conversation_finished=lifecycle_response.is_conversation_finished
            ,requires_human=lifecycle_response.requires_human
            ,human_task=lifecycle_response.human_task
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


@router.post("/session/{session_id}/finish")
async def finish_session(session_id: str, set_lifecycle: bool = True):
    """Marca la sessione come finita e opzionalmente setta il lifecycle su LINK_INVIATO

    La front-end può chiamare questa rotta per marcare la sessione come completata
    quando viene mostrata la grafica di fine conversazione.
    """
    try:
        async for db in get_db():
            result = await db.execute(
                select(SessionModel).where(SessionModel.session_id == session_id)
            )
            session = result.scalar_one_or_none()

            if not session:
                raise HTTPException(status_code=404, detail="Sessione non trovata")

            # Imposta la flag di conversazione finita
            session.is_conversation_finished = True
            # Se richiesto, imposta lifecycle su LINK_INVIATO
            if set_lifecycle:
                session.current_lifecycle = LifecycleStage.LINK_INVIATO

            await db.commit()

            return {
                "session_id": session.session_id,
                "is_conversation_finished": session.is_conversation_finished,
                "current_lifecycle": session.current_lifecycle.value,
                "message": "Sessione marcata come finita"
            }
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel marcare la sessione come finita: {e}")
        raise HTTPException(status_code=500, detail=f"Errore interno del server: {str(e)}")


@router.post("/api/tasks")
async def create_human_task(task: HumanTaskCreate):
    """Crea una nuova human task manualmente"""
    try:
        async for db in get_db():
            # Cerca la sessione associata se presente
            session_id = None
            if task.session_id:
                result = await db.execute(select(SessionModel).where(SessionModel.session_id == task.session_id))
                session = result.scalar_one_or_none()
                if session:
                    session_id = session.id

            new_task = HumanTaskModel(
                session_id=session_id,
                title=task.title,
                description=task.description,
                assigned_to=task.assigned_to,
                metadata_json=json_lib.dumps(task.metadata) if task.metadata else None,
                created_by="manual"
            )
            db.add(new_task)
            await db.commit()
            await db.refresh(new_task)

            return {
                "id": new_task.id,
                "session_id": task.session_id,
                "title": new_task.title,
                "description": new_task.description,
                "assigned_to": new_task.assigned_to,
                "status": new_task.status
                , "completed": bool(new_task.completed)
            }
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nella creazione della human task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/message-notes", response_model=MessageNoteResponse)
async def create_message_note(note: MessageNoteCreate):
    """Crea una nuova nota/commento per un messaggio"""
    try:
        from app.services.message_review_service import MessageReviewService

        created = await MessageReviewService.create_note(
            message_id=note.message_id,
            rating=note.rating,
            note=note.note,
            created_by=note.created_by
        )
        if not created:
            raise HTTPException(status_code=400, detail="Impossibile creare la nota")

        return MessageNoteResponse(
            id=created.id,
            message_id=created.message_id,
            session_id=created.session_id,
            rating=created.rating,
            note=created.note,
            created_by=created.created_by,
            created_at=created.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nella creazione della message note: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/message-notes")
async def list_message_notes(message_id: int = None, session_id: int = None):
    """Lista note per un messaggio o per una sessione"""
    try:
        from app.services.message_review_service import MessageReviewService

        if message_id:
            notes = await MessageReviewService.get_notes_for_message(message_id)
        elif session_id:
            notes = await MessageReviewService.get_notes_for_session(session_id)
        else:
            # default: return empty list
            return []

        out = []
        for n in notes:
            out.append({
                "id": n.id,
                "message_id": n.message_id,
                "session_id": n.session_id,
                "rating": n.rating,
                "note": n.note,
                "created_by": n.created_by,
                "created_at": n.created_at.isoformat()
            })

        return out
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel recupero delle message notes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/messages/{message_id}/notes")
async def get_message_notes_for_message(message_id: int):
    try:
        from app.services.message_review_service import MessageReviewService
        notes = await MessageReviewService.get_notes_for_message(message_id)

        out = [
            {
                "id": n.id,
                "message_id": n.message_id,
                "session_id": n.session_id,
                "rating": n.rating,
                "note": n.note,
                "created_by": n.created_by,
                "created_at": n.created_at.isoformat()
            }
            for n in notes
        ]
        return out
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel recupero delle message notes per message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/tasks")
async def list_human_tasks(session_id: str = None):
    """Lista delle human tasks, opzionalmente filtrata per session"""
    try:
        async for db in get_db():
            stmt = select(HumanTaskModel)
            if session_id:
                # Recup session id numeric
                s = await db.execute(select(SessionModel).where(SessionModel.session_id == session_id))
                s_obj = s.scalar_one_or_none()
                if s_obj:
                    stmt = stmt.where(HumanTaskModel.session_id == s_obj.id)

            result = await db.execute(stmt.order_by(HumanTaskModel.created_at.desc()))
            tasks = result.scalars().all()

            out = []
            for t in tasks:
                out.append({
                    "id": t.id,
                    "session_id": t.session_id,
                    "title": t.title,
                    "description": t.description,
                    "assigned_to": t.assigned_to,
                    "status": t.status,
                    "completed": bool(t.completed),
                    "created_at": t.created_at.isoformat()
                })
            return out
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel recupero delle human tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/tasks/{task_id}")
async def get_human_task(task_id: int):
    try:
        async for db in get_db():
            result = await db.execute(select(HumanTaskModel).where(HumanTaskModel.id == task_id))
            t = result.scalar_one_or_none()
            if not t:
                raise HTTPException(status_code=404, detail="Task non trovata")

            return {
                "id": t.id,
                "session_id": t.session_id,
                "title": t.title,
                "description": t.description,
                "assigned_to": t.assigned_to,
                "status": t.status,
                "completed": bool(t.completed),
                "metadata": json_lib.loads(t.metadata_json) if t.metadata_json else None,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat()
            }
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel recupero della human task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.put("/api/tasks/{task_id}")
async def update_human_task(task_id: int, task_update: HumanTaskUpdate):
    """Aggiorna una human task - permette di marcare completata"""
    try:
        async for db in get_db():
            result = await db.execute(select(HumanTaskModel).where(HumanTaskModel.id == task_id))
            t = result.scalar_one_or_none()
            if not t:
                raise HTTPException(status_code=404, detail="Task non trovata")

            if task_update.completed is not None:
                t.completed = bool(task_update.completed)
                # optionally update status
                t.status = "closed" if task_update.completed else t.status
            if task_update.status:
                t.status = task_update.status

            await db.commit()
            await db.refresh(t)

            return {
                "id": t.id,
                "completed": bool(t.completed),
                "status": t.status
            }

    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore aggiornamento task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    @router.get("/api/system-prompts/active")
    async def get_system_prompt_active():
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


@router.get("/tasks", response_class=HTMLResponse)
async def human_tasks_dashboard(request: Request):
    """Pagina dashboard per le human tasks"""
    try:
        async for db in get_db():
            result = await db.execute(select(HumanTaskModel).order_by(HumanTaskModel.created_at.desc()))
            tasks = result.scalars().all()

            tasks_data = []
            for t in tasks:
                tasks_data.append({
                    'id': t.id,
                    'session_id': t.session_id,
                    'title': t.title,
                    'description': t.description,
                    'assigned_to': t.assigned_to,
                    'completed': bool(t.completed),
                    'created_at': t.created_at,
                })

            return templates.TemplateResponse('human_tasks.html', { 'request': request, 'tasks': tasks_data })
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering della dashboard human tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}/tasks", response_class=HTMLResponse)
async def session_tasks_dashboard(session_id: str, request: Request):
    """Pagina dashboard per le task di una sessione specifica"""
    try:
        async for db in get_db():
            # Find session
            stmt = select(SessionModel).where(SessionModel.session_id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            if not session:
                raise HTTPException(status_code=404, detail="Sessione non trovata")
            
            # Get all tasks for this session
            stmt_tasks = select(HumanTaskModel).where(
                HumanTaskModel.session_id == session.id
            ).order_by(HumanTaskModel.created_at.desc())
            result_tasks = await db.execute(stmt_tasks)
            tasks = result_tasks.scalars().all()

            # Prepare data before exiting async context
            tasks_data = []
            for t in tasks:
                tasks_data.append({
                    'id': t.id,
                    'session_id': t.session_id,
                    'title': t.title,
                    'description': t.description,
                    'assigned_to': t.assigned_to,
                    'completed': bool(t.completed),
                    'status': t.status,
                    'created_at': t.created_at.isoformat(),
                })

            # Avoid triggering lazy load on session.messages (which would cause greenlet_spawn error)
            # Do an explicit count query instead
            from app.models.database_models import MessageModel
            result_count = await db.execute(select(func.count(MessageModel.id)).where(MessageModel.session_id == session.id))
            message_count = result_count.scalar() or 0

            session_info = {
                'session_id': session.session_id,
                'current_lifecycle': session.current_lifecycle.value,
                'message_count': int(message_count),
                'task_count': len(tasks)
            }

        # Return response after exiting async context
        return templates.TemplateResponse('session_tasks.html', {
            'request': request,
            'session': session_info,
            'tasks': tasks_data
        })
    except HTTPException:
        raise
    except Exception as e:
        from app.main import logger
        logger.error(f"Errore nel rendering della dashboard sessione tasks {session_id}: {e}")
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
@router.get("/api/execute/{command}")
async def execute_command(command: str):
    """Endpoint API per eseguire comandi del server script"""
    try:

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
