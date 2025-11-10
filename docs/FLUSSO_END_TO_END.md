# 🔄 Flusso Completo End-to-End del Chatbot

## Panoramica Generale

Il chatbot di Corposostenibile è un sistema intelligente basato su FastAPI e Google Gemini AI che gestisce conversazioni con potenziali clienti nel settore nutrizione/psicologia. Il sistema automatizza la transizione tra diversi lifecycle stage, persistendo i dati su PostgreSQL.

**Flusso Principale:**
```
RICHIESTA UTENTE → API FastAPI → UnifiedAgent → Google Gemini AI → RISPOSTA INTELLIGENTE
                                       ↓
                            DECISIONE LIFECYCLE
                                       ↓
                         DATABASE POSTGRESQL UPDATE
                                       ↓
                           STATO SESSIONE AGGIORNATO
```

---

## 1. Architettura Componenti

### 1.1 Stack Tecnologico

```
┌─────────────────────────────────────────────────────────┐
│                   RESPOND.IO WEBHOOK                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FASTAPI APPLICATION (main.py)              │
│  - POST /chat → Chat endpoint principale               │
│  - GET /health → Health check                          │
│  - GET /status → Status dettagliato                    │
│  - GET /session/{id} → Info sessione                   │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┬─────────────┐
        ▼                         ▼             ▼
   ┌─────────┐          ┌──────────────┐  ┌────────────────┐
   │ DATABASE│          │UnifiedAgent  │  │Error Handlers  │
   │PgSQL    │          │(unified_     │  │& Fallbacks     │
   │Async    │          │agent.py)     │  │                │
   └─────────┘          └──────┬───────┘  └────────────────┘
        ▲                      │
        │                      ▼
        │            ┌──────────────────────┐
        │            │Google Gemini AI API  │
        │            │(Generazione risposte)│
        │            │(Decisioni Lifecycle) │
        │            └──────────────────────┘
        │
   ┌────────────────────────────┐
   │ Database Models (SQLAlchemy)│
   │ - SessionModel             │
   │ - MessageModel             │
   └────────────────────────────┘
```

### 1.2 Componenti Chiave

| Componente | File | Responsabilità |
|-----------|------|-----------------|
| **API Principal** | `app/main.py` | Espone gli endpoint FastAPI, gestisce il ciclo di vita |
| **Agent Intelligente** | `app/services/unified_agent.py` | Orchestrazione conversazioni e decisioni AI |
| **Config Lifecycle** | `app/data/lifecycle_config.py` | Script e trigger per ogni fase |
| **Modelli** | `app/models/` | Enum lifecycle, modelli DB, API models |
| **Database** | `app/database.py` | Configurazione SQLAlchemy async |

---

## 2. Flusso di una Singola Richiesta Chat

### 2.1 Sequenza Temporale Completa

