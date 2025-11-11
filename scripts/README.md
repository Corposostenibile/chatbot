# Scripts di Test per Chatbot Unificato

Questa cartella contiene script per testare il sistema chatbot unificato.

## Script Disponibili

### 1. `test_complete_flow.sh` 🚀
**Test completo del flusso conversazionale**

Testa tutte le transizioni di lifecycle:
- `nuova_lead` → `contrassegnato` → `in_target`
- Verifica le risposte dell'AI
- Controlla lo stato delle sessioni
- Testa la creazione di nuove sessioni

**Utilizzo:**
```bash
./scripts/test_complete_flow.sh
```

**Cosa testa:**
1. Salute iniziale del sistema
2. Messaggio iniziale (rimane in `nuova_lead`)
3. Espressione interesse (passa a `contrassegnato`)
4. Problema specifico + motivazione (passa a `in_target`)
5. Conferma interesse (rimane in `in_target`)
6. Nuova sessione (inizia correttamente)
7. Salute finale del sistema

### 2. `quick_test.sh` ⚡
**Test rapido di tutti gli endpoint**

Verifica velocemente che tutti gli endpoint funzionino:
- `/` - Root endpoint
- `/health` - Salute generale
- `/status` - Status dettagliato
- `/unified/health` - Salute agente unificato
- `/chat` - Invio messaggio

**Utilizzo:**
```bash
./scripts/quick_test.sh
```

### 3. Altri script esistenti

#### `deploy.sh`
Script per il deployment in produzione

#### `local-dev.sh`
Script per avviare l'ambiente di sviluppo locale

## Prerequisiti

- Server chatbot in esecuzione su `localhost:8081`
- `curl` installato
- Bash shell

## Output degli Script

Gli script forniscono output dettagliato con:
- 🚀 Indicatori di progresso
- 📤📥 Messaggi inviati/ricevuti
- 🔄 Stato lifecycle corrente
- 📊 Informazioni di sistema
- ✅ Conferme di successo

## Risoluzione Problemi

Se gli script falliscono:

1. **Verifica che il server sia in esecuzione:**
   ```bash
   curl http://localhost:8080/health
   ```

2. **Controlla i log del server**

3. **Verifica la porta corretta** (8081 di default)

## Esempi di Output

### Test Completo - Successo
```
🚀 Inizio test del flusso completo del chatbot
📋 Session ID: test_flow_1762159561
👤 User ID: test_user_flow
🌐 Base URL: http://localhost:8081

📤 STEP 1: Invio messaggio
💬 Messaggio: "Ciao"
📥 Risposta ricevuta: {...}
🔄 Lifecycle: nuova_lead
🔀 Cambiato: false

✅ TEST COMPLETATO CON SUCCESSO!
```

### Test Rapido - Successo
```
🚀 Test rapido del chatbot unificato
📍 Test endpoint root (/): ✅
📍 Test endpoint health (/health): ✅
📍 Test endpoint status (/status): ✅
✅ Test rapido completato!
```