# 🤖 Chatbot Corposostenibile

Un chatbot moderno per la qualificazione di lead nel settore nutrizione e psicologia integrata, costruito con FastAPI, PostgreSQL e Google Gemini AI.

## 🚀 Sviluppo Locale

### Prerequisiti

- Python 3.11+
- Git

### Setup Rapido

```bash
# Clona il repository
git clone <repository-url>
cd chatbot

# Configurazione completa automatica
./scripts/local.sh local-setup

# Avvia l'applicazione
./scripts/local.sh local-run
```

L'applicazione sarà disponibile su: http://127.0.0.1:8081

### Comandi Sviluppo Locale

```bash
# Status dell'ambiente
./scripts/local.sh local-status

# Installa dipendenze
./scripts/local.sh local-install

# Inizializza database locale
./scripts/local.sh local-db-init

# Esegui test
./scripts/local.sh local-test

# Linting e formattazione
./scripts/local.sh local-lint
./scripts/local.sh local-format

# Pulizia ambiente
./scripts/local.sh local-clean
```

### Configurazione

Il setup crea automaticamente:
- **Virtual Environment**: `.venv/`
- **Database SQLite**: `chatbot_local.db`
- **Configurazione**: `.env.local`

Modificare `.env.local` per configurare:
- `GOOGLE_AI_API_KEY`: La tua chiave API Google Gemini
- Altre impostazioni specifiche del locale

## 🐳 Deployment Production

### Prerequisiti

- Docker & Docker Compose
- Dominio configurato
- Certificati SSL (gestiti automaticamente)

### Setup Production

```bash
# Rendi eseguibile lo script
chmod +x scripts/server.sh
ln -sf scripts/server.sh server

# Avvia i servizi
./server server-start

# Setup SSL automatico
./server ssl-setup

# Verifica tutto funzioni
./server monitor-health
```

### Comandi Production

```bash
# Gestione server
./server server-start/stop/restart/status

# SSL e certificati
./server ssl-setup/ssl-check/ssl-renew

# Monitoraggio
./server monitor-health/monitor-resources

# Troubleshooting
./server troubleshoot

# Manutenzione
./server maintenance-update/maintenance-cleanup
```

## 📊 Dashboard e Monitoraggio

### Locale
- **Dashboard principale**: http://127.0.0.1:8081/
- **API Docs**: http://127.0.0.1:8081/docs
- **Sessioni DB**: http://127.0.0.1:8081/sessions
- **System Prompts**: http://127.0.0.1:8081/system-prompts

### Production
- **Dashboard principale**: https://your-domain.com/
- **API Docs**: https://your-domain.com/docs
- **Health Check**: https://your-domain.com/health

## 🏗️ Architettura

### Componenti Principali

- **FastAPI**: Framework web ASGI
- **SQLAlchemy**: ORM database con Alembic per migrazioni
- **Google Gemini AI**: Elaborazione linguaggio naturale
- **PostgreSQL**: Database production
- **SQLite**: Database sviluppo locale
- **Nginx**: Reverse proxy e SSL termination
- **Docker**: Containerizzazione

### Lifecycle Management

Il chatbot gestisce automaticamente il percorso cliente attraverso 5 fasi:
1. **NUOVA_LEAD**: Primo contatto e raccolta info base
2. **CONTRASSEGNATO**: Approfondimento informazioni
3. **IN_TARGET**: Presentazione soluzione
4. **LINK_DA_INVIARE**: Preparazione prenotazione
5. **LINK_INVIATO**: Conversione completata

### System Prompts

I prompt di sistema sono gestiti dinamicamente tramite database:
- Creazione/modifica tramite interfaccia web
- Versionamento automatico
- Attivazione/disattivazione immediata

## 🔧 Sviluppo

### Struttura Progetto

```
chatbot/
├── app/                    # Codice applicazione
│   ├── main.py            # Entry point FastAPI
│   ├── config.py          # Configurazioni
│   ├── database.py        # Connessione DB
│   ├── models/            # Modelli dati
│   ├── services/          # Logica business
│   ├── routes.py          # Endpoint API
│   ├── templates/         # Template HTML
│   └── data/              # Configurazioni lifecycle
├── scripts/               # Script di gestione
│   ├── local.sh          # Sviluppo locale
│   └── server.sh         # Production deployment
├── tests/                 # Test suite
├── alembic/              # Migrazioni database
└── docker/               # Configurazioni Docker
```

### Testing

```bash
# Esegui tutti i test
./scripts/local.sh local-test

# Con coverage
./scripts/local.sh local-test --cov=app --cov-report=html
```

### Code Quality

```bash
# Linting
./scripts/local.sh local-lint

# Formattazione automatica
./scripts/local.sh local-format
```

## 📝 API Endpoints

### Core Endpoints
- `POST /chat`: Interazione principale con AI
- `GET /health`: Health check servizio
- `GET /status`: Status dettagliato applicazione

### Management Endpoints
- `GET /`: Dashboard monitoraggio
- `GET /sessions`: Gestione sessioni
- `GET /system-prompts`: Gestione prompt AI
- `GET /flow`: Visualizzazione flusso end-to-end

### Development Endpoints
- `GET /docs`: Documentazione API interattiva
- `GET /preview`: Test interface chat

## 🔒 Sicurezza

- **HTTPS obbligatorio** in production
- **API Key** richiesta per Google Gemini
- **Input validation** su tutti gli endpoint
- **SQL injection protection** tramite SQLAlchemy
- **CORS configurato** per sicurezza

## 📈 Monitoraggio

### Metriche Disponibili
- **Health checks** automatici
- **Performance monitoring** container
- **Database connections** tracking
- **AI service availability** monitoring
- **SSL certificate** expiry tracking

### Logs
- **Strutturati** con livelli configurabili
- **Rotazione automatica** dei file
- **Centralizzati** per troubleshooting

## 🤝 Contributi

1. Fork del repository
2. Crea un branch per la feature
3. Scrivi test per le nuove funzionalità
4. Assicurati che tutti i test passino
5. Crea una Pull Request

### Linee Guida Sviluppo

- **Python 3.11+** obbligatorio
- **Black** per formattazione codice
- **Flake8** per linting
- **isort** per ordinamento import
- **pytest** per testing
- **mypy** per type checking

## 📄 Licenza

Questo progetto è distribuito sotto licenza proprietaria di Corposostenibile.

## 📞 Supporto

Per supporto tecnico o domande:
- 📧 Email: supporto@corposostenibile.it
- 📱 WhatsApp: Contattaci per assistenza diretta
- 📚 Docs: Consulta la documentazione completa in `/docs/`