```
TEMPO 0ms: RICHIESTA ARRIVA
│
├─ POST /chat ricevuta da FastAPI
├─ Payload: {"message": "Ciao, ho problemi di peso", "session_id": "user_123"}
│
TEMPO 10ms: INIZIALIZZAZIONE SESSIONE
│
├─ UnifiedAgent.chat() chiamato
├─ Ricerca sessione in database (SELECT)
├─ Se non esiste → Crea nuova sessione (INSERT)
│  └─ current_lifecycle = NUOVA_LEAD
│  └─ created_at = now()
│
TEMPO 30ms: COSTRUZIONE CONTESTO
│
├─ _build_conversation_context() esegue
├─ Query ultimi 10 messaggi dalla sessione (ORDER BY DESC LIMIT 10)
├─ Riordina cronologicamente (reversed)
├─ Formatta come stringa leggibile
│
TEMPO 50ms: GENERAZIONE PROMPT UNIFICATO
│
├─ _get_unified_prompt() genera prompt completo
├─ Include: Identità AI + Lifecycle corrente + Script + Contesto + Messaggio
├─ Formato rigido per risposta JSON
│
TEMPO 60ms: CHIAMATA GOOGLE GEMINI AI
│
├─ agent.a_run(unified_prompt) eseguita
├─ Attesa risposta (typically 500-1500ms)
├─ Risposta in formato JSON strutturato
│
TEMPO 1500ms+: PARSING RISPOSTA
│
├─ Pulizia markdown (```json → rimozione)
├─ JSON parsing
├─ Estrazione campi: message, should_change_lifecycle, new_lifecycle, confidence
│
TEMPO 1600ms: DECISIONE LIFECYCLE
│
├─ Valutazione: should_change AND confidence >= 0.7 ?
├─ SE SÌ → _update_session_lifecycle()
│  └─ UPDATE SessionModel SET current_lifecycle = new_value
│  └─ await db.commit()
├─ SE NO → Rimane lifecycle precedente
│
TEMPO 1610ms: SAVE CONVERSAZIONE
│
├─ _add_to_conversation_history() eseguita
├─ INSERT user message nel database
├─ INSERT assistant response nel database
├─ await db.commit()
│
TEMPO 1620ms: CALCOLO NEXT ACTIONS
│
├─ _get_next_actions(current_lifecycle) fornisce:
│  ├─ NUOVA_LEAD: ["Ascolta attivamente", "Fai domande", "Mostra empatia"]
│  ├─ CONTRASSEGNATO: ["Approfondisci", "Valuta motivazione", "Presenta benefici"]
│  ├─ IN_TARGET: ["Presenta soluzione", "Spiega integrazione", "Introduci consulenza"]
│  ├─ LINK_DA_INVIARE: ["Conferma interesse", "Prepara per link", "Rassicura"]
│  └─ LINK_INVIATO: ["Conferma link", "Fornisci istruzioni", "Rimani disponibile"]
│
TEMPO 1630ms: COSTRUZIONE RESPONSE OBJECT
│
├─ LifecycleResponse creato con:
│  ├─ message: risposta AI naturale
│  ├─ current_lifecycle: stage attuale
│  ├─ lifecycle_changed: true/false
│  ├─ previous_lifecycle: stage precedente (se cambiato)
│  ├─ next_actions: lista azioni consigliate
│  └─ ai_reasoning: spiegazione decisione
│
TEMPO 1640ms: RISPOSTA INVIATA
│
└─ JSON response ritornata al client (respond.io)
  └─ HTTP 200 OK
```

### 2.2 Esempio Concreto: Transizione NUOVA_LEAD → CONTRASSEGNATO

**Input Utente:**
```json
{
  "session_id": "user_123",
  "message": "Ho problemi seri di sovrappeso e tensione muscolare, mi sento sempre stanco"
}
```

**Prompt Unificato Inviato a Gemini:**
```
Sei un assistente virtuale specializzato nel supportare persone interessate a percorsi di nutrizione e psicologia.

LA TUA IDENTITÀ:
- Sei empatico, professionale e orientato al risultato
- Non sei un nutrizionista o psicologo, ma un consulente che guida verso la soluzione giusta
- Il tuo obiettivo è far arrivare il cliente al lifecycle "Link Inviato"
- Mantieni sempre un tono caldo ma professionale

LIFECYCLE CORRENTE: NUOVA_LEAD
OBIETTIVO CORRENTE: Identificare i problemi e bisogni specifici del cliente

SCRIPT GUIDA PER QUESTO LIFECYCLE:
Ciao! Sono qui per aiutarti a trovare il percorso giusto per il tuo benessere.
Vedo che sei interessato/a ai nostri servizi di nutrizione e psicologia.

Per poterti aiutare al meglio, mi piacerebbe sapere:
- Qual è la tua principale preoccupazione riguardo al benessere?
- Hai mai seguito percorsi di nutrizione o supporto psicologico prima?

CRONOLOGIA CONVERSAZIONE:
Nessuna conversazione precedente.

MESSAGGIO UTENTE: Ho problemi seri di sovrappeso e tensione muscolare, mi sento sempre stanco

