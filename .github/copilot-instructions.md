# 🤖 Linee Guida per la Codifica AI del Chatbot

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
- `scripts/server.sh`: Script di gestione server completo (vedi sezione dedicata)

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
Esempio da `unified_agent.py`:
```python
unified_prompt = f"""...FORMATO RISPOSTA RICHIESTO:
{{
    "message": "La tua risposta conversazionale al cliente",
    "should_change_lifecycle": true/false,
    "new_lifecycle": "{next_stage.value}",
    "reasoning": "Spiegazione del perché hai deciso...",
    "confidence": 0.0-1.0
}}"""
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
- Variabili ambiente: `GOOGLE_AI_API_KEY`, `DEBUG`, `LOG_LEVEL`

### Testing
- Usa `TestClient` FastAPI per test endpoint
- Mock risposte AI per testing deterministico
- Test transizioni ciclo di vita e gestione sessioni

### Docker & Deployment
- Dockerfile multi-stage per produzione (utente non-root)
- Cloud Run con 0-10 istanze, 512Mi memoria
- Health check su `/health` endpoint
- Usa libreria `datapizza-ai` per Google Gemini integration

## File Chiave da Riferire
- `app/services/unified_agent.py`: Logica conversazione AI
- `app/data/lifecycle_config.py`: Script fasi e trigger
- `scripts/server.sh`: Script gestione server completo (Nginx, SSL, Docker, monitoraggio)
- `cloudbuild.yaml`: Pipeline CI/CD</content>

# IMPORTANTE: Non avviare mai il server, è già attivo!