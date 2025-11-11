# 🏗️ Documentazione Server Nginx + SSL per Chatbot

## Panoramica Architettura

Il server è configurato con un'architettura containerizzata che utilizza Docker Compose per orchestrare i seguenti servizi:

- **Nginx**: Reverse proxy con terminazione SSL
- **Chatbot**: Applicazione FastAPI che gestisce le conversazioni AI
- **PostgreSQL**: Database per persistenza dati
- **Let's Encrypt**: Certificati SSL automatici

### Diagramma Architettura

```
Internet
    ↓
[ Nginx (Porte 80/443) ]
    ↓ (HTTPS)
[ Chatbot (Porta 8081) ]
    ↓
[ PostgreSQL (Porta 5432) ]
```

## 📋 Configurazione Nginx

### File di Configurazione: `nginx.conf`

```nginx
server {
    listen 80;
    server_name corposostenibile.duckdns.org;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name corposostenibile.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/corposostenibile.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/corposostenibile.duckdns.org/privkey.pem;

    # Configurazioni SSL moderne
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;

    # Servire i file di challenge Let's Encrypt anche su HTTPS
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }

    location / {
        proxy_pass http://chatbot:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Spiegazione Configurazione

#### Server HTTP (Porta 80)
- **Scopo**: Reindirizza tutto il traffico HTTP a HTTPS
- **Configurazione**: `return 301 https://$server_name$request_uri;`
- **Sicurezza**: Forza l'uso di HTTPS per tutti gli accessi

#### Server HTTPS (Porta 443)
- **SSL/TLS**: Configurato con certificati Let's Encrypt
- **Protocolli**: Supporta TLS 1.2 e 1.3
- **Cipher Suites**: Priorità alle suite ECDHE moderne
- **HTTP/2**: Abilitato per prestazioni migliori

#### Location /.well-known/acme-challenge/
- **Scopo**: Serve i file di challenge per Let's Encrypt
- **Path**: `/var/www/html/.well-known/acme-challenge/`
- **Importanza**: Necessario per rinnovi automatici SSL

#### Location / (Proxy)
- **Backend**: `http://chatbot:8081` (nome servizio Docker)
- **Headers**: Preserva informazioni client originali
- **Protocol**: Passa il protocollo originale (HTTP/HTTPS)

## 🔒 Configurazione SSL Let's Encrypt

### Metodo di Autenticazione: Webroot Challenge

Il setup utilizza il **webroot challenge** invece del DNS challenge perché:
- ✅ Non richiede accesso al pannello DNS
- ✅ Funziona con domini DuckDNS
- ✅ Può essere automatizzato completamente
- ✅ Nginx rimane attivo durante il rinnovo

### Processo di Setup SSL

1. **Installazione Certbot**
   ```bash
   sudo apt update && sudo apt install -y certbot
   ```

2. **Ottieni Certificato**
   ```bash
   sudo certbot certonly --webroot \
     --webroot-path /home/manu/chatbot/webroot \
     --agree-tos \
     --email admin@corposostenibile.duckdns.org \
     --domain corposostenibile.duckdns.org
   ```

3. **Configurazione Nginx**
   - Certificati montati in `/etc/letsencrypt`
   - Webroot montato in `/var/www/html`

### Rinnovo Automatico

I certificati Let's Encrypt scadono ogni 90 giorni. Il rinnovo è configurato con:

```bash
# Cron job per rinnovo automatico
0 12 * * * /home/manu/chatbot/scripts/ssl.sh renew
```

### Verifica SSL

```bash
# Test HTTP → HTTPS redirect
curl -I http://corposostenibile.duckdns.org

# Test HTTPS
curl -I https://corposostenibile.duckdns.org

# Verifica certificato
openssl s_client -servername corposostenibile.duckdns.org -connect corposostenibile.duckdns.org:443
```

## 🐳 Configurazione Docker Compose

### File Principali

- `docker-compose.yml`: Configurazione base
- `docker-compose.override.yml`: Override per sviluppo
- `docker-compose.dev.yml`: Solo per sviluppo locale

### Servizi

#### Nginx Service
```yaml
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/conf.d/default.conf
    - ./ssl:/etc/letsencrypt
    - ./webroot:/var/www/html
  depends_on:
    - chatbot
  restart: unless-stopped
  networks:
    - chatbot-net
```

