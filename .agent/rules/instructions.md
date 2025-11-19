# Istruzioni del Progetto Chatbot

Questo file contiene le istruzioni essenziali per lavorare sul progetto Chatbot. Segui queste linee guida per mantenere la coerenza e la qualità del codice.

## 1. Panoramica del Progetto

Il progetto è un chatbot moderno costruito con **FastAPI**. Utilizza un'architettura asincrona per gestire sessioni di chat, lifecycle degli utenti, e integrazioni con modelli AI.

### Stack Tecnologico
-   **Linguaggio**: Python 3.11+
-   **Framework Web**: FastAPI
-   **Database**: PostgreSQL (produzione/docker), SQLite (sviluppo locale rapido)
-   **ORM**: SQLAlchemy (Async)
-   **Migrazioni**: Alembic
-   **Template Engine**: Jinja2 (per dashboard e visualizzazioni)
-   **Logging**: Loguru

## 2. Struttura del Codice

-   `app/`: Directory principale del codice sorgente.
    -   `main.py`: Punto di ingresso dell'applicazione, configurazione FastAPI e lifecycle.
    -   `routes.py`: Definizione degli endpoint API e delle view HTML.
    -   `database.py`: Configurazione della connessione al database (supporta SQLite e PostgreSQL async).
    -   `config.py`: Gestione della configurazione tramite Pydantic Settings.
    -   `models/`: Modelli Pydantic (API) e SQLAlchemy (Database).
    -   `services/`: Logica di business (UnifiedAgent, SystemPromptService, ecc.).
    -   `templates/`: File HTML Jinja2.
-   `scripts/`: Script di utilità per gestione locale e deployment.
-   `alembic/`: Configurazioni e versioni delle migrazioni database.
-   `tests/`: Test suite (pytest).

## 3. Convenzioni di Sviluppo

### Stile del Codice
-   Seguire **PEP 8**.
-   Utilizzare **Type Hints** ovunque possibile.
-   Usare `async/await` per tutte le operazioni I/O bound (database, chiamate API esterne).
-   Logging strutturato con `loguru`: `from app.main import logger`.

### Database
-   Utilizzare sempre `get_db()` come dependency injection nelle route.
-   Per modifiche allo schema, generare sempre una migrazione Alembic:
    ```bash
    alembic revision --autogenerate -m "descrizione_modifica"
    alembic upgrade head
    ```

### Gestione Errori
-   Usare `HTTPException` per errori API noti.
-   Loggare gli errori con `logger.error()` prima di sollevare eccezioni, includendo contesto utile (es. `session_id`).

## 4. Workflow di Sviluppo

### Avvio Locale
Per avviare l'applicazione in locale:
```bash
./scripts/local.sh local-run
```
Oppure direttamente con uvicorn (se l'ambiente è attivato):
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Testing
Eseguire i test con pytest:
```bash
pytest
```

### Aggiunta Nuove Funzionalità
1.  **Modelli**: Se necessario, aggiornare `app/models/database_models.py` e creare la migrazione.
2.  **Logica**: Implementare la logica in un servizio dedicato in `app/services/`.
3.  **API**: Esporre la funzionalità tramite `app/routes.py`.
4.  **UI**: Se applicabile, aggiornare i template in `app/templates/`.

## 5. Componenti Chiave

### Unified Agent
L'agente unificato (`app/services/unified_agent.py`) è il cuore del chatbot. Gestisce:
-   Interazione con LLM.
-   Mantenimento del contesto della sessione.
-   Transizioni di stato del lifecycle (es. da `nuova_lead` a `in_target`).

### Sessioni e Lifecycle
Ogni conversazione è legata a una `SessionModel`. Il campo `current_lifecycle` traccia lo stato dell'utente nel funnel.

### Human Tasks & Notes
Il sistema supporta l'intervento umano:
-   **Human Tasks**: Compiti manuali assegnati agli operatori.
-   **Message Notes**: Feedback/annotazioni sui singoli messaggi per il fine-tuning o la review.

## 6. Regole Specifiche per l'AI Agent (Tu)

1.  **Non rompere il build**: Verifica sempre che il codice compili e che i test passino (se possibile eseguirli).
2.  **Sicurezza**: Non committare mai credenziali o chiavi API. Usa `.env`.
3.  **Contesto**: Quando modifichi `routes.py` o `services/`, controlla sempre le dipendenze e gli import.
4.  **UI/UX**: Quando modifichi i template HTML, mantieni lo stile esistente (CSS vanilla in `<style>` block o file esterni se presenti). Cerca di mantenere un aspetto "premium" come richiesto dalle linee guida generali.
