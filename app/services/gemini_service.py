"""
Servizio per l'integrazione con Gemini 2.5 Pro usando datapizza-ai
"""

from typing import Optional, Dict, Any
from loguru import logger

from datapizza.clients.google import GoogleClient
from datapizza.agents import Agent

from app.config import settings


class GeminiService:
    """Servizio per interagire con Gemini 2.5 Pro"""
    
    def __init__(self):
        """Inizializza il servizio Gemini"""
        self.client: Optional[GoogleClient] = None
        self.agent: Optional[Agent] = None
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
                model="gemini-2.5-pro"  # Usa il modello più recente disponibile
            )
            
            # Crea un agent con il client
            self.agent = Agent(
                name="gemini_assistant",
                client=self.client
            )
            
            logger.info("Client Gemini inizializzato correttamente")
            
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione del client Gemini: {e}")
            self.client = None
            self.agent = None
    
    async def chat(self, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invia un messaggio a Gemini e restituisce la risposta
        
        Args:
            message: Il messaggio da inviare
            context: Contesto opzionale per la conversazione
            
        Returns:
            Dict contenente la risposta e metadati
        """
        try:
            if not self.agent:
                return {
                    "success": False,
                    "error": "Client Gemini non inizializzato. Verificare la configurazione API key.",
                    "response": None
                }
            
            # Prepara il prompt con eventuale contesto
            prompt = message
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                prompt = f"Contesto:\n{context_str}\n\nDomanda: {message}"
            
            logger.info(f"Invio messaggio a Gemini: {message[:100]}...")
            
            # Invia il messaggio usando l'agent
            response = self.agent.run(prompt)
            
            logger.info("Risposta ricevuta da Gemini")
            
            return {
                "success": True,
                "response": response,
                "model": "gemini-2.5-pro",
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Errore nella chiamata a Gemini: {e}")
            return {
                "success": False,
                "error": str(e),
                "response": None
            }
    
    def is_available(self) -> bool:
        """Verifica se il servizio è disponibile"""
        return self.client is not None and self.agent is not None
    
    async def health_check(self) -> Dict[str, Any]:
        """Verifica lo stato del servizio"""
        if not self.is_available():
            return {
                "status": "unhealthy",
                "message": "Client Gemini non inizializzato",
                "api_key_configured": bool(settings.gemini_api_key)
            }
        
        try:
            # Test con un messaggio semplice
            test_response = await self.chat("Ciao, questo è un test di connessione.")
            
            if test_response["success"]:
                return {
                    "status": "healthy",
                    "message": "Servizio Gemini operativo",
                    "model": "gemini-2.5-pro"
                }
            else:
                return {
                    "status": "unhealthy",
                    "message": f"Errore nel test: {test_response['error']}"
                }
                
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Errore nel health check: {str(e)}"
            }


# Istanza globale del servizio
gemini_service = GeminiService()