#### Chatbot Service
```yaml
chatbot:
  build:
    context: .
    dockerfile: Dockerfile.dev
  ports:
    - "8081:8081"
  volumes:
    - ./app:/app/app
    - ./.env:/app/.env
  environment:
    - DEBUG=true
    - DATABASE_URL=postgresql+asyncpg://chatbot:password@postgres:5432/chatbot
  restart: unless-stopped
  depends_on:
    - postgres
  networks:
    - chatbot-net
  healthcheck:
    test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8081/health')"]
    interval: 30s
    timeout: 10s
    retries: 3
```

#### PostgreSQL Service
```yaml
postgres:
  image: postgres:15-alpine
  environment:
    - POSTGRES_DB=chatbot
    - POSTGRES_USER=chatbot
    - POSTGRES_PASSWORD=password
  ports:
    - "6000:6000"  # Porta esterna 6000, interna 5432
  volumes:
    - postgres_data:/var/lib/postgresql/data
    - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init.sql
  restart: unless-stopped
  networks:
    - chatbot-net
```

### Reti e Volumi

```yaml
networks:
  chatbot-net:
    driver: bridge

volumes:
  postgres_data:
  ssl:
  webroot:
```

## 🚀 Procedure di Deploy e Manutenzione

### Avvio del Server

```bash
# Avvio completo (produzione)
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

# Verifica status
docker-compose ps

# Visualizza logs
docker-compose logs -f
```

### Setup SSL Iniziale

```bash
# Setup completo SSL
./scripts/ssl.sh setup

# Verifica configurazione
./scripts/ssl.sh check
```

### Monitoraggio

#### Health Checks
```bash
# Health check applicazione
curl https://corposostenibile.duckdns.org/health

# Status container
docker-compose ps

# Logs real-time
docker-compose logs -f chatbot
```

#### Metriche SSL
```bash
# Scadenza certificato
openssl s_client -servername corposostenibile.duckdns.org -connect corposostenibile.duckdns.org:443 2>/dev/null | openssl x509 -noout -dates

# Test SSL Labs
curl -s "https://www.ssllabs.com/ssltest/analyze.html?d=corposostenibile.duckdns.org" | grep -o '"grade":"[^"]*"' | head -1
```

### Aggiornamenti

#### Aggiornamento Applicazione
```bash
# Pull nuove immagini
docker-compose pull

# Ricostruisci chatbot
docker-compose build chatbot

# Riavvia
docker-compose up -d
```

#### Aggiornamento SSL
```bash
# Rinnovo manuale
./scripts/ssl.sh renew

# Forza rinnovo
./scripts/ssl.sh renew --force
```

## 🔧 Troubleshooting

### Problemi Comuni

#### 502 Bad Gateway
**Sintomi**: Nginx restituisce 502
**Cause possibili**:
- Applicazione non risponde su porta 8081
- Nome servizio errato in nginx.conf
- Container non nella stessa rete Docker

**Soluzioni**:
```bash
# Verifica che l'app risponda
docker-compose exec chatbot curl http://localhost:8081/health

# Verifica rete Docker
docker-compose ps

# Riavvia servizi
docker-compose restart
```

#### SSL Certificate Errors
**Sintomi**: HTTPS non funziona
**Cause possibili**:
- Certificato scaduto
- Path certificati errati
- Nginx non riavviato dopo rinnovo

**Soluzioni**:
```bash
# Verifica certificati
./scripts/ssl.sh check

# Rinnova certificati
./scripts/ssl.sh renew

# Riavvia Nginx
docker-compose restart nginx
```

#### Database Connection Issues
**Sintomi**: Applicazione non si connette al DB
**Cause possibili**:
- Container PostgreSQL non attivo
- Credenziali errate
- Rete Docker non configurata

**Soluzioni**:
```bash
# Verifica status DB
docker-compose ps postgres

# Test connessione
docker-compose exec chatbot python scripts/test_db_connection.py

# Logs database
docker-compose logs postgres
```

### Log Files Importanti

```bash
# Logs Nginx
docker-compose logs nginx

# Logs applicazione
docker-compose logs chatbot

# Logs database
docker-compose logs postgres

# Logs Certbot
sudo tail -f /var/log/letsencrypt/letsencrypt.log
```

### Comandi di Debug

```bash
# Test DNS
nslookup corposostenibile.duckdns.org

# Test connettività porte
telnet corposostenibile.duckdns.org 80
telnet corposostenibile.duckdns.org 443

# Test interno container
docker-compose exec nginx curl http://chatbot:8081/health
docker-compose exec chatbot curl http://postgres:5432
```

