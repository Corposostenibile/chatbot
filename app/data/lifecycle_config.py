"""
Configurazione dei lifecycle e script per il chatter di nutrizione e psicologia
"""
from typing import Dict, List, Any
from app.models.lifecycle import LifecycleStage


# Configurazione degli script per ogni lifecycle (senza triggers_to_next)
LIFECYCLE_SCRIPTS: Dict[LifecycleStage, Dict] = {
    LifecycleStage.NUOVA_LEAD: {
        "script": """
        Ciao! Grazie di avermi scritto! 
        
        Questo è un messaggio automatico che ho scritto personalmente per riuscire a ringraziarti subito della fiducia!🙏
        
        Come sai ricevo centinaia di richieste ogni giorno e ci tengo a dedicarti personalmente l'attenzione che meriti.
        
        Ti chiedo per favore di scrivermi intanto:
        1) Qual è l'obiettivo nel dettaglio che vorresti raggiungere
        2) Cosa hai provato in passato per raggiungerlo  
        3) La tua età
        
        Ps. Anche il tuo nome per non fare gaffe 😅
        
        Appena leggerò la tua risposta ti risponderò personalmente!
        """,
        "next_stage": LifecycleStage.CONTRASSEGNATO,
        "objective": "Ringraziare e raccogliere informazioni base: nome, obiettivo specifico, tentativi passati, età",
        "transition_indicators": [
            "Appena l'utente scrive per primo, ad es: Ciao! Ti ho visto su Facebook, volevo maggiori informazioni",
        ]
    },
    
    LifecycleStage.CONTRASSEGNATO: {
        "script": """
        Eccomi, scusami la risposta tardiva, come stai? Ricevo davvero tante richieste e ci tengo a rispondere personalmente. Possiamo proseguire la nostra conversazione?
        
        [Se manca qualche info, chiedila qui]
        
        La tua scelta di [obiettivo] è un ottimo punto di partenza, soprattutto a [età] anni, e dimostra la tua determinazione a prenderti cura di te stessa in modo consapevole.
        """,
        "next_stage": LifecycleStage.IN_TARGET,
        "objective": "Approfondire le informazioni e confermare interesse",
        "transition_indicators": [
            "Hai tutte le informazioni necessarie (nome, obiettivo, storia passata, età)",
            "Il cliente ha confermato interesse a proseguire",
            "Il cliente ha fornito dettagli aggiuntivi sul suo obiettivo"
        ]
    },
    
    LifecycleStage.IN_TARGET: {
        "script": """
        Perfetto, ora ho un quadro più chiaro della tua situazione.
        
        Con un approccio equilibrato e sostenibile, potrai raggiungere il tuo obiettivo senza rinunce estreme, mantenendo benessere e serenità. La tua motivazione è preziosa e merita tutto il supporto per trasformarsi in risultati duraturi.
        
        Il nostro percorso personalizzato di nutrizione e psicologia ha aiutato centinaia di persone nella tua stessa situazione. Lavoriamo su:
        
        ✓ Piano nutrizionale personalizzato
        ✓ Supporto psicologico mirato  
        ✓ Strategie pratiche per la vita quotidiana
        ✓ Monitoraggio costante dei progressi
        
        La cosa bella è che iniziamo sempre con una consulenza gratuita per capire esattamente qual è il percorso migliore per te.
        """,
        "next_stage": LifecycleStage.LINK_DA_INVIARE,
        "objective": "Presentare i benefici del percorso integrato e introdurre la consulenza gratuita",
        "transition_indicators": [
            "Il cliente ha mostrato interesse per la consulenza gratuita",
            "Il cliente ha fatto domande sui servizi",
            "Il cliente ha confermato di voler saperne di più"
        ]
    },
    
    LifecycleStage.LINK_DA_INVIARE: {
        "script": """
        Fantastico! Sono davvero felice di sentirti così determinato/a.
        
        La prima consulenza gratuita dura circa 45 minuti e durante questo incontro:
        - Analizzeremo insieme la tua situazione attuale
        - Definiremo gli obiettivi che vuoi raggiungere
        - Ti mostreremo come il nostro metodo può aiutarti
        - Risponderemo a tutte le tue domande
        
        È completamente gratuita e senza impegno. Se poi deciderai di continuare con noi, 
        saremo felici di accompagnarti nel tuo percorso di trasformazione.
        
        Sei pronto/a per prenotare la tua consulenza gratuita?
        """,
        "next_stage": LifecycleStage.LINK_INVIATO,
        "objective": "Spiegare la consulenza e ottenere conferma per l'invio del link",
        "transition_indicators": [
            "Il cliente ha confermato interesse con parole come 'si', 'magari', 'va bene', 'ok'",
            "Il cliente ha espresso disponibilità temporale ('mattina', 'pomeriggio', 'sera')",
            "Il cliente ha fatto qualsiasi domanda positiva sul processo",
            "Il cliente ha mostrato qualsiasi segno di interesse a procedere",
            "PASSA SUBITO A LINK_INVIATO al primo segno positivo - NON CHIEDERE ULTERIORI CONFERME"
        ]
    },
    
    LifecycleStage.LINK_INVIATO: {
        "script": """
        Perfetto! Ecco il link per prenotare la tua consulenza gratuita:
        
        👉 https://calendly.com/consulenza-gratuita-nutrizione-psicologia
        
        Scegli l'orario che preferisci tra quelli disponibili. Riceverai una email di conferma 
        con tutti i dettagli dell'appuntamento.
        
        Ti consiglio di prepararti pensando a:
        - I tuoi obiettivi principali
        - Le difficoltà che stai affrontando
        - Eventuali domande che vuoi fare
        
        Sono sicuro che sarà l'inizio di un percorso fantastico per te! 
        Ci sentiamo presto! 🌟
        """,
        "next_stage": None,  # Obiettivo raggiunto
        "objective": "Fornire il link e completare il processo di conversione",
        "transition_indicators": []
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