# 🤖 Linee Guida per la Codifica AI del Chatbot

## Panoramica dell'Architettura
Questo progetto espone un'API basata su FastAPI per la gestione di conversazioni con potenziali clienti di Corposostenibile nel settore nutrizione/psicologia. L'app espone un endpoint che viene chiamato da respond.io tramite webhook e utilizza Google Gemini AI per automatizzare le risposte e transitare i lead attraverso le fasi del ciclo di vita: `NUOVA_LEAD` → `CONTRASSEGNATO` → `IN_TARGET` → `LINK_DA_INVIARE` → `LINK_INVIATO`.

Le sessioni e le conversazioni sono persistite in un database PostgreSQL per garantire la continuità tra riavvii dell'applicazione.

**Componenti Chiave:**
- `app/main.py`: Endpoint FastAPI (`/chat`, `/health`, `/status`, `/session/{id}`)
- `app/services/unified_agent.py`: Gestore conversazioni alimentato da AI con decisioni sul ciclo di vita
- `app/services/system_prompt_service.py`: Servizio per gestione system prompts nel database
- `app/routes.py`: Route per dashboard, monitoraggio e gestione prompts
- `app/models/lifecycle.py`: Fasi del ciclo di vita e modelli di transizione
- `app/models/database_models.py`: Modelli SQLAlchemy per sessioni, messaggi e system prompts
- `app/models/api_models.py`: Modelli Pydantic per API requests/responses
- `app/database.py`: Configurazione connessione database
- `app/data/lifecycle_config.py`: Script specifici per fase e trigger di transizione
- `app/data/snippets.py`: Gestione snippets conversazionali
- `app/templates/`: Template HTML per dashboard e interfacce web
- `scripts/server.sh`: Script di gestione server completo per produzione
- `scripts/local.sh`: Script per sviluppo locale senza Docker
- `scripts/ssl.sh`: Script dedicato per configurazione SSL
- `alembic/`: Migrazioni database (sessions, messages, system_prompts)
- `context7_mcp_integration.md`: Integrazione MCP per documentazione dinamica