INDICATORI PER PASSARE AL PROSSIMO LIFECYCLE (CONTRASSEGNATO):
- Il cliente ha espresso un problema specifico
- Il cliente ha condiviso una preoccupazione personale
- Il cliente ha mostrato interesse per i servizi

FORMATO RISPOSTA RICHIESTO:
{
    "message": "La tua risposta conversazionale al cliente",
    "should_change_lifecycle": true/false,
    "new_lifecycle": "contrassegnato",
    "reasoning": "Spiegazione del perché hai deciso di cambiare o non cambiare lifecycle",
    "confidence": 0.0-1.0
}
```

**Risposta di Gemini:**
```json
{
  "message": "Capisco perfettamente la tua situazione. È normale sentirsi così e hai fatto bene a cercare aiuto. Il nostro approccio integra nutrizione e psicologia perché sappiamo che il benessere è completo solo quando corpo e mente lavorano insieme. Dimmi, quanto è importante per te risolvere questa situazione? Su una scala da 1 a 10, quanto ti sta influenzando nella vita quotidiana?",
  "should_change_lifecycle": true,
  "new_lifecycle": "contrassegnato",
  "reasoning": "Il cliente ha espresso chiaramente i suoi problemi specifici (sovrappeso, tensione muscolare, stanchezza) e ha mostrato disponibilità a cercare aiuto. Ha confermato interesse per i servizi. Tutti gli indicatori per la transizione sono presenti.",
  "confidence": 0.95
}
```

**Decisione Sistema:**
- `should_change_lifecycle` = true ✓
- `confidence` (0.95) >= 0.7 ✓
- Transizione autorizzata → UPDATE SessionModel

**Response al Client:**
```json
{
  "message": "Capisco perfettamente la tua situazione. È normale sentirsi così e hai fatto bene a cercare aiuto. Il nostro approccio integra nutrizione e psicologia perché sappiamo che il benessere è completo solo quando corpo e mente lavorano insieme. Dimmi, quanto è importante per te risolvere questa situazione? Su una scala da 1 a 10, quanto ti sta influenzando nella vita quotidiana?",
  "current_lifecycle": "contrassegnato",
  "lifecycle_changed": true,
  "previous_lifecycle": "nuova_lead",
  "next_actions": [
    "Approfondisci i problemi identificati",
    "Valuta il livello di motivazione del cliente",
    "Inizia a presentare i benefici del percorso"
  ],
  "ai_reasoning": "Il cliente ha espresso chiaramente i suoi problemi specifici (sovrappeso, tensione muscolare, stanchezza) e ha mostrato disponibilità a cercare aiuto. Ha confermato interesse per i servizi. Tutti gli indicatori per la transizione sono presenti."
}
```

---

## 3. Gestione Sessioni e Database

### 3.1 Schema Database

```sql
-- Tabella Sessioni
CREATE TABLE session_model (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    current_lifecycle VARCHAR(50) NOT NULL DEFAULT 'nuova_lead',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabella Messaggi
CREATE TABLE message_model (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES session_model(id),
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

### 3.2 Flusso Persistenza Dati

```
RICHIESTA CHAT
    ↓
Ricerca Sessione: SELECT * FROM session_model WHERE session_id = 'user_123'
    ↓
    ├─ Trovato: Usa sessione esistente
    │   └─ current_lifecycle già impostato
    │
    └─ Non trovato: Crea sessione
        └─ INSERT INTO session_model (session_id) VALUES ('user_123')
        └─ current_lifecycle = 'nuova_lead' (DEFAULT)
    
DOPO RISPOSTA AI
    ↓
Decisione Lifecycle (confidence >= 0.7?)
    │
    ├─ SÌ: Transizione necessaria
    │  └─ UPDATE session_model SET current_lifecycle = 'contrassegnato'
    │
    └─ NO: Mantieni lifecycle attuale
    
SAVE CONVERSAZIONE
    ├─ INSERT message_model (session_id, role='user', message=user_input)
    ├─ INSERT message_model (session_id, role='assistant', message=ai_response)
    └─ Limita a ultimi 20 messaggi per sessione (opzionale, per memoria)
```

### 3.3 Operazioni Async

```python
# Tutte le operazioni database usano async/await:

async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)  # Startup

async for db in get_db():
    result = await db.execute(select(...))  # Query
    await db.commit()  # Persistenza
```

---

## 4. I 5 Lifecycle Stage

### 4.1 Panoramica Completa

```
┌───────────────┐
│  NUOVA_LEAD   │  ← Primo contatto
│  (Inizio)     │
└───────┬───────┘
        │ [Problema specifico + Interesse]
        ▼
┌───────────────────────┐
│  CONTRASSEGNATO       │  ← Lead qualificato
│  (Qualificazione)     │
└───────┬───────────────┘
        │ [Alta motivazione + Urgenza]
        ▼
┌────────────────┐
│  IN_TARGET     │  ← Cliente pronto per la soluzione
│  (Target)      │
└───────┬────────┘
        │ [Interesse per la consulenza]
        ▼
┌───────────────────────┐
│  LINK_DA_INVIARE      │  ← Preparazione per l'invio
│  (Conversione)        │
└───────┬───────────────┘
        │ [Conferma di voler prenotare]
        ▼
┌────────────────────┐
│  LINK_INVIATO      │  ← OBIETTIVO RAGGIUNTO
│  (Conversione OK)  │
└────────────────────┘
```

### 4.2 Dettagli per Ogni Stage

#### STAGE 1: NUOVA_LEAD (Primo Contatto)

| Aspetto | Dettaglio |
|---------|----------|
| **Obiettivo** | Identificare i problemi e bisogni specifici |
| **Script** | Presentazione calda + domande base |
| **Azioni** | Ascoltare, fare domande, mostrare empatia |
| **Indicatori Transizione** | Problema specifico espresso + Interesse mostrato |
| **Prossimo Stage** | CONTRASSEGNATO |
| **Confidence Min** | 0.7 |

**Esempio Script:**
```
Ciao! Sono qui per aiutarti a trovare il percorso giusto per il tuo benessere.
Vedo che sei interessato/a ai nostri servizi di nutrizione e psicologia.

Per poterti aiutare al meglio, mi piacerebbe sapere:
- Qual è la tua principale preoccupazione riguardo al benessere?
- Hai mai seguito percorsi di nutrizione o supporto psicologico prima?
```

---

#### STAGE 2: CONTRASSEGNATO (Qualificazione)

| Aspetto | Dettaglio |
|---------|----------|
| **Obiettivo** | Valutare il livello di motivazione e urgenza |
| **Script** | Validazione empatica + Scala motivazione (1-10) |
| **Azioni** | Approfondire, valutare urgenza, presentare benefici |
| **Indicatori Transizione** | Alta motivazione (8-10/10) + Urgenza mostrata |
| **Prossimo Stage** | IN_TARGET |
| **Confidence Min** | 0.7 |

**Esempio Script:**
```
Capisco perfettamente la tua situazione. È normale sentirsi così e hai fatto bene a cercare aiuto.

Il nostro approccio integra nutrizione e psicologia perché sappiamo che il benessere è completo solo quando 
corpo e mente lavorano insieme.

Dimmi, quanto è importante per te risolvere questa situazione? 
Su una scala da 1 a 10, quanto ti sta influenzando nella vita quotidiana?
```

---

#### STAGE 3: IN_TARGET (Target/Soluzione)

| Aspetto | Dettaglio |
|---------|----------|
| **Obiettivo** | Presentare la soluzione e introdurre consulenza gratuita |
| **Script** | Presentazione benefici + Proposte valore + Invito consulenza |
| **Azioni** | Presentare soluzione, spiegare integrazione, introdurre consulenza |
| **Indicatori Transizione** | Interesse per consulenza + Domande sui servizi + Disponibilità |
| **Prossimo Stage** | LINK_DA_INVIARE |
| **Confidence Min** | 0.7 |

**Esempio Script:**
```
Perfetto, vedo che sei davvero motivato/a a cambiare. Questa è già metà del successo!

Il nostro percorso personalizzato di nutrizione e psicologia ha aiutato centinaia di persone 
nella tua stessa situazione. Lavoriamo su:

✓ Piano nutrizionale personalizzato
✓ Supporto psicologico mirato
✓ Strategie pratiche per la vita quotidiana
✓ Monitoraggio costante dei progressi

La cosa bella è che iniziamo sempre con una consulenza gratuita per capire esattamente 
qual è il percorso migliore per te. Ti interessa saperne di più?
```

---

#### STAGE 4: LINK_DA_INVIARE (Conversione/Pre-invio)

| Aspetto | Dettaglio |
|---------|----------|
| **Obiettivo** | Spiegare la consulenza e ottenere conferma per l'invio link |
| **Script** | Descrizione consulenza gratuita + Preparazione mentale |
| **Azioni** | Confermare interesse, preparare per link, rassicurare |
| **Indicatori Transizione** | Conferma di voler prenotare + Chiesta procedura + Disponibilità |
| **Prossimo Stage** | LINK_INVIATO |
| **Confidence Min** | 0.7 |

**Esempio Script:**
```
Fantastico! Sono davvero felice di sentirti così determinato/a.

La prima consulenza gratuita dura circa 45 minuti e durante questo incontro:
- Analizzeremo insieme la tua situazione attuale
- Definiremo gli obiettivi che vuoi raggiungere
- Ti mostreremo come il nostro metodo può aiutarti
- Risponderemo a tutte le tue domande

È completamente gratuita e senza impegno. Se poi deciderai di continuare con noi, 
saremo felici di accompagnarti nel tuo percorso di trasformazione.

Sei pronto/a per prenotare la tua consulenza gratuita?
```

---

#### STAGE 5: LINK_INVIATO (Obiettivo Raggiunto ✅)

| Aspetto | Dettaglio |
|---------|----------|
| **Obiettivo** | Fornire link e completare processo di conversione |
| **Script** | Invio link Calendly + Istruzioni prenotazione |
| **Azioni** | Confermare invio, fornire istruzioni, restare disponibile |
| **Indicatori Transizione** | NESSUNO - Obiettivo finale |
| **Prossimo Stage** | NONE (Fine) |
| **Confidence Min** | N/A |

**Esempio Script:**
```
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
```

---

## 5. Gestione Errori e Fallback

### 5.1 Flusso Gestione Errori

```
TRY: API Call a Gemini
    │
    ├─ SUCCESS: Prosegui con elaborazione
    │
    └─ FAILURE: Exception catturata
        ├─ Log errore
        ├─ Chiama _create_fallback_response()
        │   └─ Resposta predefinita basata su lifecycle
        │   └─ NO cambio di lifecycle
        │   └─ Registra nella cronologia
        │
        └─ Return fallback response al client
```

### 5.2 Fallback Responses per Lifecycle

```python
fallback_messages = {
    LifecycleStage.NUOVA_LEAD: 
        "Ciao! Sono qui per aiutarti con il tuo percorso di benessere. Come posso supportarti oggi?",
    
    LifecycleStage.CONTRASSEGNATO: 
        "Capisco la tua situazione. Parlami di più di quello che stai vivendo.",
    
    LifecycleStage.IN_TARGET: 
        "È normale sentirsi così. Il nostro approccio integrato di nutrizione e psicologia può davvero aiutarti.",
    
    LifecycleStage.LINK_DA_INVIARE: 
        "Perfetto! Ti piacerebbe saperne di più sulla nostra consulenza gratuita?",
    
    LifecycleStage.LINK_INVIATO: 
        "Grazie per il tuo interesse! Ti ho inviato il link per prenotare la tua consulenza gratuita."
}
```

### 5.3 Gestione Eccezioni Globale

```python
# In main.py

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Gestisce le eccezioni HTTP con timestamp"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "timestamp": datetime.now().isoformat()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Gestisce le eccezioni generali - ritorna 500"""
    logger.error(f"Errore non gestito: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Errore interno del server",
            "timestamp": datetime.now().isoformat()
        }
    )
```

---

## 6. Endpoints API

### 6.1 POST /chat - Endpoint Principale

**Request:**
```json
{
  "session_id": "user_123",
  "message": "Ciao, ho un problema di peso"
}
```

**Response (200 OK):**
```json
{
  "message": "Capisco perfettamente la tua situazione...",
  "current_lifecycle": "contrassegnato",
  "lifecycle_changed": true,
  "previous_lifecycle": "nuova_lead",
  "next_actions": [
    "Approfondisci i problemi identificati",
    "Valuta il livello di motivazione del cliente"
  ],
  "ai_reasoning": "Il cliente ha espresso chiaramente i suoi problemi..."
}
```

**Response (500 - Error):**
```json
{
  "detail": "Errore interno del server",
  "timestamp": "2025-11-10T14:30:45.123456"
}
```

---

### 6.2 GET /health - Health Check

**Response (200 OK):**
```json
{
  "status": "healthy",
  "ai_response": true
}
```

Usato da Cloud Run per verificare disponibilità del servizio.

---

### 6.3 GET /status - Status Dettagliato

**Response (200 OK):**
```json
{
  "app_name": "Chatbot",
  "version": "1.0.0",
  "debug": false,
  "database": "connected",
  "ai_available": true
}
```

---

### 6.4 GET /session/{session_id} - Info Sessione

**Response (200 OK):**
```json
{
  "session_id": "user_123",
  "current_lifecycle": "contrassegnato",
  "conversation_length": 4,
  "created_at": "2025-11-10T10:00:00Z",
  "updated_at": "2025-11-10T14:30:45Z"
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Sessione non trovata"
}
```

---

## 7. Ciclo Completo: Esempio Reale

### 7.1 Scenario: Marco che scopre il servizio

#### Messaggio 1: Marco scrive il primo messaggio

```
📤 UTENTE: "Ciao, ho sentito parlare di voi. Io ho problemi di sovrappeso e stress da lavoro"

SISTEMA INTERNO:
- Sessione: marco_123 (CREATA)
- Lifecycle: NUOVA_LEAD
- Contesto: Vuoto (primo messaggio)

PROMPT A GEMINI:
[NUOVA_LEAD script + messaggio]

RISPOSTA AI:
{
  "message": "Ciao Marco! Sono felicissimo di sentirti. Il sovrappeso e lo stress sono spesso collegati, e il nostro approccio integrato li affronta insieme. Ho sentito che il peso e lo stress ti stanno influenzando. Raccontami di più: da quanto tempo stai vivendo questa situazione?",
  "should_change_lifecycle": true,
  "new_lifecycle": "contrassegnato",
  "confidence": 0.85
}

DECISIONE: Confidence (0.85) >= 0.7 → TRANSIZIONE AUTORIZZATA ✓

📥 SISTEMA: Sessione aggiornata a CONTRASSEGNATO
         Messaggio aggiunto alla cronologia
         Next actions forniti
```

---

#### Messaggio 2: Marco risponde sulla gravità

```
📤 UTENTE: "Ormai da 5 anni sto così. É veramente 10/10 di importanza risolvere questo"

SISTEMA INTERNO:
- Sessione: marco_123 (ESISTENTE)
- Lifecycle: CONTRASSEGNATO
- Contesto: [Messaggio precedente + questa risposta]

PROMPT A GEMINI:
[CONTRASSEGNATO script + contesto + messaggio]

RISPOSTA AI:
{
  "message": "Vedo che è veramente una priorità per te, e 5 anni è un lungo periodo. La tua motivazione è esattamente quello che serve per il cambiamento. Il nostro percorso ha aiutato molte persone nella tua situazione. Combiniamo un piano nutrizionale personalizzato con il supporto psicologico per affrontare sia il peso che lo stress. Ti interesserebbe scoprire come possiamo aiutarti concretamente?",
  "should_change_lifecycle": true,
  "new_lifecycle": "in_target",
  "confidence": 0.92
}

DECISIONE: Confidence (0.92) >= 0.7 → TRANSIZIONE AUTORIZZATA ✓

📥 SISTEMA: Sessione aggiornata a IN_TARGET
         Cronologia aggiornata
         Marco è pronto per la presentazione della soluzione
```

---

#### Messaggio 3: Marco chiede dei dettagli

```
📤 UTENTE: "Mi piacerebbe sapere di più. Quali sono i benefici effettivi?"

SISTEMA INTERNO:
- Sessione: marco_123 (ESISTENTE)
- Lifecycle: IN_TARGET
- Contesto: [Ultimi 10 messaggi della conversazione]

PROMPT A GEMINI:
[IN_TARGET script + benefici della soluzione + contesto]

RISPOSTA AI:
{
  "message": "Perfetto! I benefici sono veramente concreti: [benefici dettagliati...] La cosa bella è che iniziamo sempre con una consulenza gratuita di 45 minuti dove analizziamo la tua situazione specifica. Non c'è nessun impegno, solo l'occasione di scoprire il percorso giusto per te. Ti piacerebbe prenotare una consulenza gratuita?",
  "should_change_lifecycle": true,
  "new_lifecycle": "link_da_inviare",
  "confidence": 0.88
}

DECISIONE: Confidence (0.88) >= 0.7 → TRANSIZIONE AUTORIZZATA ✓

📥 SISTEMA: Sessione aggiornata a LINK_DA_INVIARE
         Marco è pronto per ricevere il link
```

---

#### Messaggio 4: Marco conferma l'interesse

```
📤 UTENTE: "Sì, mi piacerebbe prenotare la consulenza gratuita"

SISTEMA INTERNO:
- Sessione: marco_123 (ESISTENTE)
- Lifecycle: LINK_DA_INVIARE
- Contesto: [Intera conversazione]

PROMPT A GEMINI:
[LINK_DA_INVIARE script + conferma]

RISPOSTA AI:
{
  "message": "Fantastico Marco! Ecco il link per prenotare: https://calendly.com/consulenza-gratuita-nutrizione-psicologia Scegli l'orario che preferisci. Ti consiglio di pensare ai tuoi obiettivi principali prima della chiamata. Sono sicuro che sarà l'inizio di un percorso fantastico! Ci sentiamo presto! 🌟",
  "should_change_lifecycle": true,
  "new_lifecycle": "link_inviato",
  "confidence": 0.99
}

DECISIONE: Confidence (0.99) >= 0.7 → TRANSIZIONE AUTORIZZATA ✓

📥 SISTEMA: Sessione aggiornata a LINK_INVIATO ✅
         OBIETTIVO RAGGIUNTO!
         Marco ha ricevuto il link per la consulenza gratuita
         Database contiene la cronologia completa della conversazione
```

### 7.2 Timeline Completa

```
Marco_123 Timeline:
│
├─ T+0m: Messaggio 1 → NUOVA_LEAD → (0.85 confidence) → CONTRASSEGNATO
├─ T+2m: Messaggio 2 → CONTRASSEGNATO → (0.92 confidence) → IN_TARGET
├─ T+4m: Messaggio 3 → IN_TARGET → (0.88 confidence) → LINK_DA_INVIARE
└─ T+6m: Messaggio 4 → LINK_DA_INVIARE → (0.99 confidence) → LINK_INVIATO ✅

Total Session Duration: 6 minuti
Total Messages: 8 (4 user + 4 AI)
Database Records: 
  - 1 SessionModel
  - 8 MessageModel
  - Transizioni: 4
```

---

## 8. Deployment e Ciclo Vita Produzione

### 8.1 Deployment su Google Cloud Run

```bash
./scripts/deploy.sh

FLUSSO:
1. Abilita API necessarie su Cloud
2. Build immagine Docker
3. Push a Google Container Registry
4. Deploy su Cloud Run
5. Configura autoscaling (0-10 istanze)
6. Espone URL pubblico
```

### 8.2 Ciclo di Vita Produzione

```
┌─────────────────────────────────────────────────┐
│   CLOUD RUN INSTANCE AVVIATA                    │
│   - Memoria: 512Mi                              │
│   - Timeout: 540s                               │
│   - Concorrenza: 80                             │
└────────────┬────────────────────────────────────┘
             │
             ├─ Health Check Endpoint: /health
             │  └─ Chiamato ogni 10s da Cloud Run
             │  └─ Se fallisce: Istanza terminata
             │
             ├─ Chat Requests ricevute
             │  └─ POST /chat (da respond.io)
             │  └─ Risposta in <2s (99.9% dei casi)
             │
             └─ Scaling Automatico
                ├─ Carico alto: Crea nuove istanze
                ├─ Carico basso: Elimina istanze
                └─ Min 0, Max 10
```

### 8.3 Monitoraggio

```
Metriche Critiche:
├─ Availability: % dei /health check che passano
├─ Response Time: Latenza media risposte /chat
├─ Error Rate: % di errori 5xx
├─ Database Connections: Numero connessioni attive
├─ AI API Quota: Utilizzo API Gemini
└─ Session Count: Numero sessioni attive
```

---

## 9. Sicurezza e Best Practices

### 9.1 Sicurezza

✅ **Implementate:**
- Variabili d'ambiente per secrets (API keys)
- CORS configurato
- Utente non-root in container
- Health checks per validazione
- Logging strutturato (loguru)
- Gestione eccezioni globale
- Database async per scalabilità

### 9.2 Best Practices

✅ **Seguite:**
- Dependency injection (get_db)
- Async/await per operazioni I/O
- Enum per lifecycle stages
- Modelli Pydantic per validazione
- Type hints (Python 3.11+)
- Logging dettagliato per debug
- Separate config per ambienti (DEBUG, LOG_LEVEL)

---

## 10. Checklist Completa: Dal Messaggio al Database

```
□ Client invia messaggio via HTTP POST
□ FastAPI riceve richiesta su /chat
□ Valida input con modello Pydantic
□ UnifiedAgent.chat() iniziato
□ Connessione al database stabilita
□ Sessione cercata in database
  ├─ Se esiste: Usa sessione
  └─ Se non esiste: Crea nuova
□ Ultimo lifecycle recuperato
□ Ultimi 10 messaggi recuperati dal database
□ Contesto della conversazione costruito
□ Prompt unificato generato
□ Google Gemini AI chiamato
□ Risposta JSON parsata
□ Decisione di transizione valutata
  ├─ Confidence >= 0.7 e should_change?
  ├─ Sì: Esegui transizione
  │   └─ UPDATE session_model SET current_lifecycle = new_value
  └─ No: Mantieni lifecycle precedente
□ Messaggio utente salvato in database (INSERT)
□ Messaggio AI salvato in database (INSERT)
□ Next actions calcolati
□ LifecycleResponse costruito
□ Response JSON ritornato al client (HTTP 200)
□ Dati di sessione persistono in PostgreSQL
□ Prossima richiesta da stesso client userà sessione esistente
```

---

## Conclusioni

Il sistema è progettato per essere:
- **Intelligente**: Decisioni lifecycle automatiche con Gemini AI
- **Scalabile**: Async, auto-scaling su Cloud Run
- **Robusto**: Fallback responses, error handling globale
- **Tracciabile**: Logging completo, database persistente
- **Modulare**: Componenti separati e responsabilità chiare

Ogni conversazione è un journey guidato dal sistema attraverso 5 stadi verso la conversione finale: il cliente che prenota la consulenza gratuita.
