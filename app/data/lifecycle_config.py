"""
Configurazione dei lifecycle e script per il chatter di nutrizione e psicologia
"""
from typing import Dict, List, Any
from app.models.lifecycle import LifecycleStage
from app.data.snippets import (
    LEVEL_2_SNIPPETS, LEVEL_3_SNIPPETS, LEVEL_4_SNIPPETS, LEVEL_5_SNIPPETS,
    GENERIC_SNIPPETS, GENERIC_MESSAGES, get_snippet
)


# Configurazione degli script per ogni lifecycle (senza triggers_to_next)
LIFECYCLE_SCRIPTS: Dict[LifecycleStage, Dict] = {
    LifecycleStage.NUOVA_LEAD: {
        "script": """
        Ciao! Grazie di avermi scritto! 
        
        Questo è un messaggio automatico che ho scritto personalmente per riuscire a ringraziarti subito della fiducia!🙏
        
        Come sai ricevo centinaia di richieste ogni giorno e ci tengo a dedicarti personalmente l'attenzione che meriti.
        """,
        "next_stage": LifecycleStage.CONTRASSEGNATO,
        "objective": "Ringraziare e raccogliere informazioni base: nome, obiettivo specifico, tentativi passati, età",
        "transition_indicators": [
            "Appena l'utente scrive per primo, ad es: Ciao! Ti ho visto su Facebook, volevo maggiori informazioni",
        ],
        "available_snippets": GENERIC_MESSAGES
    },
    
    LifecycleStage.CONTRASSEGNATO: {
        "script": list(LEVEL_2_SNIPPETS.values()),
        "next_stage": LifecycleStage.IN_TARGET,
        "objective": "Approfondire le informazioni e confermare interesse",
        "transition_indicators": [
            "Hai tutte le informazioni necessarie (nome, obiettivo, età)",
            "Il cliente ha confermato interesse a proseguire",
            "Il cliente ha fornito dettagli aggiuntivi sul suo obiettivo"
        ],
        "available_snippets": {**GENERIC_MESSAGES, **GENERIC_SNIPPETS}
    },
    
    LifecycleStage.IN_TARGET: {
        "script": list(LEVEL_3_SNIPPETS.values()),
        "next_stage": LifecycleStage.LINK_DA_INVIARE,
        "objective": "Presentare i benefici del percorso integrato e introdurre la consulenza gratuita",
        "transition_indicators": [
            "Il cliente ha mostrato interesse per la consulenza gratuita",
            "Il cliente ha fatto domande sui servizi",
            "Il cliente ha confermato di voler saperne di più"
        ],
        "available_snippets": {**GENERIC_MESSAGES, **GENERIC_SNIPPETS}
    },
    
    LifecycleStage.LINK_DA_INVIARE: {
        "script": list(LEVEL_4_SNIPPETS.values()),
        "next_stage": LifecycleStage.LINK_INVIATO,
        "objective": "Spiegare la consulenza e ottenere conferma per l'invio del link",
        "transition_indicators": [
            "Il cliente ha confermato interesse con parole come 'si', 'magari', 'va bene', 'ok'",
            "Il cliente ha espresso disponibilità temporale ('mattina', 'pomeriggio', 'sera')",
            "Il cliente ha fatto qualsiasi domanda positiva sul processo",
            "Il cliente ha mostrato qualsiasi segno di interesse a procedere",
            "PASSA SUBITO A LINK_INVIATO al primo segno positivo - NON CHIEDERE ULTERIORI CONFERME"
        ],
        "available_snippets": {**GENERIC_MESSAGES, **GENERIC_SNIPPETS}
    },
    
    LifecycleStage.LINK_INVIATO: {
        "script": list(LEVEL_5_SNIPPETS.values()),
        "next_stage": None,  # Final stage
        "objective": "Confermare invio del link e offrire supporto finale",
        "transition_indicators": [
            "Il cliente ha ricevuto il link",
            "Il cliente ha confermato l'intenzione di prenotare",
            "Il cliente ha fatto altre domande (rispondi e rimani disponibile)"
        ],
        "available_snippets": {**GENERIC_MESSAGES, **GENERIC_SNIPPETS}
    }
}

# Prompt per il sistema dinamico di decisione lifecycle
LIFECYCLE_DECISION_PROMPT = """
ANALISI LIFECYCLE: Basandoti sulla conversazione corrente, devi decidere se è il momento di cambiare lifecycle.

LIFECYCLE CORRENTE: {current_lifecycle}
OBIETTIVO CORRENTE: {current_objective}

INDICATORI PER LA TRANSIZIONE:
{transition_indicators}

PROSSIMO LIFECYCLE POSSIBILE: {next_stage}

ISTRUZIONI:
1. Analizza attentamente il messaggio dell'utente
2. Valuta se gli indicatori di transizione sono stati raggiunti
3. Assegna un punteggio di confidenza da 0.0 a 1.0
4. Se il punteggio è >= 0.7, raccomanda il cambio di lifecycle
5. Fornisci sempre una spiegazione del tuo ragionamento

FORMATO RISPOSTA:
Devi rispondere SEMPRE in questo formato JSON:
{{
    "should_change_lifecycle": true/false,
    "target_lifecycle": "nome_lifecycle" o null,
    "confidence_score": 0.0-1.0,
    "reasoning": "Spiegazione dettagliata della decisione"
}}

MESSAGGIO UTENTE: {user_message}
"""
