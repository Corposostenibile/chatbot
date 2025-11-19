# Copilot Instructions for `chatbot`

## Architettura e responsabilità
- Tratta `app/main.py` come entrypoint FastAPI e mantieni lì solo configurazione app, CORS, lifecycle e wiring dei router.
- Aggiungi nuovi endpoint in `app/routes.py` usando il `APIRouter` esistente e riutilizza `get_db`/`get_db_session` per l'accesso al database.
- Mantieni i modelli Pydantic in `app/models/api_models.py`, i modelli SQLAlchemy in `app/models/database_models.py` e la logica di dominio del lifecycle in `app/models/lifecycle.py`.
- Estendi la logica conversazionale solo tramite `app/services/unified_agent.py` e `app/data/lifecycle_config.py`, senza richiamare direttamente i client AI nei router.
- Usa `SystemPromptService` e `AIModelService` per gestire system prompt e modelli AI invece di accedere direttamente alle tabelle `system_prompts` o `ai_models`.

## Database e async
- Usa sempre `async for db in get_db():` o `get_db_session()` per ottenere una `AsyncSession` e chiuderla correttamente.
- Scrivi query con l'API 2.0 di SQLAlchemy (`select(...)`, `.scalars().all()`, `.scalar_one_or_none()`), come negli esempi in `app/routes.py` e `app/services/*`.
- Quando modifichi `app/models/database_models.py`, crea o aggiorna una migration in `alembic/versions` e lascia che `scripts/local.sh local-db-init`/`local-db-reset` applichino le migrazioni.
- Mantieni il campo `current_lifecycle` di `SessionModel` sempre allineato con l'enum `LifecycleStage` e aggiorna `SessionModel.is_conversation_finished` solo tramite `_update_session_lifecycle`.

## Unified agent e lifecycle
- Non istanziare mai manualmente `UnifiedAgent`; riutilizza l'istanza globale `unified_agent` da `app/services/unified_agent.py`.
- Quando aggiungi nuove feature conversazionali, aggiorna `LIFECYCLE_SCRIPTS` in `app/data/lifecycle_config.py` (`script`, `objective`, `transition_indicators`, `available_snippets`) invece di hardcodare testo nei router.
- Rispetta il contratto di `LifecycleResponse`: mantieni il formato di `messages`, `debug_logs`, `full_logs`, `requires_human`, `human_task` come in `unified_agent.chat`.
- Per gestire errori AI usa le eccezioni `AIError`, `ParsingError`, `ChatbotError` e mappale in `HTTPException` con codici coerenti come in `/chat`.
- Quando introduci nuove decisioni di lifecycle, usa il campo `confidence` e il threshold `>= 0.7` come nel metodo `_handle_lifecycle_transition`.

## Workflow di sviluppo
- Per lo sviluppo locale, usa sempre `./scripts/local.sh` (es. `local-setup`, `local-db-start`, `local-db-init`, `local-test`, `local-lint`, `local-format`) invece di invocare direttamente Poetry o Alembic.
- Lascia che `scripts/local.sh init_db` gestisca `.env.local`, `DATABASE_URL` e l'aggiornamento di `alembic.ini` invece di modificarli a mano.

## Dashboard, templates e integrazioni
- Per nuove viste HTML riutilizza il router esistente in `app/routes.py` con `Jinja2Templates` e i template in `app/templates/*.html`.
- Mantieni la coerenza dei dashboard: usa query aggregate sui modelli (`SessionModel`, `MessageModel`, `HumanTaskModel`, `SystemPromptModel`) e passa al template solo dizionari serializzabili.
- Quando estendi gli endpoint di gestione system prompts o human tasks, passa sempre tramite `SystemPromptService` e `MessageReviewService` invece di manipolare direttamente le sessioni.
- Se aggiungi nuovi comandi al wrapper `/api/execute/{command}`, aggiorna la mappa `available_commands` in `app/routes.py` per riflettere esattamente ciò che lo script `./server` supporta.

