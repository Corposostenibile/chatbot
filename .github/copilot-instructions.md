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

## Flusso di Sviluppo
- **Setup**: `./scripts/server.sh setup` (installa dipendenze Poetry, crea `.env`)
- **Esegui localmente**: `./scripts/server.sh dev` (Poetry + uvicorn con reload)
- **Test**: `./scripts/server.sh test` (pytest con coverage)
- **Formatta**: `./scripts/server.sh format` (black + isort + flake8)
- **Deploy**: `./scripts/deploy.sh` (Cloud Build → Cloud Run)

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
- `scripts/server.sh`: Comandi sviluppo
- `cloudbuild.yaml`: Pipeline CI/CD</content>

# IMPORTANTE: Non avviare mai il server, è già attivo!