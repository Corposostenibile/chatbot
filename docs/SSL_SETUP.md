# Configurazione SSL per Webhook respond.io

## Panoramica
Questo documento spiega come configurare SSL gratuito con Let's Encrypt per ricevere webhook sicuri da respond.io.

## Prerequisiti
- Dominio DuckDNS configurato: `corposostenibile.duckdns.org`
- Applicazione avviata con `./scripts/server.sh docker-dev`
- Nginx attivo e funzionante

## Setup SSL Automatico

### 1. Setup Completo SSL
```bash
# Assicurati che l'app sia avviata
./scripts/server.sh docker-dev

# Poi fai il setup SSL
./scripts/server.sh ssl-setup
```

Questo comando:
- Installa Certbot
- Ottiene il certificato SSL da Let's Encrypt usando **webroot challenge**
- Configura Nginx come reverse proxy SSL
- Riavvia i servizi

### 2. Come Funziona il Webroot Challenge
- Nginx rimane **ATTIVO** durante tutto il processo
- I file di challenge vengono serviti da `/var/www/html/.well-known/acme-challenge/`
- Non richiede modifiche al DNS
- Non richiede di fermare il server

### 2. Verifica Configurazione
```bash
./scripts/server.sh ssl-check
```

### 3. Rinnovo Manuale (se necessario)
```bash
./scripts/server.sh ssl-renew
```

## Rinnovo Automatico
I certificati Let's Encrypt scadono ogni 90 giorni. Per rinnovo automatico:

### Aggiungi Cron Job
```bash
# Modifica crontab
crontab -e

# Aggiungi questa riga per rinnovo alle 12:00 ogni giorno
0 12 * * * /home/manu/chatbot/scripts/ssl.sh renew
```

### Verifica Cron
```bash
# Controlla cron jobs attivi
crontab -l
```

## Configurazione respond.io

### 1. URL Webhook Sicuro
Usa questo URL per i webhook respond.io:
```
https://corposostenibile.duckdns.org/chat
```

### 2. Verifica Funzionamento
```bash
# Test endpoint health
curl -k https://corposostenibile.duckdns.org/health

# Test endpoint chat (POST)
curl -k -X POST https://corposostenibile.duckdns.org/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "from": "test"}'
```

## Troubleshooting

### Errore "Connection refused"
- Assicurati che l'app sia avviata: `./scripts/server.sh docker-dev`
- Verifica che Nginx sia attivo: `docker-compose ps`

### Errore Certificato
- Ricontrolla che il dominio DuckDNS sia corretto
- Verifica che le porte 80 e 443 siano aperte sul firewall
- Riprova setup: `./scripts/server.sh ssl-setup`

### Errore Webroot
- Verifica che la directory `webroot` esista: `ls -la webroot/`
- Controlla che Nginx possa accedere ai file: `docker-compose logs nginx`
- Assicurati che l'app sia avviata prima del setup SSL

## Sicurezza
- I certificati sono emessi da Let's Encrypt (CA affidabile)
- Nginx è configurato con TLS 1.2/1.3 moderni
- Le chiavi private sono memorizzate in container Docker sicuri

## Costi
- **GRATUITO**: Let's Encrypt non ha costi
- **AUTOMATICO**: Rinnovo ogni 90 giorni senza intervento manuale