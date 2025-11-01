"""
Modelli Pydantic per il sistema di lifecycle e snippet del chatbot
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class LifecycleStage(str, Enum):
    """Enum per i vari stage del lifecycle"""
    NUOVA_LEAD = "nuova_lead"
    CONTRASSEGNATO = "contrassegnato"
    IN_TARGET = "in_target"
    LINK_DA_INVIARE = "link_da_inviare"
    LINK_INVIATO = "link_inviato"
    PRENOTATO = "prenotato"


class ScriptSnippet(BaseModel):
    """Modello per uno snippet di script"""
    id: str = Field(..., description="ID univoco dello snippet")
    lifecycle_stage: LifecycleStage = Field(..., description="Stage del lifecycle associato")
    trigger_keywords: List[str] = Field(..., description="Parole chiave che attivano questo snippet")
    script_content: str = Field(..., description="Contenuto dello script da seguire")
    next_stage: Optional[LifecycleStage] = Field(None, description="Prossimo stage se completato")
    completion_indicators: List[str] = Field(..., description="Indicatori che segnalano il completamento")


class ConversationContext(BaseModel):
    """Contesto della conversazione con il cliente"""
    user_id: str = Field(..., description="ID dell'utente")
    current_lifecycle: LifecycleStage = Field(default=LifecycleStage.NUOVA_LEAD)
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    completed_snippets: List[str] = Field(default_factory=list)
    user_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class LifecycleTransition(BaseModel):
    """Modello per una transizione di lifecycle"""
    from_stage: LifecycleStage
    to_stage: LifecycleStage
    trigger_reason: str
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: str
    snippet_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Risposta del chatbot con informazioni sul lifecycle"""
    message: str = Field(..., description="Messaggio di risposta")
    current_lifecycle: LifecycleStage = Field(..., description="Lifecycle attuale")
    lifecycle_changed: bool = Field(default=False, description="Se il lifecycle è cambiato")
    next_actions: List[str] = Field(default_factory=list, description="Prossime azioni suggerite")
    completed_snippet: Optional[str] = Field(None, description="Snippet completato se presente")


class SystemPromptConfig(BaseModel):
    """Configurazione del prompt di sistema"""
    base_identity: str = Field(..., description="Identità base dell'agente")
    nutrition_expertise: str = Field(..., description="Competenze in nutrizione")
    psychology_expertise: str = Field(..., description="Competenze in psicologia")
    lifecycle_instructions: Dict[LifecycleStage, str] = Field(..., description="Istruzioni per ogni lifecycle")
    transition_rules: Dict[str, str] = Field(..., description="Regole per le transizioni")