## Flusso di Sviluppo
- **Installazione dipendenze**: `./scripts/server.sh dependencies-install` (installa dipendenze Poetry)
- **Aggiornamento dipendenze**: `./scripts/server.sh dependencies-update` (aggiorna dipendenze Poetry)
- **Verifica dipendenze**: `./scripts/server.sh dependencies-check` (controlla stato dipendenze)
- **Avvio server completo**: `./scripts/server.sh server-start` (avvia Nginx + SSL + Docker)
- **Status server**: `./scripts/server.sh server-status` (mostra status completo)
- **Monitoraggio health**: `./scripts/server.sh monitor-health` (controlli automatici)
- **Setup SSL**: `./scripts/server.sh ssl-setup` (configura SSL Let's Encrypt)
- **Troubleshooting**: `./scripts/server.sh troubleshoot` (diagnosi automatica problemi)
- **Deploy**: `./scripts/deploy.sh` (Cloud Build → Cloud Run)

## Script server.sh - Gestione Server Completa

Lo script `scripts/server.sh` è lo strumento principale per gestire l'intero stack di produzione:

### 🖥️ Gestione Server
- `server-start`: Avvia Nginx, chatbot e database
- `server-stop`: Arresta tutti i servizi
- `server-restart`: Riavvia tutti i servizi
- `server-status`: Mostra status completo (container, app, SSL, risorse)
- `server-logs [nginx|chatbot|postgres|all]`: Visualizza logs dei servizi

### 🔒 Gestione SSL
- `ssl-setup`: Setup completo SSL Let's Encrypt con rinnovo automatico
- `ssl-renew`: Rinnova manualmente il certificato SSL
- `ssl-check`: Verifica validità e scadenza del certificato

### 📦 Gestione Dipendenze
- `dependencies-install`: Installa dipendenze Poetry
- `dependencies-update`: Aggiorna dipendenze Poetry
- `dependencies-check`: Verifica stato dipendenze e ambiente virtuale
- `dependencies-lock`: Aggiorna poetry.lock

### 📊 Monitoraggio
- `monitor-health`: Controlli automatici di health (container, app, DB, SSL, disco)
- `monitor-resources`: Monitoraggio utilizzo risorse container

### 🔧 Troubleshooting
- `troubleshoot`: Diagnosi automatica problemi comuni (DNS, porte, container, comunicazione)

### ⚙️ Manutenzione
- `maintenance-update`: Aggiornamento completo sistema e riavvio
- `maintenance-cleanup`: Pulizia immagini, container e log inutilizzati

## Script local.sh - Sviluppo Locale

Lo script `scripts/local.sh` è specializzato per lo sviluppo locale con Docker solo per la containerizzazione del Database Postgres

### 🐍 Ambiente di Sviluppo
- `local-setup`: Configurazione iniziale completa (venv + deps + db)
- `local-install`: Installa dipendenze Poetry in ambiente virtuale
- `local-clean`: Pulisce completamente l'ambiente locale
- `local-status`: Mostra stato completo dell'ambiente di sviluppo

### 🗄️ Gestione Database Locale
- `local-db-start`: Avvia container PostgreSQL per sviluppo
- `local-db-stop`: Ferma container PostgreSQL
- `local-db-init`: Inizializza database locale con migrazioni

### 🚀 Esecuzione e Testing
- `local-run`: Avvia l'applicazione in modalità development con auto-reload
- `local-test`: Esegue suite di test completa
- `local-lint`: Esegue linting con flake8, black, isort
- `local-format`: Formatta automaticamente il codice

### ⚙️ Configurazione
Crea automaticamente `.env.local` con configurazioni per sviluppo:
- Database: PostgreSQL locale o SQLite
- Debug: abilitato
- Port: 8082 (configurabile)
- Log Level: DEBUG
- Google AI API Key precaricata

### 📦 Dipendenze
- Gestione automatica ambiente virtuale Python 3.11+
- Installazione Poetry se non presente
- Tool di sviluppo: pytest, flake8, black, isort, mypy

## System Prompts Service

### Panoramica
Il `SystemPromptService` gestisce i system prompts nel database, permettendo la modifica dinamica del comportamento dell'AI senza riavviare l'applicazione.

### Funzionalità Principali
- **Gestione CRUD**: Creazione, lettura, aggiornamento e eliminazione prompts
- **Prompt Attivo**: Un solo prompt può essere attivo alla volta
- **Versioning**: Supporto per versioni multiple dei prompts
- **Inizializzazione Automatica**: Setup automatico del prompt di default

### Metodi Chiave
- `get_active_prompt()`: Recupera il prompt attualmente attivo
- `get_all_prompts()`: Lista tutti i prompts nel database
- `create_prompt(name, content, version, description)`: Crea nuovo prompt
- `update_prompt(prompt_id, **kwargs)`: Aggiorna prompt esistente
- `set_active_prompt(prompt_id)`: Attiva un prompt specifico
- `delete_prompt(prompt_id)`: Elimina prompt dal database
- `initialize_default_prompt()`: Setup prompt di default se non esistente

### Database Schema
```sql
CREATE TABLE system_prompts (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    content TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    version VARCHAR NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### API Endpoints
- `GET /system-prompts`: Lista tutti i prompts
- `GET /system-prompts/{id}`: Dettagli prompt specifico
- `POST /system-prompts`: Crea nuovo prompt
- `PUT /system-prompts/{id}`: Aggiorna prompt
- `DELETE /system-prompts/{id}`: Elimina prompt
- `POST /system-prompts/{id}/activate`: Attiva prompt specifico

## Dashboard e Interfacce Web

### Template HTML Disponibili
- `chat.html`: Interfaccia chat diretta con il bot
- `conversation.html`: Visualizzazione dettagliata singola conversazione
- `flow_visualization.html`: Mappa visiva del ciclo di vita conversazioni
- `monitoring_dashboard.html`: Dashboard monitoraggio in tempo reale
- `sessions.html`: Gestione e列表a sessioni attive
- `system_prompts.html`: Interfaccia per gestire system prompts

### Funzionalità Dashboard
- **Monitoraggio Real-time**: Statistiche conversazioni e performance
- **Gestione Sessioni**: Visualizzazione e controllo sessioni attive
- **Visualizzazione Flussi**: Mappa dei transitioni tra lifecycle stages
- **CRUD Prompts**: Interfaccia completa per gestire system prompts
- **Analytics**: Metriche di conversione e engagement

### Accesso Dashboard
- **URL Base**: `http://localhost:8082` (dev) o dominio configurato (prod)
- **Routes principali**:
  - `/`: Dashboard principale
  - `/sessions`: Gestione sessioni
  - `/conversation/{id}`: Dettagli conversazione
  - `/flow`: Visualizzazione flussi
  - `/system-prompts`: Gestione prompts
  - `/monitoring`: Dashboard monitoraggio

# IMPORTANTE: Non avviare mai il server, è già attivo!
