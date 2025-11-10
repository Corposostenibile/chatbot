"""
Modelli Pydantic per l'API
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Modello per i messaggi del chat"""
    message: str
    user_id: str = "anonymous"
    session_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Modello per le risposte del chat"""
    response: str
    session_id: str
    current_lifecycle: str
    lifecycle_changed: bool = False
    previous_lifecycle: Optional[str] = None
    next_actions: List[str] = []
    ai_reasoning: Optional[str] = None
    debug_logs: Optional[List[str]] = None
    full_logs: Optional[str] = None
    timestamp: str


class HealthCheck(BaseModel):
    """Modello per l'health check"""
    status: str
    version: str
    environment: str