## 📊 Monitoraggio e Alerting

### Metriche da Monitorare

1. **Disponibilità Servizio**
   - Endpoint health: `https://corposostenibile.duckdns.org/health`
   - Status code 200 = OK

2. **SSL Certificate**
   - Scadenza > 30 giorni
   - Validità dominio

3. **Database**
   - Connessioni attive
   - Spazio disco
   - Performance query

4. **Risorse Sistema**
   - CPU/Memoria container
   - Spazio disco
   - Network I/O

### Setup Monitoring (Opzionale)

```bash
# Installa monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Prometheus + Grafana per metriche
# Alert Manager per notifiche
```

## 🔐 Sicurezza

### Best Practices Implementate

- ✅ HTTPS forzato su tutte le connessioni
- ✅ Certificati SSL validi e aggiornati
- ✅ Headers di sicurezza in Nginx
- ✅ Rete isolata Docker
- ✅ Credenziali database protette
- ✅ Accesso root limitato

### Configurazioni di Sicurezza Aggiuntive

```nginx
# Headers di sicurezza aggiuntivi
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

## 📞 Supporto e Manutenzione

### Contatti
- **Admin**: admin@corposostenibile.duckdns.org
- **Documentazione**: Questo file
- **Logs**: `/var/log/letsencrypt/`, Docker logs

### Checklist Manutenzione Mensile

- [ ] Verifica scadenza SSL (>30 giorni)
- [ ] Aggiornamenti sicurezza
- [ ] Test funzionalità complete
- [ ] Verifica logs per errori
- [ ] Controllo spazio disco

## 🚀 Script di Gestione Server

Per semplificare la gestione del server, è disponibile lo script completo `scripts/server.sh` che automatizza tutte le operazioni principali.

### Installazione Script

```bash
# Rendere eseguibile
chmod +x scripts/server.sh

# Creare link simbolico per accesso facile
ln -sf scripts/server.sh server

# Ora puoi usare ./server invece di ./scripts/server.sh
```

### Comandi Principali

#### Gestione Server
```bash
# Avvio completo
./server server-start

# Arresto
./server server-stop

# Riavvio
./server server-restart

# Status completo
./server server-status

# Logs specifici
./server server-logs nginx     # Logs Nginx
./server server-logs chatbot   # Logs applicazione
./server server-logs postgres  # Logs database
./server server-logs           # Tutti i logs
```

#### Gestione SSL
```bash
# Setup completo SSL
./server ssl-setup

# Rinnovo certificato
./server ssl-renew

# Verifica SSL
./server ssl-check
```

#### Monitoraggio
```bash
# Controlli health automatici
./server monitor-health

# Monitoraggio risorse
./server monitor-resources
```

#### Troubleshooting
```bash
# Diagnosi automatica problemi
./server troubleshoot
```

#### Manutenzione
```bash
# Aggiornamento completo sistema
./server maintenance-update

# Pulizia sistema
./server maintenance-cleanup
```

### Esempi di Uso Quotidiano

#### Avvio Mattutino
```bash
./server server-start
./server monitor-health
```

#### Controllo Serale
```bash
./server server-status
./server ssl-check
```

#### Manutenzione Settimanale
```bash
./server maintenance-update
./server maintenance-cleanup
```

### Integrazione con Cron

Aggiungi al crontab per automazione:

```bash
# Modifica crontab
crontab -e

# Aggiungi queste righe:
# Health check ogni ora
0 * * * * /home/manu/chatbot/server monitor-health >> /home/manu/chatbot/logs/health.log 2>&1
# Rinnovo SSL giornaliero (già configurato automaticamente)
```

### Log e Monitoraggio

Lo script genera log automatici in `logs/`:
- `health.log`: Risultati controlli health
- `ssl-renew.log`: Log rinnovi SSL
- `server.log`: Log operazioni generali

### Sicurezza

Lo script include controlli di sicurezza automatici:
- ✅ Verifica dipendenze prima di ogni operazione
- ✅ Validazione SSL e certificati
- ✅ Controlli integrità file di configurazione

### Troubleshooting con Script

Se riscontri problemi, usa la diagnosi automatica:

```bash
./server troubleshoot
```

Questo comando verifica automaticamente:
- Risoluzione DNS
- Porte firewall
- Connettività di rete
- Status container Docker
- Comunicazione tra servizi
- Connessione database</content>
<parameter name="filePath">/home/manu/chatbot/docs/Nginx_SSL_Documentation.md