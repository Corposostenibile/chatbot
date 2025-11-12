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

from datapizza.clients.google import GoogleClient
from datapizza.agents import Agent

from app.models.lifecycle import (
    LifecycleStage, 
    ChatSession, 
    LifecycleResponse
)
from app.data.lifecycle_config import LIFECYCLE_SCRIPTS
from app.config import settings
from app.database import get_db
from app.models.database_models import SessionModel, MessageModel
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

    async def _get_agent(self) -> Agent:
        """Ottiene l'agente con il prompt di sistema attivo"""
        if self.agent is None:
            # Carica il prompt attivo dal database
            system_prompt = await SystemPromptService.get_active_prompt()
            logger.info("Caricato prompt di sistema attivo dal database")
            logger.info("===============================================")
            logger.info(f"{system_prompt}")
            logger.info("===============================================")
            
            # Inizializza l'agente con il prompt caricato
            self.agent = Agent(
                client=self.client,
                name="Corposostenibile Unified Agent",
                system_prompt=system_prompt,
            )
            logger.info("Agente inizializzato con prompt dal database")
        
        return self.agent

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

    def _parse_ai_response(self, ai_response: str) -> Dict:
        """Parssa la risposta JSON dell'AI"""
        try:
            cleaned_response = self._clean_ai_response(ai_response)
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Errore nel parsing JSON: {e}")
            logger.error(f"Risposta AI: {ai_response}")
            raise ParsingError(f"Errore nel parsing della risposta AI: {str(e)}")

    def _normalize_messages(self, messages: Union[str, List]) -> List[Dict[str, Union[str, int]]]:
        """Normalizza i messaggi da stringa o lista eterogenea a lista uniforme"""
        if isinstance(messages, str):
            return [{"text": messages, "delay_ms": 0}]
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

    async def _call_ai_agent(self, prompt: str, context: str = "") -> str:
        """Chiama l'agente AI e gestisce gli errori"""
        try:
            agent = await self._get_agent()
            ai_result = await agent.a_run(prompt)
            return ai_result.text
        except Exception as ai_error:
            logger.error(f"Errore con l'AI{context}: {ai_error}")
            raise AIError(f"Errore nell'elaborazione della richiesta AI{context}: {str(ai_error)}")

    async def _save_message_to_history(self, session_id: int, role: str, message: str, db: AsyncSession) -> None:
        """Salva un messaggio nella cronologia"""
        msg = MessageModel(
            session_id=session_id,
            role=role,
            message=message,
            timestamp=datetime.now(timezone.utc)
        )
        db.add(msg)
        await db.commit()

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
        
        # Normalizza messaggi
        normalized_messages = self._normalize_messages(messages)
        
        # Gestisci transizione lifecycle
        lifecycle_changed = await self._handle_lifecycle_transition(session, new_lifecycle_str, confidence, db)
        
        return {
            "messages": normalized_messages,
            "should_change": should_change,
            "new_lifecycle_str": new_lifecycle_str,
            "reasoning": reasoning,
            "confidence": confidence,
            "lifecycle_changed": lifecycle_changed,
            "full_message_text": " ".join([msg["text"] for msg in normalized_messages])
        }

    async def _handle_nuova_lead_special_case(self, session: SessionModel, user_message: str, db: AsyncSession) -> LifecycleResponse:
        """Gestisce il caso speciale di NUOVA_LEAD"""
        logger.info(f"GESTIONE SPECIALE NUOVA_LEAD per sessione {session.session_id}")
        log_capture.add_log("INFO", "LIFECYCLE: NUOVA_LEAD - Usando script di default, passando a CONTRASSEGNATO")
        
        # Ottieni script NUOVA_LEAD
        nuova_lead_config = LIFECYCLE_SCRIPTS[LifecycleStage.NUOVA_LEAD]
        script_text = nuova_lead_config.get("script", "")
        
        # Salva messaggi nella cronologia
        await self._save_message_to_history(session.id, "user", user_message, db)
        await self._save_message_to_history(session.id, "assistant", script_text, db)
        
        # Transizione a CONTRASSEGNATO
        previous_lifecycle = session.current_lifecycle
        session.current_lifecycle = LifecycleStage.CONTRASSEGNATO
        db.add(session)
        await db.commit()
        
        log_capture.add_log("INFO", f"Lifecycle transitioned: {previous_lifecycle.value} → {LifecycleStage.CONTRASSEGNATO.value}")
        
        # Prepara messaggi risposta
        messages = [{"text": script_text.strip(), "delay_ms": 0}]
        
        # Genera risposta CONTRASSEGNATO
        session_refreshed = await db.get(SessionModel, session.id)
        unified_prompt = await self._get_unified_prompt(session_refreshed, user_message, db)
        log_capture.add_log("INFO", f"SCRIPT GUIDA (CONTRASSEGNATO)\n{unified_prompt}")
        
        logger.info(f"Generando risposta CONTRASSEGNATO per sessione {session.session_id}")
        
        # Chiama AI per CONTRASSEGNATO
        ai_response = await self._call_ai_agent(unified_prompt, " (CONTRASSEGNATO)")
        log_capture.add_log("INFO", "AI response received (CONTRASSEGNATO)")
        
        # Elabora risposta CONTRASSEGNATO
        contrassegnato_result = await self._process_ai_response(ai_response, session_refreshed, db)
        
        # Aggiungi messaggi CONTRASSEGNATO
        messages.extend(contrassegnato_result["messages"])
        
        # Salva risposta CONTRASSEGNATO nella cronologia
        await self._save_message_to_history(session.id, "assistant", contrassegnato_result["full_message_text"], db)
        
        # Gestisci transizione se necessaria
        if contrassegnato_result["lifecycle_changed"]:
            session_refreshed = await db.get(SessionModel, session.id)
        
        return LifecycleResponse(
            messages=messages,
            current_lifecycle=session_refreshed.current_lifecycle,
            lifecycle_changed=True,
            previous_lifecycle=previous_lifecycle,
            next_actions=self._get_next_actions(session_refreshed.current_lifecycle),
            ai_reasoning=contrassegnato_result["reasoning"],
            confidence=contrassegnato_result["confidence"],
            debug_logs=log_capture.get_session_logs(),
            full_logs=log_capture.get_session_logs_str()
        )

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
            # Se è una stringa (come per NUOVA_LEAD), usa direttamente
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
OBIETTIVO CORRENTE: {objective}

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

