# 🚀 Script di Gestione Server Chatbot

Questo script fornisce un'interfaccia unificata per gestire completamente il server Nginx + SSL + Docker del chatbot.

## 📋 Panoramica

Lo script `server.sh` automatizza tutte le operazioni di:
- ✅ Gestione server (avvio/arresto/riavvio)
- ✅ Configurazione SSL Let's Encrypt
- ✅ Monitoraggio e health checks
- ✅ Troubleshooting automatico
- ✅ Manutenzione e aggiornamenti

## 🚀 Installazione Rapida

```bash
# Dalla directory del progetto
chmod +x scripts/server.sh
ln -sf scripts/server.sh server

# Ora puoi usare ./server
```

## 📖 Uso Base

```bash
# Mostra aiuto completo
./server help

# Avvia il server
./server server-start

# Verifica tutto funzioni
./server monitor-health

# Setup SSL completo
./server ssl-setup
```

## 🔧 Workflow Tipico

### Setup Iniziale
```bash
./server server-start    # Avvia servizi
./server ssl-setup      # Configura SSL
./server monitor-health # Verifica tutto OK
```

### Gestione Quotidiana
```bash
./server server-status   # Controlla status
./server ssl-check      # Verifica SSL
```

### Troubleshooting
```bash
./server troubleshoot    # Diagnosi automatica
./server server-logs     # Visualizza logs
```

## 📊 Monitoraggio Integrato

Lo script include monitoraggio completo:
- Health checks automatici
- Monitoraggio risorse Docker
- Verifica SSL e certificati
- Controlli database
- Alert per problemi critici

## 🔄 Automazione

### Cron Jobs Automatici
```bash
# Aggiungi al crontab (crontab -e):
0 * * * * /home/manu/chatbot/server monitor-health  # Ogni ora
```

### Rinnovo SSL Automatico
Configurato automaticamente durante `ssl-setup` per rinnovare ogni giorno a mezzogiorno.

## 📁 Struttura File

```
logs/           # Log operazioni
ssl/           # Certificati SSL
webroot/       # Challenge Let's Encrypt
```

## 🆘 Supporto

- **Documentazione completa**: `docs/Nginx_SSL_Documentation.md`
- **Diagnosi problemi**: `./server troubleshoot`
- **Logs dettagliati**: `./server server-logs`

## 🔒 Sicurezza

- Validazione certificati SSL
- Controlli integrità configurazione
- Accesso root limitato alle operazioni necessarie

---

*Script Version: 1.0*
*Creato per: Chatbot Corposostenibile*