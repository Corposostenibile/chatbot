"""Servizio per l'integrazione con Gemini AI tramite datapizza-ai"""

from typing import Optional, Dict, Any
from loguru import logger

from datapizza.clients.google import GoogleClient
from datapizza.agents import Agent

from app.config import settings
from app.services.lifecycle_manager import LifecycleManager
from app.models import ChatResponse


class GeminiService:
    """Servizio per gestire le interazioni con Gemini AI"""
    
    def __init__(self):
        self.client: Optional[GoogleClient] = None
        self.agent: Optional[Agent] = None
        self.lifecycle_manager = LifecycleManager()
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Inizializza il client Gemini"""
        try:
            if not settings.google_ai_api_key:
                logger.warning("Google AI API key non configurata (GOOGLE_AI_API_KEY)")
                return
            
            # Inizializza il client Google con datapizza-ai
            self.client = GoogleClient(
                api_key=settings.google_ai_api_key,
                model="gemini-2.0-flash-exp"  # Usa il modello più recente disponibile
            )
            
            # Crea un agent con il client
            self.agent = Agent(
                name="sara_nutrition_coach",
                client=self.client
            )
            
            logger.info("Client Gemini inizializzato correttamente")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione del client Gemini: {e}")
            self.client = None
            self.agent = None
    
    def is_available(self) -> bool:
        """Verifica se il servizio Gemini è disponibile"""
        return self.client is not None and self.agent is not None
    
    async def chat_with_lifecycle(self, user_id: str, message: str, context: Optional[Dict[str, Any]] = None) -> ChatResponse:
        """
        Gestisce una conversazione con Gemini includendo la logica dei lifecycle
        """
        if not self.is_available():
            raise Exception("Servizio Gemini non disponibile")
        
        try:
            # Ottieni il prompt di sistema basato sul lifecycle corrente
            system_prompt = self.lifecycle_manager.get_system_prompt(user_id)
            
            # Ottieni il contesto della conversazione
            conversation_context = self.lifecycle_manager.get_or_create_context(user_id)
            
            # Prepara il messaggio con contesto
            full_message = f"""
CONTESTO CONVERSAZIONE:
- Lifecycle corrente: {conversation_context.current_lifecycle.value}
- Snippet completati: {len(conversation_context.completed_snippets)}
- Turni di conversazione: {len(conversation_context.conversation_history)}

MESSAGGIO UTENTE: {message}
"""
            
            # Invia il messaggio a Gemini con il prompt di sistema
            response = self.agent.run(task_input=full_message)
            
            # Estrai il testo dalla risposta
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Elabora la risposta attraverso il lifecycle manager
            chat_response = self.lifecycle_manager.process_conversation_turn(
                user_id=user_id,
                user_message=message,
                bot_response=response_text
            )
            
            logger.info(f"Risposta Gemini elaborata per utente {user_id}, lifecycle: {chat_response.current_lifecycle}")
            
            return chat_response
            
        except Exception as e:
            logger.error(f"Errore nella chat con Gemini: {e}")
            raise
    
    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Metodo di compatibilità per chat semplice senza lifecycle
        """
        if not self.is_available():
            raise Exception("Servizio Gemini non disponibile")
        
        try:
            # Usa il metodo corretto dell'agent
            response = self.agent.run(task_input=message)
            logger.info("Risposta Gemini ricevuta (modalità semplice)")
            return response.text if hasattr(response, 'text') else str(response)
            
        except Exception as e:
            logger.error(f"Errore nella chat semplice con Gemini: {e}")
            return f"Errore: {str(e)}"
    
    def get_lifecycle_stats(self, user_id: str) -> Dict[str, Any]:
        """Ottiene le statistiche del lifecycle per un utente"""
        return self.lifecycle_manager.get_lifecycle_stats(user_id)
    
    def get_current_lifecycle(self, user_id: str) -> str:
        """Ottiene il lifecycle corrente per un utente"""
        context = self.lifecycle_manager.get_or_create_context(user_id)
        return context.current_lifecycle.value
    
    def reset_user_context(self, user_id: str) -> bool:
        """Reset del contesto di un utente (per test)"""
        try:
            if user_id in self.lifecycle_manager.conversations:
                del self.lifecycle_manager.conversations[user_id]
                logger.info(f"Contesto resettato per utente {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Errore nel reset del contesto per {user_id}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Verifica lo stato di salute del servizio"""
        try:
            if not self.is_available():
                return {
                    "status": "unhealthy",
                    "message": "Client Gemini non inizializzato",
                    "lifecycle_manager": "active" if self.lifecycle_manager else "inactive"
                }
            
            # Test rapido del client
            # Nota: questo è un test sincrono, in produzione potresti voler fare un test asincrono
            return {
                "status": "healthy",
                "message": "Servizio Gemini operativo",
                "model": "gemini-2.0-flash-exp",
                "lifecycle_manager": "active",
                "loaded_snippets": len(self.lifecycle_manager.snippets),
                "active_conversations": len(self.lifecycle_manager.conversations)
            }
            
        except Exception as e:
            logger.error(f"Errore nel health check: {e}")
            return {
                "status": "error",
                "message": f"Errore nel health check: {str(e)}",
                "lifecycle_manager": "unknown"
            }


# Istanza globale del servizio
gemini_service = GeminiService()