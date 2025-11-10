# 🤖 Chatbot con FastAPI

Un chatbot moderno e scalabile costruito con FastAPI, ottimizzato per Google Cloud Run. Gestisce conversazioni con potenziali clienti nel settore nutrizione/psicologia.

## Panoramica dell'Architettura

Questo progetto espone un'API basata su FastAPI per la gestione di conversazioni con potenziali clienti di Corposostenibile nel settore nutrizione/psicologia. L'app espone un endpoint che viene chiamato da respond.io tramite webhook e utilizza Google Gemini AI per automatizzare le risposte e transitare i lead attraverso le fasi del ciclo di vita: `NUOVA_LEAD` → `CONTRASSEGNATO` → `IN_TARGET` → `LINK_DA_INVIARE` → `LINK_INVIATO`.

Le sessioni e le conversazioni sono persistite in un database PostgreSQL per garantire la continuità tra riavvii dell'applicazione.

**Componenti Chiave:**
- `app/main.py`: Endpoint FastAPI (`/chat`, `/health`, `/status`, `/session/{id}`)
- `app/services/unified_agent.py`: Gestore conversazioni alimentato da AI con decisioni sul ciclo di vita
- `app/models/lifecycle.py`: Fasi del ciclo di vita e modelli di transizione
- `app/models/database_models.py`: Modelli SQLAlchemy per sessioni e messaggi
- `app/database.py`: Configurazione connessione database
- `app/data/lifecycle_config.py`: Script specifici per fase e trigger di transizione

## 📊 Visualizzazione Flusso End-to-End

Abbiamo creato una **visualizzazione HTML interattiva** del flusso completo con diagrammi Mermaid!

```bash
# Avvia il server
./scripts/run_server.sh

# Poi vai a: http://localhost:8080/flow
```

**Caratteristiche:**
- ✅ 8 sezioni navigabili
- ✅ 6 diagrammi Mermaid interattivi
- ✅ Timeline dettagliata (ms-level)
- ✅ Esempio reale con Marco
- ✅ Responsive design
- ✅ Zero dipendenze frontend pesanti

[Leggi il Quick Start →](FLOW_VISUALIZATION_START.md) | [Guida Completa →](docs/FLOW_VISUALIZATION_GUIDE.md)

## Flusso di Sviluppo

