"""
Modelli Pydantic per l'API
"""
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Modello per i messaggi del chat"""
    message: str
    user_id: str = "anonymous"
    session_id: Optional[str] = "default"
    model_name: Optional[str] = None  # Nome del modello AI selezionato
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Modello per le risposte del chat"""
    messages: Union[str, List[Dict[str, Union[str, int]]]]  # Stringa singola o lista di messaggi
    session_id: str
    current_lifecycle: str
    lifecycle_changed: bool = False
    previous_lifecycle: Optional[str] = None
    next_actions: List[str] = []
    ai_reasoning: Optional[str] = None
    confidence: float = 0.0
    debug_logs: Optional[List[str]] = None
    full_logs: Optional[str] = None
    timestamp: str
    is_conversation_finished: bool = False


class HealthCheck(BaseModel):
    """Modello per l'health check"""
    status: str
    version: str
    environment: str


class SystemPromptCreate(BaseModel):
    """Modello per creare un system prompt"""
    name: str
    content: str
    version: str = "1.0"
    description: Optional[str] = None


class SystemPromptUpdate(BaseModel):
    """Modello per aggiornare un system prompt"""
    name: Optional[str] = None
    content: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None