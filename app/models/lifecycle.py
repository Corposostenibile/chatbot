"""
Modelli per la gestione dei lifecycle del chatbot
"""
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel


class LifecycleStage(str, Enum):
    """Enum per i vari stage del lifecycle"""
    NUOVA_LEAD = "nuova_lead"
    CONTRASSEGNATO = "contrassegnato"
    IN_TARGET = "in_target"
    LINK_DA_INVIARE = "link_da_inviare"
    LINK_INVIATO = "link_inviato"


class LifecycleTransition(BaseModel):
    """Modello per le transizioni tra lifecycle"""
    from_stage: LifecycleStage
    to_stage: LifecycleStage
    trigger_keywords: List[str]
    trigger_phrases: List[str]
    description: str


class ChatSession(BaseModel):
    """Modello per la sessione di chat con lifecycle"""
    session_id: str
    current_lifecycle: LifecycleStage = LifecycleStage.NUOVA_LEAD
    conversation_history: List[Dict[str, str]] = []
    user_info: Dict[str, str] = {}
    lifecycle_history: List[Dict[str, str]] = []


class LifecycleDecision(BaseModel):
    """Decisione del modello AI riguardo al lifecycle"""
    should_change_lifecycle: bool = False
    target_lifecycle: Optional[LifecycleStage] = None
    confidence_score: float = 0.0
    reasoning: str = ""


class AIResponse(BaseModel):
    """Risposta completa del modello AI con decisioni sul lifecycle"""
    message: str
    lifecycle_decision: LifecycleDecision


class LifecycleResponse(BaseModel):
    """Risposta del sistema con informazioni sul lifecycle"""
    messages: Union[str, List[Dict[str, Union[str, int]]]]  # Stringa singola o lista di messaggi con delay
    current_lifecycle: LifecycleStage
    lifecycle_changed: bool = False
    previous_lifecycle: Optional[LifecycleStage] = None
    next_actions: List[str] = []
    ai_reasoning: str = ""
    confidence: float = 0.0
    debug_logs: Optional[List[str]] = None
    full_logs: Optional[str] = None