- **Setup**: `./scripts/local-dev.sh setup` (installa dipendenze Poetry, crea `.env`)
- **Esegui localmente**: `./scripts/local-dev.sh dev` (FastAPI nativa con Poetry + PostgreSQL in Docker)
- **Visualizza Flusso**: `./scripts/run_server.sh` (Avvia server + apri http://localhost:8080/flow)
- **Test**: `./scripts/local-dev.sh test` (pytest con coverage)
- **Formatta**: `./scripts/local-dev.sh format` (black + isort + flake8)
- **Deploy**: `./scripts/deploy.sh` (Cloud Build → Cloud Run)

## Tech Stack

- **Python 3.11** - Linguaggio di programmazione
- **FastAPI** - Framework web moderno e veloce (esecuzione nativa con Poetry)
- **PostgreSQL** - Database relazionale (containerizzato con Docker)
- **Docker** - Containerizzazione solo per database
- **Poetry** - Gestione dipendenze e packaging per l'applicazione
- **Google Cloud Run** - Deployment serverless
- **Uvicorn** - Server ASGI ad alte prestazioni
- **SQLAlchemy** - ORM per database con supporto async
- **Google Gemini AI** - Intelligenza artificiale per conversazioni

## Struttura del Progetto

```
chatbot/
├── app/                    # Codice dell'applicazione
│   ├── main.py            # Applicazione FastAPI principale
│   ├── config.py          # Configurazioni
│   ├── database.py        # Configurazione database
│   ├── models/
│   │   ├── lifecycle.py   # Modelli ciclo di vita
│   │   └── database_models.py # Modelli SQLAlchemy
│   ├── services/
│   │   └── unified_agent.py # Logica AI conversazioni
│   └── data/
│       └── lifecycle_config.py # Configurazioni fasi
├── tests/                 # Test automatizzati
├── scripts/               # Script di utilità
│   ├── deploy.sh         # Script per deployment
│   └── local-dev.sh      # Script per sviluppo locale
├── docker-compose.dev.yml # Solo PostgreSQL per sviluppo
├── pyproject.toml        # Configurazione Poetry
├── Dockerfile            # Docker per produzione
└── README.md
```

## Setup Locale

### Prerequisiti

- Python 3.11+
- Poetry ([Installazione](https://python-poetry.org/docs/#installation))
- Docker (solo per database PostgreSQL)

### Installazione Rapida

```bash
# Clona il repository
git clone <your-repo-url>
cd chatbot

# Setup automatico con script
./scripts/local-dev.sh setup

# Oppure manualmente:
# 1. Installa dipendenze
poetry install

# 2. Crea file di configurazione
cp .env.example .env

# 3. Modifica le variabili in .env secondo le tue necessità
# Nota: DATABASE_URL è già configurato per PostgreSQL locale con Docker
```

### Avvio Sviluppo

```bash
# Metodo 1: Con script di utilità (raccomandato - avvia automaticamente DB)
./scripts/local-dev.sh dev

# Metodo 2: Direttamente con Poetry (assicurati che PostgreSQL sia attivo)
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# Metodo 3: Con Docker Compose (solo per produzione/test)
docker-compose up --build
```

**Nota**: Lo script `local-dev.sh dev` avvia automaticamente PostgreSQL con Docker e poi l'app FastAPI con Poetry.

L'applicazione sarà disponibile su:
- **API**: http://localhost:8080
- **Documentazione**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health

## Pattern di Codifica

### Formato Risposta AI
Richiedi sempre risposte JSON dall'AI con questa struttura esatta:
```json
{
  "message": "Risposta conversazionale naturale",
  "should_change_lifecycle": true/false,
  "new_lifecycle": "nome_fase",
  "reasoning": "Spiegazione della decisione",
  "confidence": 0.0-1.0
}
```

### Gestione del Ciclo di Vita
- Usa l'enum `LifecycleStage` per le fasi
- Memorizza la cronologia conversazioni (limita a ultimi 20 messaggi)
- Transita solo con confidenza ≥ 0.7
- Non menzionare mai i cicli di vita agli utenti

### Gestione Errori
- Risposte di fallback quando l'AI fallisce (vedi `_create_fallback_response`)
- Gestori eccezioni globali in `main.py`
- Health check per disponibilità AI

### Configurazione
- Usa `Settings` Pydantic da `config.py` (carica da `.env`)
- Variabili ambiente: `GOOGLE_AI_API_KEY`, `DEBUG`, `LOG_LEVEL`, `DATABASE_URL`

### Testing
- Usa `TestClient` FastAPI per test endpoint
- Mock risposte AI per testing deterministico
- Test transizioni ciclo di vita e gestione sessioni

## Docker

### Database Locale
Il progetto utilizza PostgreSQL come database. Per lo sviluppo locale:

```bash
# Avvia solo il database (automatico con ./scripts/local-dev.sh dev)
docker-compose -f docker-compose.dev.yml up -d postgres

# Ferma il database
./scripts/local-dev.sh db-stop

# Verifica stato database
docker-compose -f docker-compose.dev.yml ps
```

### Build Locale

```bash
# Build immagine di produzione
docker build -t chatbot:latest .

# Build immagine di sviluppo
docker build -f Dockerfile.dev -t chatbot:dev .

# Avvio con Docker Compose
docker-compose up --build
```

## Configurazione

### Variabili d'Ambiente

Copia `.env.example` in `.env` e configura:

```bash
# Configurazione dell'applicazione
APP_NAME=Chatbot
DEBUG=false
LOG_LEVEL=info

# Server
HOST=0.0.0.0
PORT=8080

# Security
SECRET_KEY=your-secret-key-here

# Database (già configurato per sviluppo locale)
DATABASE_URL=postgresql+asyncpg://chatbot:password@localhost:5432/chatbot

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id

# API Keys (aggiungi le tue)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_AI_API_KEY=your-google-ai-key
```

## API Endpoints

### Principali

- `GET /` - Informazioni base
- `GET /health` - Health check per Cloud Run
- `GET /status` - Status dettagliato
- `POST /chat` - Endpoint principale del chatbot
- `GET /session/{session_id}` - Informazioni sessione

### Esempio Utilizzo

```bash
# Health check
curl https://your-app-url/health

# Chat
curl -X POST https://your-app-url/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Ciao!", "user_id": "user123"}'
```

## Deployment su Google Cloud Run

### Setup Iniziale

1. **Installa Google Cloud CLI**:
   ```bash
   # Su Ubuntu/Debian
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. **Configura il progetto**:
   ```bash
   # Imposta il PROJECT_ID
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   
   # Login
   gcloud auth login
   gcloud config set project $GOOGLE_CLOUD_PROJECT
   ```

### Deployment Automatico

```bash
# Deployment con script automatico
./scripts/deploy.sh

# Il script farà automaticamente:
# - Abiliterà le API necessarie
# - Farà build dell'immagine
# - Farà deploy su Cloud Run
# - Mostrerà l'URL finale
```

## Sicurezza

- ✅ Utente non-root nel container
- ✅ Variabili d'ambiente per secrets
- ✅ CORS configurato
- ✅ Health checks
- ✅ Logging strutturato
- ✅ Gestione errori globale

## Performance

- **Cold Start**: ~2-3 secondi
- **Memoria**: 512Mi (configurabile)
- **CPU**: 1 vCPU (configurabile)
- **Concorrenza**: 80 richieste per istanza
- **Scaling**: 0-10 istanze (configurabile)

## File Chiave da Riferire

- `app/services/unified_agent.py`: Logica conversazione AI
- `app/data/lifecycle_config.py`: Script fasi e trigger
- `scripts/local-dev.sh`: Comandi sviluppo
- `cloudbuild.yaml`: Pipeline CI/CD

---

**Fatto con ❤️ e FastAPI**