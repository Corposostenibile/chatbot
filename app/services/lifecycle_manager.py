"""
Servizio per la gestione dei lifecycle e delle transizioni del chatbot
"""
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger

from app.models import (
    LifecycleStage, 
    ScriptSnippet, 
    ConversationContext, 
    LifecycleTransition,
    ChatResponse
)
from app.data.test_snippets import TEST_SNIPPETS, SYSTEM_PROMPT_CONFIG


class LifecycleManager:
    """Gestisce i lifecycle e le transizioni del chatbot"""
    
    def __init__(self):
        self.snippets: Dict[LifecycleStage, List[ScriptSnippet]] = {}
        self.conversations: Dict[str, ConversationContext] = {}
        self._load_snippets()
    
    def _load_snippets(self) -> None:
        """Carica gli snippet organizzandoli per lifecycle stage"""
        for snippet in TEST_SNIPPETS:
            if snippet.lifecycle_stage not in self.snippets:
                self.snippets[snippet.lifecycle_stage] = []
            self.snippets[snippet.lifecycle_stage].append(snippet)
        
        logger.info(f"Caricati {len(TEST_SNIPPETS)} snippet per {len(self.snippets)} lifecycle stages")
    
    def get_or_create_context(self, user_id: str) -> ConversationContext:
        """Ottiene o crea il contesto di conversazione per un utente"""
        if user_id not in self.conversations:
            self.conversations[user_id] = ConversationContext(
                user_id=user_id,
                current_lifecycle=LifecycleStage.NUOVA_LEAD
            )
            logger.info(f"Creato nuovo contesto per utente {user_id}")
        
        return self.conversations[user_id]
    
    def analyze_message_for_triggers(self, message: str, current_stage: LifecycleStage) -> Optional[ScriptSnippet]:
        """Analizza il messaggio per identificare trigger keywords"""
        message_lower = message.lower()
        
        # Cerca negli snippet del stage corrente
        if current_stage in self.snippets:
            for snippet in self.snippets[current_stage]:
                for keyword in snippet.trigger_keywords:
                    if keyword.lower() in message_lower:
                        logger.info(f"Trigger trovato: '{keyword}' per snippet {snippet.id}")
                        return snippet
        
        return None
    
    def check_completion_indicators(self, message: str, snippet: ScriptSnippet) -> bool:
        """Verifica se il messaggio contiene indicatori di completamento"""
        message_lower = message.lower()
        
        for indicator in snippet.completion_indicators:
            if indicator.lower() in message_lower:
                logger.info(f"Indicatore di completamento trovato: '{indicator}' per snippet {snippet.id}")
                return True
        
        return False
    
    def should_transition_lifecycle(self, context: ConversationContext, user_message: str) -> Optional[LifecycleStage]:
        """Determina se è necessaria una transizione di lifecycle"""
        current_snippets = self.snippets.get(context.current_lifecycle, [])
        
        # Prima verifica se ci sono snippet completati nel lifecycle corrente
        for snippet in current_snippets:
            if snippet.id in context.completed_snippets:
                continue
                
            # Verifica se il messaggio contiene indicatori di completamento
            if self.check_completion_indicators(user_message, snippet):
                if snippet.next_stage:
                    logger.info(f"Transizione richiesta da {context.current_lifecycle} a {snippet.next_stage}")
                    return snippet.next_stage
        
        # Se non ci sono completamenti, verifica i trigger per tutti i lifecycle
        for stage, snippets in self.snippets.items():
            if stage == context.current_lifecycle:
                continue  # Salta il lifecycle corrente
                
            for snippet in snippets:
                # Verifica se il messaggio contiene trigger keywords per questo snippet
                message_lower = user_message.lower()
                for trigger in snippet.trigger_keywords:
                    if trigger.lower() in message_lower:
                        logger.info(f"Trigger trovato '{trigger}' per transizione da {context.current_lifecycle} a {stage}")
                        return stage
        
        return None
    
    def transition_lifecycle(self, user_id: str, new_stage: LifecycleStage, reason: str, snippet_id: Optional[str] = None) -> LifecycleTransition:
        """Esegue una transizione di lifecycle"""
        context = self.get_or_create_context(user_id)
        old_stage = context.current_lifecycle
        
        # Crea la transizione
        transition = LifecycleTransition(
            from_stage=old_stage,
            to_stage=new_stage,
            trigger_reason=reason,
            user_id=user_id,
            snippet_id=snippet_id
        )
        
        # Aggiorna il contesto
        context.current_lifecycle = new_stage
        context.updated_at = datetime.now()
        
        logger.info(f"Transizione completata per utente {user_id}: {old_stage} -> {new_stage}")
        
        return transition
    
    def get_current_snippet(self, user_id: str) -> Optional[ScriptSnippet]:
        """Ottiene lo snippet appropriato per il lifecycle corrente"""
        context = self.get_or_create_context(user_id)
        current_snippets = self.snippets.get(context.current_lifecycle, [])
        
        # Trova il primo snippet non completato per questo stage
        for snippet in current_snippets:
            if snippet.id not in context.completed_snippets:
                return snippet
        
        return None
    
    def mark_snippet_completed(self, user_id: str, snippet_id: str) -> None:
        """Marca uno snippet come completato"""
        context = self.get_or_create_context(user_id)
        if snippet_id not in context.completed_snippets:
            context.completed_snippets.append(snippet_id)
            context.updated_at = datetime.now()
            logger.info(f"Snippet {snippet_id} marcato come completato per utente {user_id}")
    
    def get_system_prompt(self, user_id: str) -> str:
        """Genera il prompt di sistema basato sul lifecycle corrente"""
        context = self.get_or_create_context(user_id)
        current_snippet = self.get_current_snippet(user_id)
        
        base_prompt = f"""
{SYSTEM_PROMPT_CONFIG.base_identity}

COMPETENZE NUTRIZIONALI:
{SYSTEM_PROMPT_CONFIG.nutrition_expertise}

COMPETENZE PSICOLOGICHE:
{SYSTEM_PROMPT_CONFIG.psychology_expertise}

LIFECYCLE CORRENTE: {context.current_lifecycle.value}
ISTRUZIONI PER QUESTO STAGE: {SYSTEM_PROMPT_CONFIG.lifecycle_instructions.get(context.current_lifecycle, "")}

SNIPPET CORRENTE:
{current_snippet.script_content if current_snippet else "Nessuno snippet attivo"}

REGOLE IMPORTANTI:
- Mantieni sempre la tua identità di Sara
- Segui lo script ma adattalo naturalmente alla conversazione
- Identifica le parole chiave per le transizioni: {current_snippet.completion_indicators if current_snippet else []}
- Non saltare mai step del funnel
- Gestisci le obiezioni con empatia

SNIPPET COMPLETATI: {context.completed_snippets}
"""
        
        return base_prompt
    
    def process_conversation_turn(self, user_id: str, user_message: str, bot_response: str) -> ChatResponse:
        """Elabora un turno di conversazione completo"""
        context = self.get_or_create_context(user_id)
        initial_lifecycle = context.current_lifecycle
        
        # Aggiungi il messaggio alla cronologia
        context.conversation_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_response": bot_response,
            "lifecycle": context.current_lifecycle.value
        })
        
        # Verifica se è necessaria una transizione
        new_stage = self.should_transition_lifecycle(context, user_message)
        lifecycle_changed = False
        completed_snippet = None
        
        if new_stage:
            # Marca lo snippet corrente come completato
            current_snippet = self.get_current_snippet(user_id)
            if current_snippet:
                self.mark_snippet_completed(user_id, current_snippet.id)
                completed_snippet = current_snippet.id
            
            # Esegui la transizione
            self.transition_lifecycle(
                user_id=user_id,
                new_stage=new_stage,
                reason=f"Completamento snippet: {user_message[:50]}...",
                snippet_id=current_snippet.id if current_snippet else None
            )
            lifecycle_changed = True
        
        # Genera le prossime azioni suggerite
        next_actions = self._get_next_actions(user_id)
        
        return ChatResponse(
            message=bot_response,
            current_lifecycle=context.current_lifecycle,
            lifecycle_changed=lifecycle_changed,
            next_actions=next_actions,
            completed_snippet=completed_snippet
        )
    
    def _get_next_actions(self, user_id: str) -> List[str]:
        """Genera le prossime azioni suggerite basate sul lifecycle corrente"""
        context = self.get_or_create_context(user_id)
        current_snippet = self.get_current_snippet(user_id)
        
        if not current_snippet:
            return ["Conversazione completata"]
        
        actions = []
        
        # Azioni basate sul lifecycle corrente
        if context.current_lifecycle == LifecycleStage.NUOVA_LEAD:
            actions = ["Identificare il problema principale", "Creare rapport", "Qualificare il lead"]
        elif context.current_lifecycle == LifecycleStage.CONTRASSEGNATO:
            actions = ["Approfondire il problema", "Creare empatia", "Fare domande qualificanti"]
        elif context.current_lifecycle == LifecycleStage.IN_TARGET:
            actions = ["Presentare la soluzione", "Evidenziare i benefici", "Creare urgenza"]
        elif context.current_lifecycle == LifecycleStage.LINK_DA_INVIARE:
            actions = ["Inviare link presentazione", "Spiegare i contenuti", "Fissare follow-up"]
        elif context.current_lifecycle == LifecycleStage.LINK_INVIATO:
            actions = ["Verificare visione presentazione", "Proporre consulenza", "Fissare appuntamento"]
        elif context.current_lifecycle == LifecycleStage.PRENOTATO:
            actions = ["Confermare appuntamento", "Preparare il cliente", "Inviare promemoria"]
        
        return actions
    
    def get_lifecycle_stats(self, user_id: str) -> Dict:
        """Ottiene statistiche sul lifecycle per un utente"""
        context = self.get_or_create_context(user_id)
        
        return {
            "user_id": user_id,
            "current_lifecycle": context.current_lifecycle.value,
            "completed_snippets": len(context.completed_snippets),
            "total_snippets": len(TEST_SNIPPETS),
            "conversation_turns": len(context.conversation_history),
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat()
        }