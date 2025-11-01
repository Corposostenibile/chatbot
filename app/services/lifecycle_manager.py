"""
Gestione dei lifecycle del chatbot con sistema dinamico basato su AI
"""
import json
import time
from typing import Dict, Optional, Tuple, List
from loguru import logger

from datapizza.clients.google import GoogleClient
from datapizza.agents import Agent

from app.models.lifecycle import (
    LifecycleStage, 
    ChatSession, 
    LifecycleResponse,
    LifecycleDecision,
    AIResponse
)
from app.data.lifecycle_config import (
    SYSTEM_PROMPT, 
    LIFECYCLE_SCRIPTS,
    LIFECYCLE_DECISION_PROMPT
)
from app.config import settings


class LifecycleManager:
    """Gestisce i lifecycle delle conversazioni del chatbot"""
    
    def __init__(self):
        """Inizializza il LifecycleManager con le sessioni e un client AI separato"""
        self.sessions: Dict[str, ChatSession] = {}
        
        # Crea un client AI separato per il lifecycle manager
        try:
            self.lifecycle_client = GoogleClient(
                api_key=settings.google_ai_api_key,
                model="gemini-2.5-flash",
                temperature=0.3,  # Temperatura più bassa per decisioni più consistenti
                system_prompt="Sei un analista AI specializzato nell'analisi di transizioni di lifecycle per chatbot di vendita."
            )
            
            self.lifecycle_agent = Agent(
                client=self.lifecycle_client,
                name="LifecycleAnalyzer"
            )
            
            logger.info("LifecycleManager inizializzato con client AI separato")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione del client AI per LifecycleManager: {e}")
            self.lifecycle_client = None
            self.lifecycle_agent = None

    def get_or_create_session(self, session_id: str) -> ChatSession:
        """Ottiene o crea una nuova sessione"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(session_id=session_id)
            logger.info(f"Nuova sessione creata: {session_id}")
        return self.sessions[session_id]

    def get_system_prompt(self, current_lifecycle: LifecycleStage) -> str:
        """Genera il prompt di sistema completo per il lifecycle corrente"""
        base_prompt = SYSTEM_PROMPT
        
        # Aggiungi informazioni specifiche del lifecycle corrente
        current_script = LIFECYCLE_SCRIPTS.get(current_lifecycle, {})
        script_text = current_script.get("script", "")
        objective = current_script.get("objective", "")
        
        lifecycle_prompt = f"""
        
LIFECYCLE CORRENTE: {current_lifecycle.value.upper()}

OBIETTIVO CORRENTE: {objective}

SCRIPT PER QUESTO LIFECYCLE:
{script_text}

