"""
Servizio per l'integrazione con Gemini tramite datapizza-ai
"""
import asyncio
from typing import Dict, Optional
from loguru import logger

from datapizza.clients.google import GoogleClient
from datapizza.agents import Agent

from app.models.lifecycle import LifecycleStage, LifecycleResponse
from app.services.lifecycle_manager import lifecycle_manager
from app.config import settings


class GeminiService:
    """Servizio per l'integrazione con Gemini"""
    
    def __init__(self):
        """Inizializza il servizio Gemini"""
        try:
            # Verifica che l'API key sia configurata
            if not settings.google_ai_api_key:
                raise ValueError("GOOGLE_AI_API_KEY non configurata nel file .env")
            
            # Inizializza il client Google direttamente con i parametri
            self.client = GoogleClient(
                api_key=settings.google_ai_api_key,
                model="gemini-2.5-flash",
                temperature=0.7,
                system_prompt="Sei un assistente AI utile e professionale."
            )
            
            # Inizializza l'agent
            self.agent = Agent(
                client=self.client,
                name="ChatbotAgent"
            )
            
            logger.info("GeminiService inizializzato con successo")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione di GeminiService: {e}")
            raise

    async def chat(self, session_id: str, user_message: str) -> LifecycleResponse:
        """
        Gestisce una conversazione con Gemini e il lifecycle management
        
        Args:
            session_id: ID della sessione di chat
            user_message: Messaggio dell'utente
            
        Returns:
            LifecycleResponse con la risposta e informazioni sul lifecycle
        """
        try:
            # Ottieni o crea la sessione
            session = lifecycle_manager.get_or_create_session(session_id)
            
            # Genera il prompt di sistema per il lifecycle corrente
            system_prompt = lifecycle_manager.get_system_prompt(session.current_lifecycle)
            
            # Costruisci il contesto della conversazione
            conversation_context = self._build_conversation_context(session)
            
            # Costruisci il prompt completo
            full_prompt = f"""{system_prompt}

CRONOLOGIA CONVERSAZIONE:
{conversation_context}

MESSAGGIO UTENTE: {user_message}

RISPOSTA ASSISTENTE:"""

            # Invia il messaggio a Gemini
            logger.info(f"Invio messaggio a Gemini per sessione {session_id}")
            try:
                gemini_result = await self.agent.a_run(full_prompt)
                gemini_response = gemini_result.text  # Estrai il testo dalla risposta
                logger.info(f"Risposta Gemini ricevuta per sessione {session_id}")
            except Exception as gemini_error:
                logger.error(f"Errore specifico con Gemini agent: {gemini_error}")
                raise gemini_error
            
            # Processa la risposta attraverso il lifecycle manager
            try:
                lifecycle_response = await lifecycle_manager.get_lifecycle_response(
                    session_id=session_id,
                    user_message=user_message,
                    ai_response=gemini_response,
                    ai_client=self.agent  # Passa l'agent per l'analisi dinamica
                )
                logger.info(f"Lifecycle response processata per sessione {session_id}")
            except Exception as lifecycle_error:
                logger.error(f"Errore specifico nel lifecycle manager: {lifecycle_error}")
                raise lifecycle_error
            
            logger.info(f"Risposta generata per sessione {session_id}, lifecycle: {lifecycle_response.current_lifecycle}")
            
            return lifecycle_response
            
        except Exception as e:
            logger.error(f"Errore nel chat con Gemini: {e}")
            # Risposta di fallback
            return LifecycleResponse(
                message="Mi dispiace, si è verificato un errore. Puoi riprovare?",
                current_lifecycle=LifecycleStage.NUOVA_LEAD,
                lifecycle_changed=False,
                ai_reasoning="Errore nel servizio AI"
            )

    def _build_conversation_context(self, session) -> str:
        """Costruisce il contesto della conversazione dalla cronologia"""
        if not session.conversation_history:
            return "Nessuna conversazione precedente."
        
        context_lines = []
        # Prendi solo gli ultimi 5 scambi per non sovraccaricare il prompt
        recent_history = session.conversation_history[-5:]
        
        for i, exchange in enumerate(recent_history, 1):
            context_lines.append(f"Scambio {i}:")
            context_lines.append(f"Utente: {exchange['user']}")
            context_lines.append(f"Assistente: {exchange['assistant']}")
            if exchange.get('lifecycle_changed'):
                context_lines.append(f"[Lifecycle cambiato a: {exchange['lifecycle']}]")
            context_lines.append("")
        
        return "\n".join(context_lines)

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Restituisce informazioni sulla sessione"""
        return lifecycle_manager.get_session_info(session_id)

    def is_available(self) -> bool:
        """Controlla se il servizio è disponibile"""
        try:
            return self.client is not None and self.agent is not None
        except Exception:
            return False

    async def health_check(self) -> Dict[str, str]:
        """Esegue un controllo di salute del servizio"""
        try:
            # Test semplice con Gemini
            test_result = await self.agent.a_run("Rispondi solo con 'OK' se funzioni correttamente.")
            test_response = test_result.text  # Estrai il testo dalla risposta
            
            if "OK" in test_response.upper():
                return {"status": "healthy", "message": "Servizio Gemini operativo"}
            else:
                return {"status": "degraded", "message": "Risposta inaspettata da Gemini"}
                
        except Exception as e:
            logger.error(f"Health check fallito: {e}")
            return {"status": "unhealthy", "message": f"Errore: {str(e)}"}


# Istanza globale del servizio
gemini_service = GeminiService()