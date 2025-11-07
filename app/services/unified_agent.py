"""
Agente unificato che gestisce conversazione e lifecycle management in un'unica chiamata AI
"""
import json
import time
from typing import Dict, Optional, List
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
import json as json_lib


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
                model="gemini-2.5-flash",
                temperature=0.7,
                system_prompt="Sei un assistente AI specializzato in nutrizione e psicologia."
            )
            
            # Inizializza l'agent
            self.agent = Agent(
                client=self.client,
                name="UnifiedChatbotAgent"
            )
            
            logger.info("UnifiedAgent inizializzato con successo")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di UnifiedAgent: {e}")
            raise

    async def get_or_create_session(self, session_id: str, db: AsyncSession) -> SessionModel:
        """Ottiene o crea una nuova sessione"""
        # Cerca la sessione esistente
        result = await db.execute(
            SessionModel.__table__.select().where(SessionModel.session_id == session_id)
        )
        session = result.first()
        
        if session:
            return session[0]
        
        # Crea una nuova sessione
        new_session = SessionModel(session_id=session_id)
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        logger.info(f"Nuova sessione creata: {session_id}")
        return new_session

    async def _build_conversation_context(self, session: SessionModel, db: AsyncSession) -> str:
        """Costruisce il contesto della conversazione dalla cronologia"""
        # Ottieni gli ultimi 10 messaggi (5 scambi)
        result = await db.execute(
            MessageModel.__table__.select()
            .where(MessageModel.session_id == session.id)
            .order_by(MessageModel.timestamp.desc())
            .limit(10)
        )
        messages = result.all()
        
        if not messages:
            return "Nessuna conversazione precedente."
        
        # Riordina cronologicamente
        messages = list(reversed(messages))
        
        context_lines = []
        for msg in messages:
            role = "UTENTE" if msg[0].role == "user" else "ASSISTENTE"
            context_lines.append(f"{role}: {msg[0].message}")
        
        return "\n".join(context_lines)

    async def _get_unified_prompt(self, session: SessionModel, user_message: str, db: AsyncSession) -> str:
        """Genera il prompt unificato che gestisce conversazione e lifecycle"""
        current_lifecycle = session.current_lifecycle
        current_config = LIFECYCLE_SCRIPTS.get(current_lifecycle, {})
        
        # Informazioni sul lifecycle corrente
        script_text = current_config.get("script", "")
        objective = current_config.get("objective", "")
        transition_indicators = current_config.get("transition_indicators", [])
        next_stage = current_config.get("next_stage")
        
        # Contesto conversazione
        conversation_context = await self._build_conversation_context(session, db)
        
        # Costruisci il prompt unificato
        unified_prompt = f"""Sei un assistente virtuale specializzato nel supportare persone interessate a percorsi di nutrizione e psicologia.

LA TUA IDENTITÀ:
- Sei empatico, professionale e orientato al risultato
- Non sei un nutrizionista o psicologo, ma un consulente che guida verso la soluzione giusta
- Il tuo obiettivo è far arrivare il cliente al lifecycle "Link Inviato"
- Mantieni sempre un tono caldo ma professionale

LIFECYCLE CORRENTE: {current_lifecycle.value.upper()}
OBIETTIVO CORRENTE: {objective}

SCRIPT GUIDA PER QUESTO LIFECYCLE:
{script_text}

CRONOLOGIA CONVERSAZIONE:
{conversation_context}

MESSAGGIO UTENTE: {user_message}

ISTRUZIONI:
1. Rispondi al messaggio dell'utente in modo naturale e utile
2. Usa il script come guida ma mantieni la conversazione fluida
3. Valuta se il messaggio dell'utente indica che è pronto per il prossimo lifecycle
4. NON menzionare mai i lifecycle al cliente

INDICATORI PER PASSARE AL PROSSIMO LIFECYCLE ({next_stage.value if next_stage else 'NESSUNO'}):
{chr(10).join(f"- {indicator}" for indicator in transition_indicators) if transition_indicators else "- Lifecycle finale raggiunto"}

FORMATO RISPOSTA RICHIESTO:
Devi rispondere SEMPRE in questo formato JSON:

{{
    "message": "La tua risposta conversazionale al cliente",
    "should_change_lifecycle": true/false,
    "new_lifecycle": "{next_stage.value if next_stage else current_lifecycle.value}",
    "reasoning": "Spiegazione del perché hai deciso di cambiare o non cambiare lifecycle",
    "confidence": 0.0-1.0
}}

IMPORTANTE: 
- Il campo "message" deve contenere la tua risposta naturale al cliente
- Cambia lifecycle solo se sei sicuro al 70% o più (confidence >= 0.7)
- Se non ci sono più lifecycle successivi, mantieni quello corrente
- La risposta deve essere SEMPRE un JSON valido

RISPOSTA:"""

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
        async for db in get_db():
            try:
                # Ottieni o crea la sessione
                session = await self.get_or_create_session(session_id, db)
                previous_lifecycle = session.current_lifecycle
                
                # Genera il prompt unificato
                unified_prompt = await self._get_unified_prompt(session, user_message, db)
                logger.info("-------------------------------------------------")
                logger.info(f"Prompt unificato per sessione {session_id}:\n{unified_prompt}")
                logger.info("-------------------------------------------------")
                
                # Invia il messaggio all'AI
                logger.info(f"Invio messaggio unificato per sessione {session_id}")
                
                try:
                    ai_result = await self.agent.a_run(unified_prompt)
                    ai_response = ai_result.text
                    logger.info(f"Risposta AI ricevuta per sessione {session_id}")
                except Exception as ai_error:
                    logger.error(f"Errore con l'AI: {ai_error}")
                    # Fallback response
                    return await self._create_fallback_response(session_id, user_message, previous_lifecycle, db)
                
                # Parsing della risposta JSON
                try:
                    # Pulisci la risposta da eventuali markdown
                    cleaned_response = ai_response.strip()
                    if cleaned_response.startswith("```json"):
                        cleaned_response = cleaned_response[7:]
                    if cleaned_response.endswith("```"):
                        cleaned_response = cleaned_response[:-3]
                    cleaned_response = cleaned_response.strip()
                    
                    response_data = json.loads(cleaned_response)
                    
                    # Estrai i dati dalla risposta
                    message = response_data.get("message", "Ciao! Come posso aiutarti oggi?")
                    should_change = response_data.get("should_change_lifecycle", False)
                    new_lifecycle_str = response_data.get("new_lifecycle", session.current_lifecycle.value)
                    reasoning = response_data.get("reasoning", "Risposta automatica")
                    confidence = response_data.get("confidence", 0.5)
                    
                    # Determina il nuovo lifecycle
                    lifecycle_changed = False
                    new_lifecycle = session.current_lifecycle
                    
                    if should_change and confidence >= 0.7:
                        try:
                            new_lifecycle = LifecycleStage(new_lifecycle_str)
                            if new_lifecycle != session.current_lifecycle:
                                await self._update_session_lifecycle(session, new_lifecycle, db)
                                lifecycle_changed = True
                                logger.info(f"Sessione {session_id}: {previous_lifecycle.value} → {new_lifecycle.value}")
                        except ValueError:
                            logger.warning(f"Lifecycle non valido: {new_lifecycle_str}")
                    
                    # Aggiungi il messaggio alla cronologia
                    await self._add_to_conversation_history(session, user_message, message, db)
                    
                    # Genera next actions
                    next_actions = self._get_next_actions(new_lifecycle)
                    
                    return LifecycleResponse(
                        message=message,
                        current_lifecycle=new_lifecycle,
                        lifecycle_changed=lifecycle_changed,
                        previous_lifecycle=previous_lifecycle if lifecycle_changed else None,
                        next_actions=next_actions,
                        ai_reasoning=reasoning
                    )
                    
                except json.JSONDecodeError as json_error:
                    logger.error(f"Errore nel parsing JSON: {json_error}")
                    logger.error(f"Risposta AI: {ai_response}")
                    return await self._create_fallback_response(session_id, user_message, previous_lifecycle, db)
                    
            except Exception as e:
                logger.error(f"Errore generale nell'agente unificato: {e}")
                return await self._create_fallback_response(session_id, user_message, previous_lifecycle, db)

    async def _create_fallback_response(self, session_id: str, user_message: str, current_lifecycle: LifecycleStage, db: AsyncSession) -> LifecycleResponse:
        """Crea una risposta di fallback quando l'AI non è disponibile"""
        session = await self.get_or_create_session(session_id, db)
        
        fallback_messages = {
            LifecycleStage.NUOVA_LEAD: "Ciao! Sono qui per aiutarti con il tuo percorso di benessere. Come posso supportarti oggi?",
            LifecycleStage.CONTRASSEGNATO: "Capisco la tua situazione. Parlami di più di quello che stai vivendo.",
            LifecycleStage.IN_TARGET: "È normale sentirsi così. Il nostro approccio integrato di nutrizione e psicologia può davvero aiutarti.",
            LifecycleStage.LINK_DA_INVIARE: "Perfetto! Ti piacerebbe saperne di più sulla nostra consulenza gratuita?",
            LifecycleStage.LINK_INVIATO: "Grazie per il tuo interesse! Ti ho inviato il link per prenotare la tua consulenza gratuita."
        }
        
        message = fallback_messages.get(current_lifecycle, "Grazie per il tuo messaggio. Come posso aiutarti?")
        
        # Aggiungi alla cronologia
        await self._add_to_conversation_history(session, user_message, message, db)
        
        return LifecycleResponse(
            message=message,
            current_lifecycle=current_lifecycle,
            lifecycle_changed=False,
            next_actions=self._get_next_actions(current_lifecycle),
            ai_reasoning="Risposta di fallback - AI non disponibile"
        )

    async def _update_session_lifecycle(self, session: SessionModel, new_lifecycle: LifecycleStage, db: AsyncSession) -> None:
        """Aggiorna il lifecycle della sessione"""
        session.current_lifecycle = new_lifecycle
        await db.commit()

    async def _add_to_conversation_history(self, session: SessionModel, user_message: str, ai_response: str, db: AsyncSession) -> None:
        """Aggiunge i messaggi alla cronologia della conversazione"""
        from datetime import datetime
        
        # Aggiungi messaggio utente
        user_msg = MessageModel(
            session_id=session.id,
            role="user",
            message=user_message,
            timestamp=datetime.utcnow()
        )
        db.add(user_msg)
        
        # Aggiungi risposta AI
        ai_msg = MessageModel(
            session_id=session.id,
            role="assistant",
            message=ai_response,
            timestamp=datetime.utcnow()
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
                SessionModel.__table__.select().where(SessionModel.session_id == session_id)
            )
            session_row = result.first()
            if not session_row:
                return None
            
            session = session_row[0]
            
            # Conta i messaggi
            result = await db.execute(
                MessageModel.__table__.select().where(MessageModel.session_id == session.id)
            )
            message_count = len(result.all())
            
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
            return self.agent is not None and self.client is not None
        except:
            return False

    async def health_check(self) -> Dict[str, str]:
        """Esegue un health check del servizio"""
        try:
            # Test semplice con l'AI
            test_result = await self.agent.a_run("Rispondi solo con 'OK'")
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