## Flusso end-to-end e funzionalità principali
- 1) La richiesta `/chat` è il punto d'ingresso per la conversazione: `app.routes.chat_endpoint` valida la sessione e poi chiama `unified_agent.chat`.
- 2) `UnifiedAgent.chat`:
	- carica o crea la `SessionModel` (DB);
	- blocca il flusso se esiste una `HumanTask` aperta per la sessione (la UI dovrebbe mostrare la gestione manuale);
	- se `message_count == 0`, invia un auto-response e imposta `CONTRASSEGNATO`; quindi chiama l'AI;
	- se la sessione è in `is_batch_waiting`, accoda nuovi messaggi e ritorna risposta vuota; al termine del timeout, genera un unico prompt aggregato e chiama l'AI;
	- costruisce il `unified_prompt` usando `LIFECYCLE_SCRIPTS` (dal file `app/data/lifecycle_config.py`) e gli `available_snippets` per la fase corrente;
	- chiama il client AI (Google via `datapizza`) con il prompt; la risposta attesa è JSON conforme al `LifecycleResponse` (vedi `app/models/lifecycle.py`);
	- elabora la risposta: normalizza `messages`, valuta `should_change_lifecycle` e la `confidence` (threshold >= 0.7), aggiorna la sessione se necessario, e salva messaggi nel DB o crea `HumanTask` se `requires_human`.
- 3) `SystemPromptService` fornisce il prompt di sistema attivo al momento della chiamata, `AIModelService` restituisce il modello attivo per la chiamata AI.
- 4) I `LIFECYCLE_SCRIPTS` contengono `script`, `objective`, `available_snippets`, e `transition_indicators` — modificare questi file per cambiare il comportamento conversazionale.
- 5) `log_capture` raccoglie i log di una singola sessione per debug e viene restituito come `debug_logs`/`full_logs` nella `LifecycleResponse`.
	- `SystemPromptService.initialize_default_prompt()` viene chiamato durante lo startup (`app/main.py`) per garantire che esista un prompt attivo.

## Vincoli e gotcha importanti
- Non avviare mai il server di produzione né eseguire `./server`, `uvicorn app.main:app` o comandi analoghi da un agente AI.
- Preserva l'uso di `loguru` e di `app.logger_config.log_capture` per costruire `debug_logs`/`full_logs` invece di introdurre sistemi di logging paralleli.
- Non salvare direttamente credenziali o API key nel codice sorgente; lascia che `scripts/local.sh` e i file `.env`/`.env.local` gestiscano la configurazione.
- Mantieni i messaggi, i commenti e le stringhe utente in italiano per coerenza con il resto del progetto.

## Errori comuni e "gotchas"
- Evita il lazy-loading degli oggetti ORM (es. `session.messages`) fuori dal contesto `async for db in get_db()`; usare query esplicite per evitare `greenlet_spawn`.
- L'AI può restituire JSON malformato; `UnifiedAgent._parse_ai_response` contiene tentativi di riparazione (es. escape delle virgolette interne) — mantieni questo comportamento quando estendi il parsing.
- Non cambiare `current_lifecycle` direttamente su `SessionModel` da un router: usa `_update_session_lifecycle` per mantenere la coerenza dello stato e la `is_conversation_finished` quando si raggiunge `LINK_INVIATO`.
- Quando scrivi migrazioni Alembic, ricordati che gli enum (LifecycleStage) sono gestiti a DB; lo script `scripts/local.sh local-db-reset` cancella e ricrea le tabelle e le enums.
- Il comportamento di batch wait è testato in `tests/test_batch_wait.py`; se cambi il timeout, aggiorna i test o il comportamento della UI.
- Non inserire API key o credenziali nel codice sorgente; `scripts/local.sh` e `.env.local` gestiscono l'inserimento sicuro.

## Esempio di risposta AI attesa (formato JSON)
L'agente si aspetta sempre un JSON conforme per semplificare il parsing e le transizioni. Esempio minimale:

```json
{
	"messages": [
		{"text": "Ciao! Posso aiutarti oggi?", "delay_ms": 0}
	],
	"should_change_lifecycle": true,
	"new_lifecycle": "IN_TARGET",
	"reasoning": "L'utente ha mostrato interesse a proseguire",
	"confidence": 0.85,
	"requires_human": false
}
```

Se `requires_human` è `true`, l'AI può restituire un `human_task`:

```json
{
	"requires_human": true,
	"human_task": {"title":"Verifica dati paziente","description":"Controllare informazioni anagrafiche","assigned_to":"team@company.it","metadata":{}}
}
```