ISTRUZIONI SPECIFICHE:
- Usa questo script come guida per la conversazione
- Mantieni un tono naturale e conversazionale
- Non copiare il script letteralmente, ma usalo come ispirazione
- Concentrati sul raggiungere l'obiettivo del lifecycle corrente
- Se il cliente fa domande specifiche, rispondi sempre in modo utile
- NON menzionare mai esplicitamente i lifecycle al cliente
"""
        
        return base_prompt + lifecycle_prompt

    async def analyze_lifecycle_transition(self, session: ChatSession, user_message: str, ai_client=None) -> LifecycleDecision:
        """Analizza se è necessaria una transizione di lifecycle usando l'AI"""
        current_stage = session.current_lifecycle
        current_config = LIFECYCLE_SCRIPTS.get(current_stage, {})
        
        # Se siamo nell'ultimo stage, non c'è transizione possibile
        if current_config.get("next_stage") is None:
            return LifecycleDecision(
                should_change_lifecycle=False,
                reasoning="Lifecycle finale raggiunto"
            )
        
        # Usa il client AI separato se disponibile, altrimenti fallback
        if self.lifecycle_agent is None:
            logger.warning("Client AI per lifecycle non disponibile, uso fallback")
            return self._fallback_analysis(current_stage, user_message)
        
        # Prepara il prompt per l'analisi
        decision_prompt = LIFECYCLE_DECISION_PROMPT.format(
            current_lifecycle=current_stage.value,
            current_objective=current_config.get("objective", ""),
            transition_indicators="\n".join(f"- {indicator}" for indicator in current_config.get("transition_indicators", [])),
            next_stage=current_config.get("next_stage").value if current_config.get("next_stage") else "Nessuno",
            user_message=user_message
        )
        
        try:
            # Usa il client AI separato con 'a_stream_invoke'
            logger.info(f"Usando client AI separato per l'analisi del lifecycle")
            full_response = ""
            async for chunk in self.lifecycle_agent.a_stream_invoke(decision_prompt):
                if hasattr(chunk, 'text') and chunk.text:
                    full_response += chunk.text
            
            response = full_response
            
            # Pulisci la risposta dai blocchi markdown se presenti
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Rimuovi ```json
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Rimuovi ```
            cleaned_response = cleaned_response.strip()
            
            # Prova a parsare la risposta JSON
            try:
                decision_data = json.loads(cleaned_response)
                
                target_lifecycle = None
                if decision_data.get("should_change_lifecycle") and decision_data.get("target_lifecycle"):
                    try:
                        target_lifecycle = LifecycleStage(decision_data["target_lifecycle"])
                    except ValueError:
                        # Se il lifecycle non è valido, usa quello configurato
                        target_lifecycle = current_config.get("next_stage")
                
                return LifecycleDecision(
                    should_change_lifecycle=decision_data.get("should_change_lifecycle", False),
                    target_lifecycle=target_lifecycle,
                    confidence_score=decision_data.get("confidence_score", 0.0),
                    reasoning=decision_data.get("reasoning", "Nessuna spiegazione fornita")
                )
                
            except json.JSONDecodeError:
                logger.warning(f"Risposta AI non in formato JSON valido: {cleaned_response}")
                # Fallback: analisi semplice basata su parole chiave
                return self._fallback_analysis(current_stage, user_message)
                
        except Exception as e:
            logger.error(f"Errore nell'analisi AI del lifecycle con 'a_stream_invoke': {e}")
            return self._fallback_analysis(current_stage, user_message)

    def _fallback_analysis(self, current_stage: LifecycleStage, user_message: str) -> LifecycleDecision:
        """Analisi di fallback semplice basata su parole chiave"""
        user_message_lower = user_message.lower()
        
        # Parole chiave positive generiche
        positive_keywords = ["sì", "si", "certo", "assolutamente", "perfetto", "va bene", "ok", "d'accordo"]
        
        if any(keyword in user_message_lower for keyword in positive_keywords):
            current_config = LIFECYCLE_SCRIPTS.get(current_stage, {})
            next_stage = current_config.get("next_stage")
            
            if next_stage:
                return LifecycleDecision(
                    should_change_lifecycle=True,
                    target_lifecycle=next_stage,
                    confidence_score=0.6,
                    reasoning="Fallback: rilevata risposta positiva generica"
                )
        
        return LifecycleDecision(
            should_change_lifecycle=False,
            confidence_score=0.3,
            reasoning="Fallback: nessun indicatore chiaro di transizione"
        )

    async def get_lifecycle_response(self, session_id: str, user_message: str, ai_response: str, ai_client) -> LifecycleResponse:
        """Processa un messaggio e restituisce la risposta con informazioni sul lifecycle"""
        session = self.get_or_create_session(session_id)
        
        # Analizza se c'è una transizione di lifecycle
        lifecycle_decision = await self.analyze_lifecycle_transition(session, user_message, ai_client)
        
        lifecycle_changed = False
        previous_lifecycle = None
        
        if lifecycle_decision.should_change_lifecycle and lifecycle_decision.target_lifecycle:
            if lifecycle_decision.confidence_score >= 0.7:  # Soglia di confidenza
                previous_lifecycle = session.current_lifecycle
                self.update_session_lifecycle(session, lifecycle_decision.target_lifecycle)
                lifecycle_changed = True
                logger.info(f"Lifecycle cambiato da {previous_lifecycle} a {session.current_lifecycle} (confidenza: {lifecycle_decision.confidence_score})")
        
        # Aggiungi il messaggio alla cronologia
        session.conversation_history.append({
            "user": user_message,
            "assistant": ai_response,
            "lifecycle": session.current_lifecycle.value,
            "lifecycle_changed": lifecycle_changed
        })
        
        # Determina le prossime azioni
        next_actions = self._get_next_actions(session.current_lifecycle)
        
        return LifecycleResponse(
            message=ai_response,
            current_lifecycle=session.current_lifecycle,
            lifecycle_changed=lifecycle_changed,
            previous_lifecycle=previous_lifecycle,
            next_actions=next_actions,
            ai_reasoning=lifecycle_decision.reasoning
        )
    
    def update_session_lifecycle(self, session: ChatSession, new_lifecycle: LifecycleStage) -> None:
        """Aggiorna il lifecycle di una sessione"""
        old_lifecycle = session.current_lifecycle
        session.current_lifecycle = new_lifecycle
        
        # Aggiungi alla cronologia dei lifecycle
        session.lifecycle_history.append({
            "from": old_lifecycle.value,
            "to": new_lifecycle.value,
            "timestamp": str(int(time.time()))
        })
        
        logger.info(f"Lifecycle aggiornato da {old_lifecycle} a {new_lifecycle}")

    def _get_next_actions(self, current_lifecycle: LifecycleStage) -> List[str]:
        """Restituisce le prossime azioni suggerite per il lifecycle corrente"""
        actions_map = {
            LifecycleStage.NUOVA_LEAD: [
                "Raccogli informazioni sui problemi del cliente",
                "Mostra empatia e comprensione",
                "Fai domande aperte sui suoi bisogni"
            ],
            LifecycleStage.CONTRASSEGNATO: [
                "Approfondisci la motivazione del cliente",
                "Chiedi quanto è importante per lui risolvere il problema",
                "Valuta il livello di urgenza (scala 1-10)"
            ],
            LifecycleStage.IN_TARGET: [
                "Presenta i benefici del percorso integrato",
                "Spiega l'approccio nutrizione + psicologia",
                "Introduci la consulenza gratuita"
            ],
            LifecycleStage.LINK_DA_INVIARE: [
                "Spiega cosa succede nella consulenza gratuita",
                "Rassicura che è senza impegno",
                "Chiedi conferma per l'invio del link"
            ],
            LifecycleStage.LINK_INVIATO: [
                "Obiettivo raggiunto!",
                "Fornisci supporto per la prenotazione se necessario"
            ]
        }
        
        return actions_map.get(current_lifecycle, [])

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Restituisce informazioni sulla sessione"""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return {
            "session_id": session_id,
            "current_lifecycle": session.current_lifecycle.value,
            "conversation_turns": len(session.conversation_history),
            "lifecycle_history": session.lifecycle_history
        }


# Istanza globale del manager
lifecycle_manager = LifecycleManager()