"""
Agente unificato che gestisce conversazione e lifecycle management in un'unica chiamata AI
"""
import json
import time
from typing import Dict, Optional, List, Union
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import asyncio

from datapizza.clients.google import GoogleClient
from datapizza.agents import Agent

from app.models.lifecycle import (
    LifecycleStage, 
    LifecycleResponse
)
from app.data.lifecycle_config import LIFECYCLE_SCRIPTS
from app.config import settings
from app.database import get_db
from app.models.database_models import SessionModel, MessageModel
from app.models.database_models import HumanTaskModel
from app.logger_config import log_capture
import json as json_lib

from app.services.system_prompt_service import SystemPromptService


class ChatbotError(Exception):
    """Eccezione base per errori del chatbot"""
    pass


class AIError(ChatbotError):
    """Errore quando l'AI non è disponibile o fallisce"""
    pass


class ParsingError(ChatbotError):
    """Errore nel parsing della risposta AI"""
    pass


class UnifiedAgent:
    """Agente unificato che gestisce conversazione e lifecycle management"""
    
    def __init__(self):
        """Inizializza l'agente unificato"""
        try:
            # Verifica che l'API key sia configurata
            if not settings.google_ai_api_key:
                raise ValueError("GOOGLE_AI_API_KEY non configurata nel file .env")
            
            # Inizializza il client Google
            self.client = GoogleClient(
                api_key=settings.google_ai_api_key,
                model="gemini-flash-latest",
            )
            
            # Carica il prompt di sistema attivo dal database
            # Nota: il prompt verrà caricato dinamicamente per ogni richiesta
            self.agent = None  # Verrà inizializzato al primo uso
            
            logger.info("UnifiedAgent inizializzato con successo")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di UnifiedAgent: {e}")
            raise

    async def _get_agent(self, model_name: str = None) -> Agent:
        """Ottiene l'agente con il prompt di sistema attivo e il modello specificato
        
        Args:
            model_name: Nome del modello da utilizzare (opzionale, usa il default se non specificato)
        """
        # Determina il modello da usare
        if not model_name:
            # Se non specificato, usa il modello attivo dal database
            from app.services.ai_model_service import AIModelService
            active_model = await AIModelService.get_active_model()
            model_name = active_model.name if active_model else "gemini-flash-latest"
        
        logger.info(f"Utilizzo del modello: {model_name}")
        
        # Carica il prompt attivo dal database
        system_prompt = await SystemPromptService.get_active_prompt()
        logger.info("Caricato prompt di sistema attivo dal database")
        logger.info("===============================================")
        logger.info(f"{system_prompt}")
        logger.info("===============================================")
        
        # Crea un nuovo client con il modello specificato
        client = GoogleClient(
            api_key=settings.google_ai_api_key,
            model=model_name,
        )
        
        # Inizializza l'agente con il prompt caricato
        agent = Agent(
            client=client,
            name="Corposostenibile Unified Agent",
            system_prompt=system_prompt,
        )
        logger.info(f"Agente inizializzato con prompt dal database e modello {model_name}")
        
        return agent

    async def get_or_create_session(self, session_id: str, db: AsyncSession) -> SessionModel:
        # Cerca la sessione esistente
        result = await db.execute(
            select(SessionModel).where(SessionModel.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if session:
            return session
        
        # Crea una nuova sessione
        new_session = SessionModel(session_id=session_id)
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        logger.info(f"Nuova sessione creata: {session_id}")
        return new_session

    def _format_snippets_context(self, snippets: Dict[str, str]) -> str:
        """Formatta gli snippet disponibili per il contesto del prompt"""
        if not snippets:
            return "Nessuno snippet disponibile per questa fase."
        
        snippets_list = []
        for snippet_id, snippet_content in snippets.items():
            snippets_list.append(f"- {snippet_id}: {snippet_content}")
        
        return "\n".join(snippets_list)

    def _clean_ai_response(self, ai_response: str) -> str:
        """Pulisce la risposta AI rimuovendo markdown e spazi extra"""
        cleaned_response = ai_response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        return cleaned_response.strip()

    async def _add_user_message_to_history(self, session: SessionModel, user_message: str, db: AsyncSession) -> None:
        """Aggiunge solo il messaggio utente alla cronologia senza risposta dell'assistente"""
        user_msg = MessageModel(
            session_id=session.id,
            role="user",
            message=user_message,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(user_msg)
        await db.commit()

    def _parse_ai_response(self, ai_response: str) -> Dict:
        """Parssa la risposta JSON dell'AI"""
        try:
            cleaned_response = self._clean_ai_response(ai_response)
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Errore nel parsing JSON: {e}")
            logger.error(f"Risposta AI: {ai_response}")
            # Proviamo a riparare comuni problemi nel JSON restituito dall'AI.
            # Un problema frequente: l'AI include "doppi apici" non scappati all'interno di stringhe (es. "fai da te"),
            # questo rompe il parsing standard. Proviamo una correzione semplice per i campi di testo.
            try:
                fixed = self._repair_unescaped_inner_quotes(cleaned_response, keys=["text", "reasoning", "message"])
                return json.loads(fixed)
            except Exception:
                logger.error(f"Riparazione JSON fallita. Raw response: {ai_response}")
                raise ParsingError(f"Errore nel parsing della risposta AI: {str(e)}")

    def _normalize_messages(self, messages: Union[str, Dict, List]) -> List[Dict[str, Union[str, int]]]:
        """Normalizza i messaggi da stringa, dict singolo o lista eterogenea a lista uniforme"""
        if isinstance(messages, str):
            return [{"text": messages, "delay_ms": 0}]
        elif isinstance(messages, dict):
            return [{
                "text": messages.get("text", ""),
                "delay_ms": messages.get("delay_ms", 0)
            }]
        elif isinstance(messages, list):
            normalized_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    normalized_messages.append({
                        "text": msg.get("text", ""),
                        "delay_ms": msg.get("delay_ms", 1000)
                    })
                else:
                    normalized_messages.append({"text": str(msg), "delay_ms": 1000})
            return normalized_messages
        else:
            return [{"text": str(messages), "delay_ms": 0}]

    def _repair_unescaped_inner_quotes(self, text: str, keys: list[str]) -> str:
        """Ripara stringhe JSON dove l'AI ha inserito doppi apici non scappati all'interno del contenuto.

        Strategia:
        - Per ogni chiave in `keys`, trova le occorrenze del valore stringa associata
        - Scandisci il contenuto del valore e scappa i doppi apici che non sono il delimitatore finale
          (identificando come delimitatore finale l'apice doppio seguito da uno dei caratteri JSON validi: , ] })
        - Ritorna il testo con le correzioni applicate

        Nota: soluzione pragmatica per casi comuni (es. "fai da te"), non un parser JSON completo.
        """
        import re

        if not text or not keys:
            return text

        chars = list(text)
        for key in keys:
            # Pattern che trova l'indice subito dopo "<key>" : "
            pattern = re.compile(rf'"{re.escape(key)}"\s*:\s*"', re.IGNORECASE)
            for m in pattern.finditer(text):
                # Inizio del valore stringa
                start = m.end()  # index of the opening quote char + 0
                i = start
                # Scandisce fino a trovare la fine della stringa che è: an unescaped '"' followed by optional spaces and one of ,}] or end
                while i < len(chars):
                    ch = chars[i]
                    if ch == '"':
                        # check if escaped
                        if i > 0 and chars[i - 1] == '\\':
                            i += 1
                            continue

                        # Lookahead to see if it's closing quote: next non-space char is , or } or ] or end of string
                        j = i + 1
                        while j < len(chars) and chars[j].isspace():
                            j += 1
                        if j >= len(chars) or chars[j] in [',', '}', ']']:
                            # This is the real closing quote
                            break
                        else:
                            # This is an inner quote, escape it
                            chars[i] = '\\"'
                            # Move past the newly inserted escape - adjust i accordingly
                            i += 2
                            continue
                    i += 1

        return ''.join(chars)

    async def _call_ai_agent(self, prompt: str, model_name: str = None, context: str = "") -> str:
        """Chiama l'agente AI e gestisce gli errori
        
        Args:
            prompt: Il prompt da inviare all'AI
            model_name: Nome del modello da utilizzare (opzionale)
            context: Contesto aggiuntivo per il logging
        """
        try:
            agent = await self._get_agent(model_name=model_name)
            ai_result = await agent.a_run(prompt)
            return ai_result.text
        except Exception as ai_error:
            logger.error(f"Errore con l'AI{context}: {ai_error}")
            raise AIError(f"Errore nell'elaborazione della richiesta AI{context}: {str(ai_error)}")

    async def _handle_lifecycle_transition(self, session: SessionModel, new_lifecycle_str: str, confidence: float, db: AsyncSession) -> bool:
        """Gestisce la transizione del lifecycle se necessario"""
        if confidence < 0.7:
            return False
            
        try:
            new_lifecycle = LifecycleStage[new_lifecycle_str.upper().replace(" ", "_")]
            if new_lifecycle != session.current_lifecycle:
                await self._update_session_lifecycle(session, new_lifecycle, db)
                return True
        except (KeyError, ValueError) as e:
            logger.warning(f"Lifecycle non valido: {new_lifecycle_str}")
            
        return False

    async def _process_ai_response(self, ai_response: str, session: SessionModel, db: AsyncSession) -> Dict:
        """Elabora la risposta AI completa: parsing, normalizzazione, transizione"""
        # Parse risposta AI
        response_data = self._parse_ai_response(ai_response)
        
        # Estrai dati
        messages = response_data.get("messages") or response_data.get("message", "Ciao! Come posso aiutarti oggi?")
        should_change = response_data.get("should_change_lifecycle", False)
        new_lifecycle_str = response_data.get("new_lifecycle", session.current_lifecycle.value)
        reasoning = response_data.get("reasoning", "Risposta automatica")
        confidence = response_data.get("confidence", 0.5)
        requires_human = response_data.get("requires_human", False)
        human_task = response_data.get("human_task")
        
        # Normalizza messaggi
        # If a human task is required, the AI should not return messages for the user
        if requires_human:
            normalized_messages = []
        else:
            normalized_messages = self._normalize_messages(messages)
        
        # Gestisci transizione lifecycle solo se richiesta dall'AI
        lifecycle_changed = False
        if should_change:
            lifecycle_changed = await self._handle_lifecycle_transition(session, new_lifecycle_str, confidence, db)
        
        return {
            "messages": normalized_messages,
            "should_change": should_change,
            "new_lifecycle_str": new_lifecycle_str,
            "reasoning": reasoning,
            "confidence": confidence,
            "lifecycle_changed": lifecycle_changed,
            "requires_human": requires_human,
            "human_task": human_task,
            "full_message_text": " ".join([msg["text"] for msg in normalized_messages])
        }

    async def _build_conversation_context(self, session: SessionModel, db: AsyncSession) -> str:
        """Costruisce il contesto della conversazione dalla cronologia"""
        # Ottieni gli ultimi 10 messaggi (5 scambi)
        result = await db.execute(
            select(MessageModel)
            .where(MessageModel.session_id == session.id)
            .order_by(MessageModel.timestamp.desc())
            .limit(10)
        )
        messages = result.scalars().all()
        
        if not messages:
            return "Nessuna conversazione precedente."
        
        # Riordina cronologicamente
        messages = list(reversed(messages))
        
        context_lines = []
        for msg in messages:
            role = "UTENTE" if msg.role == "user" else "ASSISTENTE"
            context_lines.append(f"{role}: {msg.message}")
        
        return "\n".join(context_lines)

    async def _get_unified_prompt(self, session: SessionModel, user_message: str, db: AsyncSession) -> str:
        """Genera il prompt unificato che gestisce conversazione e lifecycle"""
        current_lifecycle = session.current_lifecycle
        current_config = LIFECYCLE_SCRIPTS.get(current_lifecycle, {})
        
        # Informazioni sul lifecycle corrente
        script_raw = current_config.get("script", "")
        if isinstance(script_raw, list):
            # Se è una lista di snippet, formatta come elenco numerato
            script_text = "\n".join(f"{i+1}. {snippet}" for i, snippet in enumerate(script_raw))
        else:
            # Se è una stringa, usa direttamente
            script_text = script_raw
        objective = current_config.get("objective", "")
        transition_indicators = current_config.get("transition_indicators", [])
        next_stage = current_config.get("next_stage")
        
        # Ottieni snippet disponibili per questo lifecycle
        available_snippets = current_config.get("available_snippets", {})
        snippets_context = self._format_snippets_context(available_snippets)
        
        # Contesto conversazione
        conversation_context = await self._build_conversation_context(session, db)
        
        # Costruisci il prompt unificato
        unified_prompt = f"""LIFECYCLE CORRENTE: {current_lifecycle.value.upper()}

OBIETTIVO LIFECYCLE: {objective}

SCRIPT GUIDA PER QUESTO LIFECYCLE:
{script_text}

SNIPPET DISPONIBILI PER QUESTA FASE:
{snippets_context}

CRONOLOGIA CONVERSAZIONE:
{conversation_context}

MESSAGGIO UTENTE: {user_message}

ISTRUZIONI SPECIFICHE PER QUESTO LIFECYCLE:
1. Usa il script come guida ma mantieni la conversazione fluida
2. Valuta se il messaggio dell'utente indica che è pronto per il prossimo lifecycle
3. Se decidi di spezzettare, specifica i delay tra i messaggi
4. Nel caso in cui l'utente chiede delle cose a cui non sai rispondere, crea una task umana: "human_task": {{"title": "...", "description": "...", "assigned_to": "..."}} e imposta "requires_human": true

INDICATORI PER PASSARE AL PROSSIMO LIFECYCLE ({next_stage.value if next_stage else 'NESSUNO'}):
{chr(10).join(f"- {indicator}" for indicator in transition_indicators) if transition_indicators else "- Lifecycle finale raggiunto"}

FORMATO RISPOSTA RICHIESTO:
Devi rispondere SEMPRE in questo formato JSON:
{{
    "messages": "La tua risposta completa" 
    OPPURE 
    "messages": [
        {{"text": "Prima parte del messaggio", "delay_ms": 5000}},
        {{"text": "Seconda parte", "delay_ms": 10000}}
    ],
    "should_change_lifecycle": true/false,
    "new_lifecycle": "{next_stage.value} o null",
    "reasoning": "Spiegazione del perché hai deciso di cambiare o non cambiare lifecycle",
    "confidence": 0.0-1.0,
    "requires_human": true/false,
    "human_task": {{
        "title": "Breve titolo della task",
        "description": "Dettaglio della task per l'operatore umano",
        "assigned_to": "opzionale@team.it",
        "metadata": {{"key": "value"}}
    }}
}}

IMPORTANTE:
- Il campo "messages" può essere una stringa (risposta singola senza delay), un oggetto singolo con "text" e "delay_ms", o un array di oggetti
- Ogni oggetto nell'array ha "text" (il messaggio) e "delay_ms" (millisecondi di attesa prima del prossimo, minimo 10000ms se multipli)
- Cambia lifecycle solo se sei sicuro al 70% o più (confidence >= 0.7)
- La risposta deve essere SEMPRE un JSON valido
"""

        logger.info(f"Generated unified prompt for session {session.session_id}:\n{unified_prompt}")
        return unified_prompt

    async def chat(self, session_id: str, user_message: str, model_name: str = None, batch_wait_seconds: Optional[int] = None) -> LifecycleResponse:
        """
        Gestisce una conversazione completa con decisione automatica del lifecycle
        
        Args:
            session_id: ID della sessione di chat
            user_message: Messaggio dell'utente
            model_name: Nome del modello AI da utilizzare (opzionale)
            
        Returns:
            LifecycleResponse con la risposta e informazioni sul lifecycle
        """
        # Inizia una nuova sessione di log
        log_capture.start_session()
        
        async for db in get_db():
            try:
                # STARTING AGENT
                log_capture.add_log("INFO", "-------------------------------------------------")
                log_capture.add_log("INFO", "STARTING AGENT")
                
                # Ottieni o crea la sessione
                session = await self.get_or_create_session(session_id, db)
                previous_lifecycle = session.current_lifecycle
                
                log_capture.add_log("INFO", f"Session loaded: {session_id}")
                
                # Check if this is the first message
                result = await db.execute(
                    select(func.count(MessageModel.id)).where(MessageModel.session_id == session.id)
                )
                message_count = result.scalar()
                
                if message_count == 0:
                    # First message: send auto response and then call AI with CONTRASSEGNATO
                    auto_response = """Ciao! Grazie di avermi scritto! 

Questo è un messaggio automatico che ho scritto personalmente per riuscire a ringraziarti subito della fiducia!🙏

Come sai ricevo centinaia di richieste ogni giorno e ci tengo a dedicarti personalmente l'attenzione che meriti."""
                    
                    # Update lifecycle to CONTRASSEGNATO
                    await self._update_session_lifecycle(session, LifecycleStage.CONTRASSEGNATO, db)
                    
                    # Add auto response to history
                    await self._add_to_conversation_history(session, user_message, auto_response, db)
                    
                    # Now generate prompt for CONTRASSEGNATO and call AI
                    session_refreshed = await db.get(SessionModel, session.id)
                    unified_prompt = await self._get_unified_prompt(session_refreshed, user_message, db)
                    log_capture.add_log("INFO", f"SCRIPT GUIDA (CONTRASSEGNATO dopo messaggio automatico)\n{unified_prompt}")
                    
                    logger.info(f"Generando risposta CONTRASSEGNATO per primo messaggio in sessione {session_id}")
                    
                    # Call AI for CONTRASSEGNATO
                    ai_response = await self._call_ai_agent(unified_prompt, model_name=model_name)
                    log_capture.add_log("INFO", "AI response received (CONTRASSEGNATO)")
                    
                    # Process AI response
                    contrassegnato_result = await self._process_ai_response(ai_response, session_refreshed, db)
                    
                    # Add AI response to history (unless human task required)
                    created_task = None
                    if not contrassegnato_result.get("requires_human"):
                        await self._add_assistant_response_to_history(session_refreshed, contrassegnato_result["full_message_text"], db)
                    else:
                        created_task = await self._create_human_task(session_refreshed, contrassegnato_result.get("human_task") or {}, db)
                        log_capture.add_log("INFO", f"Human task created (contrassegnato first message): {created_task}")
                    
                    # Combine messages: auto response + AI response
                    combined_messages = [{"text": auto_response.strip(), "delay_ms": 0}]
                    if isinstance(contrassegnato_result["messages"], list):
                        combined_messages.extend(contrassegnato_result["messages"])
                    else:
                        combined_messages.append({"text": contrassegnato_result["messages"], "delay_ms": 1000})
                    
                    next_actions = self._get_next_actions(session_refreshed.current_lifecycle)
                    
                    return LifecycleResponse(
                        messages=combined_messages,
                        current_lifecycle=session_refreshed.current_lifecycle,
                        lifecycle_changed=True,
                        previous_lifecycle=previous_lifecycle,
                        next_actions=next_actions,
                        ai_reasoning=contrassegnato_result["reasoning"],
                        confidence=contrassegnato_result["confidence"],
                        debug_logs=log_capture.get_session_logs(),
                        full_logs=log_capture.get_session_logs_str(),
                        is_conversation_finished=False,
                        requires_human=contrassegnato_result.get("requires_human", False),
                        human_task=created_task if contrassegnato_result.get("requires_human") else None
                    )

                # If we are already in a batch wait window, append message and return queued response
                if session.is_batch_waiting:
                    # Save user message only and don't start a new AI call
                    await self._add_user_message_to_history(session, user_message, db)
                    log_capture.add_log("INFO", f"Message queued for session {session.session_id} in batch")
                    return LifecycleResponse(
                        messages=[],
                        current_lifecycle=session.current_lifecycle,
                        lifecycle_changed=False,
                        previous_lifecycle=None,
                        next_actions=self._get_next_actions(session.current_lifecycle),
                        ai_reasoning="Messaggio messo in coda (batch aggregation)",
                        confidence=1.0,
                        debug_logs=log_capture.get_session_logs(),
                        full_logs=log_capture.get_session_logs_str(),
                        is_conversation_finished=session.is_conversation_finished
                    )

                # If not in batch mode, set batch waiting and delay the AI call to gather subsequent messages
                # This prevents multiple AI calls when the user sends several messages quickly.
                # Mark session as waiting for batch and commit
                session.is_batch_waiting = True
                session.batch_started_at = datetime.now(timezone.utc)
                await db.commit()

                # Add current user message to history and then wait for more messages
                await self._add_user_message_to_history(session, user_message, db)

                # Wait for aggregation window (default 60s). This is intentionally blocking the request.
                # Respect explicit 0 value (no wait) vs None (default wait)
                wait_seconds = int(batch_wait_seconds) if batch_wait_seconds is not None else 60
                if wait_seconds < 0:
                    wait_seconds = 0
                log_capture.add_log("INFO", f"Batch wait started for session {session.session_id} - waiting {wait_seconds}s")
                # Log a per-second countdown in the terminal like a timer
                logger.info(f"Batch wait started for session {session.session_id} - waiting {wait_seconds}s")
                for i in range(wait_seconds):
                    # Update every second to show progress in terminal and debug logs
                    logger.info(f"Batch wait for session {session.session_id}: {i+1}/{wait_seconds} s")
                    log_capture.add_log("INFO", f"Batch wait for session {session.session_id}: {i+1}/{wait_seconds} s")
                    await asyncio.sleep(1)

                # Refresh session and proceed to generate prompt with aggregated messages
                session = await db.get(SessionModel, session.id)
                session.is_batch_waiting = False
                session.batch_started_at = None
                await db.commit()

                # Now continue with the normal unified prompt generation using aggregated messages
                unified_prompt = await self._get_unified_prompt(session, user_message, db)
                log_capture.add_log("INFO", f"Batch window ended; calling AI for session {session.session_id}")
                
                # CASO NORMALE: genera il prompt unificato
                unified_prompt = await self._get_unified_prompt(session, user_message, db)
                log_capture.add_log("INFO", f"SCRIPT GUIDA\n{unified_prompt}")
                
                logger.info("-------------------------------------------------")
                logger.info(f"Prompt unificato per sessione {session_id}:\n{unified_prompt}")
                logger.info("-------------------------------------------------")
                
                # Invia il messaggio all'AI
                log_capture.add_log("INFO", "-------------------------------------------------")
                log_capture.add_log("INFO", f"Invio messaggio unificato per sessione {session_id}")
                logger.info(f"Invio messaggio unificato per sessione {session_id}")
                
                ai_response = await self._call_ai_agent(unified_prompt, model_name=model_name)
                log_capture.add_log("INFO", "AI response received")
                logger.info(f"Risposta AI ricevuta per sessione {session_id}")
                
                # Elabora la risposta AI completa
                log_capture.add_log("INFO", "Parsing AI response...")
                result = await self._process_ai_response(ai_response, session, db)
                
                log_capture.add_log("INFO", f"Decision: change={result['should_change']}, confidence={result['confidence']}, messages={len(result['messages'])}")
                log_capture.add_log("INFO", f"```json\n{json.dumps(result, indent=2)}\n```")
                log_capture.add_log("INFO", "JSON parsed successfully")
                
                # Aggiungi il messaggio alla cronologia
                await self._add_to_conversation_history(session, user_message, result["full_message_text"], db)
                log_capture.add_log("INFO", "Conversation history updated")
                
                # Genera next actions
                next_actions = self._get_next_actions(session.current_lifecycle)
                
                log_capture.add_log("INFO", "Response ready")
                
                return LifecycleResponse(
                    messages=result["messages"],
                    current_lifecycle=session.current_lifecycle,
                    lifecycle_changed=result["lifecycle_changed"],
                    previous_lifecycle=previous_lifecycle if result["lifecycle_changed"] else None,
                    next_actions=next_actions,
                    ai_reasoning=result["reasoning"],
                    confidence=result["confidence"],
                    debug_logs=log_capture.get_session_logs(),
                    full_logs=log_capture.get_session_logs_str(),
                    is_conversation_finished=session.is_conversation_finished,
                    requires_human=result.get("requires_human", False),
                    human_task=created_task if result.get("requires_human") else None
                )
                    
            except Exception as e:
                log_capture.add_log("INFO", "ERROR: General error")
                logger.error(f"Errore generale nell'agente unificato: {e}")
                raise ChatbotError(f"Errore interno del chatbot: {str(e)}")

    async def _update_session_lifecycle(self, session: SessionModel, new_lifecycle: LifecycleStage, db: AsyncSession) -> None:
        """Aggiorna il lifecycle della sessione"""
        session.current_lifecycle = new_lifecycle

        # Imposta il flag di conversazione finita se si passa a LINK_INVIATO
        from app.models.lifecycle import LifecycleStage as LS
        if new_lifecycle == LS.LINK_INVIATO:
            session.is_conversation_finished = True
            logger.info(f"Conversazione finita impostata per sessione {session.session_id}")

        await db.commit()

    async def _add_to_conversation_history(self, session: SessionModel, user_message: str, ai_response: str, db: AsyncSession) -> None:
        """Aggiunge i messaggi alla cronologia della conversazione"""
        
        # Aggiungi messaggio utente
        user_msg = MessageModel(
            session_id=session.id,
            role="user",
            message=user_message,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(user_msg)
        
        # Aggiungi risposta AI
        ai_msg = MessageModel(
            session_id=session.id,
            role="assistant",
            message=ai_response,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(ai_msg)
        
        await db.commit()
        
        # Mantieni solo gli ultimi 20 messaggi per ottimizzare la memoria (opzionale, ma per pulizia)
        # Potremmo implementare una pulizia periodica

    async def _add_assistant_response_to_history(self, session: SessionModel, ai_response: str, db: AsyncSession) -> None:
        """Aggiunge solo una risposta assistant alla cronologia (senza nuovo user message)"""
        
        # Aggiungi risposta AI
        ai_msg = MessageModel(
            session_id=session.id,
            role="assistant",
            message=ai_response,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(ai_msg)
        
        await db.commit()

    async def _create_human_task(self, session: SessionModel, task_payload: Dict, db: AsyncSession) -> Dict:
        """Crea una task per intervento umano basata sul payload fornito dall'AI"""
        try:
            title = task_payload.get("title") or f"Task from session {session.session_id}"
            description = task_payload.get("description") or "Task generata automaticamente dall'agente AI"
            assigned_to = task_payload.get("assigned_to")
            metadata = task_payload.get("metadata")

            human_task = HumanTaskModel(
                session_id=session.id,
                title=title,
                description=description,
                assigned_to=assigned_to,
                metadata_json=json_lib.dumps(metadata) if metadata else None,
                created_by="agent"
            )
            db.add(human_task)
            await db.commit()
            await db.refresh(human_task)

            return {
                "id": human_task.id,
                "session_id": session.session_id,
                "title": human_task.title,
                "description": human_task.description,
                "status": human_task.status,
                "assigned_to": human_task.assigned_to,
                "created_at": human_task.created_at.isoformat(),
                "metadata": json_lib.loads(human_task.metadata_json) if human_task.metadata_json else None
            }
        except Exception as e:
            logger.error(f"Errore nella creazione della human task: {e}")
            return {"error": str(e)}

    def _get_next_actions(self, current_lifecycle: LifecycleStage) -> List[str]:
        """Genera le prossime azioni suggerite basate sul lifecycle corrente"""
        actions_map = {
            LifecycleStage.CONTRASSEGNATO: [
                "Approfondisci i problemi identificati",
                "Valuta il livello di motivazione del cliente",
                "Inizia a presentare i benefici del percorso"
            ],
            LifecycleStage.IN_TARGET: [
                "Presenta i benefici del percorso integrato",
                "Spiega l'approccio nutrizione + psicologia",
                "Introduci la consulenza gratuita"
            ],
            LifecycleStage.LINK_DA_INVIARE: [
                "Conferma l'interesse per la consulenza",
                "Prepara per l'invio del link di prenotazione",
                "Rassicura sulla qualità del servizio"
            ],
            LifecycleStage.LINK_INVIATO: [
                "Conferma l'invio del link",
                "Fornisci istruzioni per la prenotazione",
                "Rimani disponibile per domande"
            ]
        }
        
        return actions_map.get(current_lifecycle, ["Continua la conversazione"])

    async def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Ottiene informazioni sulla sessione"""
        async for db in get_db():
            result = await db.execute(
                select(SessionModel).where(SessionModel.session_id == session_id)
            )
            session = result.scalar_one_or_none()
            if not session:
                return None

            # Conta i messaggi
            result = await db.execute(
                select(func.count(MessageModel.id)).where(MessageModel.session_id == session.id)
            )
            message_count = result.scalar()

            return {
                "session_id": session.session_id,
                "current_lifecycle": session.current_lifecycle.value,
                "conversation_length": message_count,
                "is_conversation_finished": session.is_conversation_finished,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat()
            }

    async def is_available(self) -> bool:
        """Verifica se il servizio è disponibile"""
        try:
            return self.client is not None
        except:
            return False

    async def health_check(self) -> Dict[str, str]:
        """Esegue un health check del servizio"""
        try:
            # Test semplice con l'AI
            agent = await self._get_agent()
            test_result = await agent.a_run("Rispondi solo con 'OK'")
            return {
                "status": "healthy",
                "ai_response": "OK" in test_result.text,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Istanza globale dell'agente unificato
unified_agent = UnifiedAgent()