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
# nuova lead serve solo per inizializzare la conversazione
LIFECYCLE_SCRIPTS: Dict[LifecycleStage, Dict] = {
    LifecycleStage.NUOVA_LEAD: {
        "script": """
        """,
        "next_stage": LifecycleStage.CONTRASSEGNATO,
        "objective": "",
        "transition_indicators": [
        ],
        "available_snippets": ""
    },

    LifecycleStage.CONTRASSEGNATO: {
        "script": list(LEVEL_2_SNIPPETS.values()),
        "next_stage": LifecycleStage.IN_TARGET,
        "objective": "Rispondi dopo il messaggio automatico con esattamente lo snippet 'livello_2' senza scusarti per l'attesa. Raccogli le informazioni di base in un unico messaggio (NON SPEZZETTARE), e solo una volta ottenute, chiedere esplicitamente qual è la motivazione principale per cui vuole migliorare (SPEZZETTARE qui esattamente come da script), passare al prossimo lifecycle appena chiesta la motivazione.",
        "transition_indicators": [
            "Hai tutte le informazioni necessarie (nome, obiettivo, età)",
            "Il cliente ha confermato interesse a proseguire",
            "Il cliente ha fornito dettagli aggiuntivi sul suo obiettivo"
        ],
        "available_snippets": {**GENERIC_SNIPPETS}
    },

    LifecycleStage.IN_TARGET: {
        "script": list(LEVEL_3_SNIPPETS.values()),
        "next_stage": LifecycleStage.LINK_DA_INVIARE,
        "objective": "Presentare i benefici del percorso integrato e introdurre la consulenza gratuita.",
        "transition_indicators": [
            "Solo se dopo aver presentato la consulenza gratuita, il cliente ha accettato di prenotare",
        ],
        "available_snippets": {**GENERIC_MESSAGES, **GENERIC_SNIPPETS}
    },

    LifecycleStage.LINK_DA_INVIARE: {
        "script": list(LEVEL_4_SNIPPETS.values()),
        "next_stage": LifecycleStage.LINK_INVIATO,
        "objective": "Inviare il link di prenotazione e ottenere conferma",
        "transition_indicators": [
            "PASSA SUBITO A LINK_INVIATO al primo segno positivo - NON CHIEDERE ULTERIORI CONFERME"
        ],
        "available_snippets": {**GENERIC_MESSAGES, **GENERIC_SNIPPETS}
    },

    LifecycleStage.LINK_INVIATO: {
        "script": list(LEVEL_5_SNIPPETS.values()),
        "next_stage": None,  # Final stage
        "objective": "",
        "transition_indicators": [
        ],
        "available_snippets": ""
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
