# 🤖 Chatbot con FastAPI

Un chatbot moderno e scalabile costruito con FastAPI, ottimizzato per Google Cloud Run.

## 🚀 Tech Stack

- **Python 3.11** - Linguaggio di programmazione
- **FastAPI** - Framework web moderno e veloce
- **Docker** - Containerizzazione
- **Poetry** - Gestione dipendenze e packaging
- **Google Cloud Run** - Deployment serverless
- **Uvicorn** - Server ASGI ad alte prestazioni

## 📁 Struttura del Progetto

```
chatbot/
├── app/                    # Codice dell'applicazione
│   ├── __init__.py
│   ├── main.py            # Applicazione FastAPI principale
│   └── config.py          # Configurazioni
├── tests/                 # Test automatizzati
│   ├── __init__.py
│   └── test_main.py
├── scripts/               # Script di utilità
│   ├── deploy.sh         # Script per deployment
│   └── local-dev.sh      # Script per sviluppo locale
├── docs/                 # Documentazione
├── .github/workflows/    # GitHub Actions (futuro)
├── pyproject.toml        # Configurazione Poetry
├── Dockerfile            # Docker per produzione
├── Dockerfile.dev       # Docker per sviluppo
├── docker-compose.yml   # Compose per produzione
├── docker-compose.dev.yml # Compose per sviluppo
├── cloudbuild.yaml      # Configurazione Cloud Build
├── service.yaml         # Configurazione Cloud Run
├── .env.example         # Template variabili d'ambiente
├── .gitignore
└── README.md
```

## 🛠️ Setup Locale

### Prerequisiti

- Python 3.11+
- Poetry ([Installazione](https://python-poetry.org/docs/#installation))
- Docker (opzionale, per containerizzazione)
- Google Cloud CLI (per deployment)

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

**Nota**: Lo script `local-dev.sh dev` avvia automaticamente PostgreSQL con Docker e poi l'app con Poetry.

L'applicazione sarà disponibile su:
- **API**: http://localhost:8080
- **Documentazione**: http://localhost:8080/docs
- **Health Check**: http://localhost:8080/health

## 🧪 Test e Qualità del Codice

```bash
# Esegui tutti i test
./scripts/local-dev.sh test

# Oppure manualmente:
poetry run pytest tests/ -v --cov=app --cov-report=term-missing

# Formattazione codice
./scripts/local-dev.sh format

# Oppure manualmente:
poetry run black app/ tests/
poetry run isort app/ tests/
poetry run flake8 app/ tests/
```

## 🐳 Docker

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

## ☁️ Deployment su Google Cloud Run

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

### Deployment Manuale

```bash
# 1. Abilita le API
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# 2. Build e deploy
gcloud builds submit --config cloudbuild.yaml .

# 3. Ottieni l'URL del servizio
gcloud run services describe chatbot --region=europe-west1 --format="value(status.url)"
```

### Configurazione Avanzata

Per configurazioni avanzate, modifica <mcfile name="service.yaml" path="/home/ubuntu/chatbot/service.yaml"></mcfile>:

- **Scaling**: Modifica `minScale` e `maxScale`
- **Risorse**: Cambia CPU e memoria
- **Variabili d'ambiente**: Aggiungi nuove env vars
- **Health checks**: Personalizza i controlli di salute

## 🔧 Configurazione

### Variabili d'Ambiente

Copia <mcfile name=".env.example" path="/home/ubuntu/chatbot/.env.example"></mcfile> in `.env` e configura:

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

## 📚 API Endpoints

### Principali

- `GET /` - Informazioni base
- `GET /health` - Health check per Cloud Run
- `GET /status` - Status dettagliato
- `POST /chat` - Endpoint principale del chatbot

### Esempio Utilizzo

```bash
# Health check
curl https://your-app-url/health

# Chat
curl -X POST https://your-app-url/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Ciao!", "user_id": "user123"}'
```

## 🔍 Monitoraggio e Logs

```bash
# Visualizza logs in tempo reale
gcloud run services logs read chatbot --region=europe-west1 --follow

# Logs recenti
gcloud run services logs read chatbot --region=europe-west1 --limit=50

# Metriche del servizio
gcloud run services describe chatbot --region=europe-west1
```

## 🚀 Sviluppo e Contributi

### Workflow di Sviluppo

1. **Setup**: `./scripts/local-dev.sh setup`
2. **Sviluppo**: `./scripts/local-dev.sh dev` (avvia DB + app)
3. **Test**: `./scripts/local-dev.sh test`
4. **Format**: `./scripts/local-dev.sh format`
5. **Build**: `./scripts/local-dev.sh build`
6. **Stop DB**: `./scripts/local-dev.sh db-stop`
7. **Deploy**: `./scripts/deploy.sh`

### Aggiungere Nuove Funzionalità

1. Modifica <mcfile name="app/main.py" path="/home/ubuntu/chatbot/app/main.py"></mcfile> per nuovi endpoint
2. Aggiungi test in <mcfolder name="tests" path="/home/ubuntu/chatbot/tests"></mcfolder>
3. Aggiorna la documentazione
4. Testa localmente
5. Deploy

## 🔒 Sicurezza

- ✅ Utente non-root nel container
- ✅ Variabili d'ambiente per secrets
- ✅ CORS configurato
- ✅ Health checks
- ✅ Logging strutturato
- ✅ Gestione errori globale

## 📈 Performance

- **Cold Start**: ~2-3 secondi
- **Memoria**: 512Mi (configurabile)
- **CPU**: 1 vCPU (configurabile)
- **Concorrenza**: 80 richieste per istanza
- **Scaling**: 0-10 istanze (configurabile)

## 🆘 Troubleshooting

### Problemi Comuni

1. **Build fallisce**:
   ```bash
   # Verifica Poetry
   poetry check
   
   # Reinstalla dipendenze
   poetry install --no-cache
   ```

2. **Deploy fallisce**:
   ```bash
   # Verifica autenticazione
   gcloud auth list
   
   # Verifica progetto
   gcloud config get-value project
   ```

3. **App non risponde**:
   ```bash
   # Controlla logs
   gcloud run services logs read chatbot --region=europe-west1
   
   # Verifica health check
   curl https://your-app-url/health
   ```

## 📞 Supporto

- **Documentazione API**: `/docs` (solo in sviluppo)
- **Health Check**: `/health`
- **Status**: `/status`

## 📄 Licenza

[Inserisci qui la tua licenza]

---

**Fatto con ❤️ e FastAPI**