INDICATORI PER PASSARE AL PROSSIMO LIFECYCLE ({next_stage.value if next_stage else 'NESSUNO'}):
{chr(10).join(f"- {indicator}" for indicator in transition_indicators) if transition_indicators else "- Lifecycle finale raggiunto"}

FORMATO RISPOSTA RICHIESTO:
Devi rispondere SEMPRE in questo formato JSON:
{{
    "messages": "La tua risposta completa" OPPURE [
        {{"text": "Prima parte del messaggio", "delay_ms": 1000}},
        {{"text": "Seconda parte", "delay_ms": 2000}}
    ],
    "should_change_lifecycle": true/false,
    "new_lifecycle": "nome_lifecycle",
    "reasoning": "Spiegazione del perché hai deciso di cambiare o non cambiare lifecycle",
    "confidence": 0.0-1.0
}}

IMPORTANTE:
- Il campo "messages" può essere una stringa (risposta singola) o un array di oggetti
- Ogni oggetto nell'array ha "text" (il messaggio) e "delay_ms" (millisecondi di attesa prima del prossimo)
- Cambia lifecycle solo se sei sicuro al 70% o più (confidence >= 0.7)
- La risposta deve essere SEMPRE un JSON valido
"""

        return unified_prompt

    async def chat(self, session_id: str, user_message: str) -> LifecycleResponse:
        """
        Gestisce una conversazione completa con decisione automatica del lifecycle
        
        Args:
            session_id: ID della sessione di chat
            user_message: Messaggio dell'utente
            
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
                
                # GESTIONE SPECIALE: NUOVA_LEAD
                if session.current_lifecycle == LifecycleStage.NUOVA_LEAD:
                    return await self._handle_nuova_lead_special_case(session, user_message, db)
                
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
                
                ai_response = await self._call_ai_agent(unified_prompt)
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
                    full_logs=log_capture.get_session_logs_str()
                )
                    
            except Exception as e:
                log_capture.add_log("INFO", "ERROR: General error")
                logger.error(f"Errore generale nell'agente unificato: {e}")
                raise ChatbotError(f"Errore interno del chatbot: {str(e)}")

    async def _update_session_lifecycle(self, session: SessionModel, new_lifecycle: LifecycleStage, db: AsyncSession) -> None:
        """Aggiorna il lifecycle della sessione"""
        session.current_lifecycle = new_lifecycle
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

    def _get_next_actions(self, current_lifecycle: LifecycleStage) -> List[str]:
        """Genera le prossime azioni suggerite basate sul lifecycle corrente"""
        actions_map = {
            LifecycleStage.NUOVA_LEAD: [
                "Ascolta attivamente i problemi del cliente",
                "Fai domande per capire le sue esigenze specifiche",
                "Mostra empatia e comprensione"
            ],
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