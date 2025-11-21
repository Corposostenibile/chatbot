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
    batch_wait_seconds: Optional[int] = None  # Numero di secondi da aspettare per aggregare messaggi (opzionale)


class ChatResponse(BaseModel):
    """Modello per le risposte del chat"""
    messages: Union[str, List[Dict[str, Union[str, int]]]]  # Stringa singola o lista di messaggi
    session_id: str
    current_lifecycle: str
    lifecycle_changed: bool = False
    previous_lifecycle: Optional[str] = None
    # `next_actions` removed: this feature was deprecated — see PR notes
    ai_reasoning: Optional[str] = None
    confidence: float = 0.0
    timestamp: str
    is_conversation_finished: bool = False
    requires_human: bool = False
    human_task: Optional[Dict[str, Any]] = None


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


class HumanTaskCreate(BaseModel):
    """Modello per creare una human task via API"""
    title: str
    description: str
    session_id: Optional[str] = None
    assigned_to: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class HumanTaskUpdate(BaseModel):
    """Modello per aggiornare una human task (es. completarla)"""
    completed: Optional[bool] = None
    status: Optional[str] = None


class MessageNoteCreate(BaseModel):
    """Model to create a message note/rating"""
    message_id: int
    rating: int
    note: Optional[str] = None
    created_by: Optional[str] = None


class MessageNoteResponse(BaseModel):
    """Model to return message note information"""
    id: int
    message_id: int
    session_id: Optional[int]
    rating: int
    note: Optional[str]
    created_by: Optional[str]
    created_at: str


class MessageNoteUpdate(BaseModel):
    """Model to update a message note"""
    rating: Optional[int] = None
    note: Optional[str] = None


class SessionNoteCreate(BaseModel):
    """Model to create a session note"""
    session_id: str
    note: str


class SessionNoteResponse(BaseModel):
    """Model to return session note information"""
    id: int
    session_id: int
    note: str
    created_at: str
    updated_at: str


class SessionNoteUpdate(BaseModel):
    """Model to update a session note"""
    note: Optional[str] = None
