#!/bin/bash

# 🚀 Script di Gestione Completo Server Chatbot
# Gestisce Nginx, SSL, Docker, Dipendenze e Monitoraggio
set -e

# Configurazione
DOMAIN="corposostenibile.duckdns.org"
PROJECT_DIR="/home/manu/chatbot"
LOG_DIR="$PROJECT_DIR/logs"
WEBROOT_DIR="$PROJECT_DIR/webroot"
SSL_DIR="$PROJECT_DIR/ssl"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Funzioni di utilità
print_header() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ $1${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
}

print_subheader() {
    echo -e "${CYAN}┌─ $1${NC}"
}

print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Verifica dipendenze
check_dependencies() {
    print_subheader "Verifica Dipendenze"

    local deps=("docker" "docker-compose" "curl" "openssl" "poetry")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        print_error "Dipendenze mancanti: ${missing[*]}"
        print_info "Installa con: sudo apt update && sudo apt install -y ${missing[*]}"
        print_info "Per Poetry: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi

    print_status "Tutte le dipendenze sono installate"
}

# Verifica che siamo nella directory del progetto
check_project_dir() {
    if [ ! -f "docker-compose.yml" ] || [ ! -f "nginx.conf" ]; then
        print_error "Esegui questo script dalla directory del progetto chatbot"
        exit 1
    fi
}

# Crea directory necessarie
create_directories() {
    print_subheader "Creazione Directory Necessarie"

    mkdir -p "$LOG_DIR" "$WEBROOT_DIR/.well-known/acme-challenge"

    # Imposta permessi
    chmod 755 "$WEBROOT_DIR"
    chmod 755 "$WEBROOT_DIR/.well-known"
    chmod 755 "$WEBROOT_DIR/.well-known/acme-challenge"

    print_status "Directory create e configurate"
}

# ===============================
# GESTIONE SERVER
# ===============================

server_start() {
    print_header "🚀 AVVIO SERVER COMPLETO"

    check_dependencies
    check_project_dir
    create_directories

    print_subheader "Avvio Servizi Docker"
    docker-compose up -d

    print_subheader "Attesa Avvio Servizi"
    sleep 5

    print_subheader "Verifica Status Servizi"
    if docker-compose ps | grep -q "Up"; then
        print_status "Tutti i servizi sono attivi"

        # Test endpoint health
        if curl -f -s "https://$DOMAIN/health" > /dev/null 2>&1; then
            print_status "Endpoint health risponde correttamente"
        else
            print_warning "Endpoint health non raggiungibile - verifica configurazione"
        fi
    else
        print_error "Alcuni servizi non sono attivi"
        docker-compose ps
        exit 1
    fi

    print_info "Server avviato su: https://$DOMAIN"
    print_info "Documentazione: https://$DOMAIN/docs"
}

server_stop() {
    print_header "🛑 ARRESTO SERVER"

    print_subheader "Arresto Servizi Docker"
    docker-compose down

    print_status "Server arrestato"
}

server_restart() {
    print_header "🔄 RIAVVIO SERVER"

    server_stop
    sleep 2
    server_start
}

server_status() {
    print_header "📊 STATUS SERVER"

    print_subheader "Status Container Docker"
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        docker-compose ps
    else
        print_info "ℹ Docker non disponibile nel container"
        print_info "ℹ Controlla lo status dall'host con: docker-compose ps"
    fi

    echo

    print_subheader "Status Applicazione"
    if curl -f -s "https://$DOMAIN/health" > /dev/null 2>&1; then
        echo -e "${GREEN}● Applicazione: ONLINE${NC}"
    else
        echo -e "${RED}● Applicazione: OFFLINE${NC}"
    fi

    echo

    print_subheader "Status SSL"
    if [ -f "$SSL_DIR/live/$DOMAIN/fullchain.pem" ]; then
        local expiry=$(openssl x509 -in "$SSL_DIR/live/$DOMAIN/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
        if [ -n "$expiry" ]; then
            echo -e "${GREEN}● Certificato: VALIDO fino al $expiry${NC}"
        else
            echo -e "${YELLOW}● Certificato: STATO SCONOSCIUTO${NC}"
        fi
    else
        echo -e "${RED}● Certificato: NON TROVATO${NC}"
    fi

    echo

    print_subheader "Utilizzo Risorse"
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        echo "Container attivi:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    else
        print_info "ℹ Monitoraggio risorse non disponibile nel container"
        print_info "ℹ Usa 'docker stats' dall'host per monitorare le risorse"
    fi
}

server_logs() {
    local service="${1:-all}"
    local lines="${2:-50}"

    print_header "📋 LOGS SERVER"

    case "$service" in
        nginx)
            docker-compose logs --tail="$lines" -f nginx
            ;;
        chatbot)
            docker-compose logs --tail="$lines" -f chatbot
            ;;
        postgres)
            docker-compose logs --tail="$lines" -f postgres
            ;;
        all|*)
            docker-compose logs --tail="$lines" -f
            ;;
    esac
}

# ===============================
# GESTIONE SSL
# ===============================

ssl_setup() {
    print_header "🔒 SETUP SSL COMPLETO"

    check_dependencies

    print_subheader "Installazione Certbot"
    if ! command -v certbot &> /dev/null; then
        sudo apt update && sudo apt install -y certbot
        print_status "Certbot installato"
    else
        print_status "Certbot già installato"
    fi

    print_subheader "Verifica DNS"
    if ! nslookup "$DOMAIN" >/dev/null 2>&1; then
        print_error "Dominio $DOMAIN non risolto. Verifica configurazione DuckDNS"
        exit 1
    fi
    print_status "DNS risolto correttamente"

    print_subheader "Avvio Nginx per Challenge"
    docker-compose up -d nginx
    sleep 3

    print_subheader "Ottieni Certificato SSL"
    sudo certbot certonly --webroot \
        --webroot-path "$WEBROOT_DIR" \
        --agree-tos \
        --email "admin@$DOMAIN" \
        --domain "$DOMAIN" \
        --non-interactive

    if [ $? -eq 0 ]; then
        print_status "Certificato ottenuto con successo"

        print_subheader "Riavvio Nginx"
        docker-compose restart nginx

        print_subheader "Configurazione Cron per Rinnovo"
        setup_ssl_cron

        print_subheader "Verifica Configurazione"
        ssl_check

        print_status "SSL configurato con successo!"
        print_info "Sito disponibile su: https://$DOMAIN"
    else
        print_error "Errore nell'ottenimento del certificato"
        exit 1
    fi
}

ssl_renew() {
    print_header "🔄 RINNOVO CERTIFICATO SSL"

    print_subheader "Avvio Nginx"
    docker-compose up -d nginx
    sleep 3

    print_subheader "Rinnovo Certificato"
    sudo certbot renew --webroot --webroot-path "$WEBROOT_DIR"

    if [ $? -eq 0 ]; then
        print_status "Certificato rinnovato"

        print_subheader "Riavvio Nginx"
        docker-compose restart nginx

        print_status "Rinnovo completato"
    else
        print_error "Errore nel rinnovo"
        exit 1
    fi
}

ssl_check() {
    print_header "🔍 VERIFICA SSL"

    print_subheader "Test HTTP → HTTPS Redirect"
    local http_response=$(curl -I -s "http://$DOMAIN" | head -1)
    if echo "$http_response" | grep -q "301\|302"; then
        print_status "HTTP redirecta correttamente a HTTPS"
    else
        print_warning "HTTP non redirecta a HTTPS"
    fi

    print_subheader "Test HTTPS"
    local https_response=$(curl -I -s "https://$DOMAIN" | head -1)
    if echo "$https_response" | grep -q "200\|301\|302"; then
        print_status "HTTPS funziona correttamente"
    else
        print_error "HTTPS non funziona"
    fi

    print_subheader "Verifica Certificato"
    if [ -f "$SSL_DIR/live/$DOMAIN/fullchain.pem" ]; then
        local expiry=$(openssl x509 -in "$SSL_DIR/live/$DOMAIN/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
        if [ -n "$expiry" ]; then
            print_info "Certificato valido fino al: $expiry"

            # Calcola giorni rimanenti
            local expiry_epoch=$(date -d "$expiry" +%s)
            local now_epoch=$(date +%s)
            local days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

            if [ $days_left -gt 30 ]; then
                print_status "Certificato valido ($days_left giorni rimanenti)"
            elif [ $days_left -gt 7 ]; then
                print_warning "Certificato scade tra $days_left giorni"
            else
                print_error "Certificato scade tra $days_left giorni - rinnova urgentemente!"
            fi
        else
            print_error "Impossibile leggere data scadenza"
        fi
    else
        print_error "Certificato non trovato"
    fi

    print_subheader "Test SSL Labs Rating"
    print_info "Visita: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
}

setup_ssl_cron() {
    print_subheader "Configurazione Cron per Rinnovo SSL"

    local cron_job="0 12 * * * $PROJECT_DIR/scripts/server.sh ssl-renew >> $LOG_DIR/ssl-renew.log 2>&1"

    if ! crontab -l 2>/dev/null | grep -q "ssl-renew"; then
        (crontab -l 2>/dev/null; echo "$cron_job") | crontab -
        print_status "Cron job aggiunto per rinnovo automatico"
    else
        print_status "Cron job già esistente"
    fi

    print_info "Rinnovo automatico alle 12:00 ogni giorno"
}

# ===============================
# GESTIONE DIPENDENZE
# ===============================

dependencies_update() {
    print_header "📦 AGGIORNAMENTO DIPENDENZE POETRY"

    print_subheader "Verifica Poetry"
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry non è installato"
        print_info "Installa con: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi

    print_subheader "Verifica Ambiente Virtuale"
    if ! poetry env info >/dev/null 2>&1; then
        print_error "Ambiente virtuale Poetry non trovato"
        print_info "Inizializza con: poetry install"
        exit 1
    fi

    print_subheader "Aggiornamento Dipendenze"
    poetry update

    if [ $? -eq 0 ]; then
        print_status "Dipendenze aggiornate con successo"

        print_subheader "Verifica Ambiente"
        if poetry check; then
            print_status "Ambiente Poetry OK"
        else
            print_warning "Possibili problemi con l'ambiente Poetry"
        fi

        print_info "Riavvia l'applicazione per applicare le modifiche"
        print_info "Usa: ./server server-restart"
    else
        print_error "Errore nell'aggiornamento delle dipendenze"
        exit 1
    fi
}

dependencies_install() {
    print_header "📦 INSTALLAZIONE DIPENDENZE POETRY"

    print_subheader "Verifica Poetry"
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry non è installato"
        print_info "Installa con: curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi

    print_subheader "Installazione Dipendenze"
    poetry install

    if [ $? -eq 0 ]; then
        print_status "Dipendenze installate con successo"

        print_subheader "Verifica Ambiente"
        if poetry check; then
            print_status "Ambiente Poetry OK"
        else
            print_warning "Possibili problemi con l'ambiente Poetry"
        fi
    else
        print_error "Errore nell'installazione delle dipendenze"
        exit 1
    fi
}

dependencies_check() {
    print_header "🔍 VERIFICA DIPENDENZE POETRY"

    print_subheader "Verifica Poetry"
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry non è installato"
        exit 1
    fi

    print_subheader "Stato Ambiente Virtuale"
    if poetry env info >/dev/null 2>&1; then
        print_status "Ambiente virtuale attivo"
        poetry env info | head -5
    else
        print_error "Ambiente virtuale non trovato"
        print_info "Installa dipendenze con: ./server dependencies-install"
        exit 1
    fi

    echo

    print_subheader "Verifica Dipendenze"
    if poetry check; then
        print_status "Tutte le dipendenze sono OK"
    else
        print_error "Problemi con le dipendenze Poetry"
    fi

    echo

    print_subheader "Dipendenze Installate"
    poetry show --only=main | head -10
    echo "..."
    print_info "Mostrate solo le prime 10 dipendenze. Usa 'poetry show' per vedere tutte."
}

dependencies_lock() {
    print_header "🔒 AGGIORNAMENTO POETRY.LOCK"

    print_subheader "Verifica Poetry"
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry non è installato"
        exit 1
    fi

    print_subheader "Aggiornamento Lock File"
    poetry lock

    if [ $? -eq 0 ]; then
        print_status "File poetry.lock aggiornato con successo"
    else
        print_error "Errore nell'aggiornamento del lock file"
        exit 1
    fi
}

# ===============================
# MONITORAGGIO
# ===============================

monitor_health() {
    print_header "🏥 MONITORAGGIO HEALTH"

    local issues=0

    print_subheader "Controlli Automatici"

    # Controllo container
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        if ! docker-compose ps | grep -q "Up"; then
            print_error "Alcuni container non sono attivi"
            ((issues++))
        else
            print_status "Tutti i container sono attivi"
        fi
    else
        print_info "ℹ Controllo container non disponibile (Docker non accessibile dal container)"
    fi

    # Controllo applicazione
    if ! curl -f -s "https://$DOMAIN/health" > /dev/null 2>&1; then
        print_error "Applicazione non risponde"
        ((issues++))
    else
        print_status "Applicazione risponde correttamente"
    fi

    # Controllo database
    if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
        if ! docker-compose exec -T postgres pg_isready -U chatbot >/dev/null 2>&1; then
            print_error "Database non accessibile"
            ((issues++))
        else
            print_status "Database accessibile"
        fi
    else
        print_info "ℹ Controllo database non disponibile (Docker non accessibile dal container)"
    fi

    # Controllo SSL
    if [ -f "$SSL_DIR/live/$DOMAIN/fullchain.pem" ]; then
        local expiry=$(openssl x509 -in "$SSL_DIR/live/$DOMAIN/fullchain.pem" -noout -enddate 2>/dev/null | cut -d= -f2)
        if [ -n "$expiry" ]; then
            local expiry_epoch=$(date -d "$expiry" +%s)
            local now_epoch=$(date +%s)
            local days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

            if [ $days_left -le 7 ]; then
                print_error "Certificato SSL scade tra $days_left giorni"
                ((issues++))
            elif [ $days_left -le 30 ]; then
                print_warning "Certificato SSL scade tra $days_left giorni"
            else
                print_status "Certificato SSL valido ($days_left giorni rimanenti)"
            fi
        fi
    else
        print_error "Certificato SSL non trovato"
        ((issues++))
    fi

    # Controllo spazio disco
    local disk_usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ $disk_usage -gt 90 ]; then
        print_error "Spazio disco critico: $disk_usage% utilizzato"
        ((issues++))
    elif [ $disk_usage -gt 75 ]; then
        print_warning "Spazio disco elevato: $disk_usage% utilizzato"
    else
        print_status "Spazio disco OK: $disk_usage% utilizzato"
    fi

    echo

    if [ $issues -eq 0 ]; then
        print_status "TUTTI I CONTROLLI SUPERATI ✓"
        return 0
    else
        print_error "TROVATI $issues PROBLEMI"
        return 1
    fi
}

monitor_resources() {
    print_header "📊 MONITORAGGIO RISORSE"

    print_subheader "Utilizzo Container"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

    echo

    print_subheader "Utilizzo Disco"
    df -h / | tail -1

    echo

    print_subheader "Utilizzo Database"
    docker-compose exec postgres psql -U chatbot -c "SELECT * FROM pg_stat_database WHERE datname = 'chatbot';" 2>/dev/null | head -5
}

# ===============================
# TROUBLESHOOTING
# ===============================

troubleshoot() {
    print_header "🔧 TROUBLESHOOTING AUTOMATICO"

    local issues_found=0

    print_subheader "Diagnosi Problemi Comuni"

    # 1. Controlla DNS
    print_info "1. Verifica DNS..."
    if nslookup "$DOMAIN" >/dev/null 2>&1; then
        print_status "DNS risolto correttamente"
    else
        print_error "DNS non risolto - verifica configurazione DuckDNS"
        ((issues_found++))
    fi

    # 2. Controlla porte firewall
    print_info "2. Verifica porte firewall..."
    if sudo ufw status | grep -q "80\|443"; then
        print_status "Porte 80/443 aperte nel firewall"
    else
        print_warning "Porte 80/443 potrebbero essere bloccate"
        print_info "Apri con: sudo ufw allow 80,443/tcp"
    fi

    # 3. Test connettività
    print_info "3. Test connettività porte..."
    if timeout 5 bash -c "</dev/tcp/$DOMAIN/80" 2>/dev/null; then
        print_status "Porta 80 raggiungibile"
    else
        print_error "Porta 80 non raggiungibile"
        ((issues_found++))
    fi

    if timeout 5 bash -c "</dev/tcp/$DOMAIN/443" 2>/dev/null; then
        print_status "Porta 443 raggiungibile"
    else
        print_error "Porta 443 non raggiungibile"
        ((issues_found++))
    fi

    # 4. Controlla container
    print_info "4. Verifica container Docker..."
    if docker-compose ps | grep -q "Up"; then
        print_status "Container attivi"
    else
        print_error "Container non attivi"
        print_info "Avvia con: $0 server-start"
        ((issues_found++))
    fi

    # 5. Test interno
    print_info "5. Test comunicazione interna..."
    if docker-compose exec nginx curl -f -s http://chatbot:8081/health >/dev/null 2>&1; then
        print_status "Comunicazione Nginx ↔ Chatbot OK"
    else
        print_error "Comunicazione Nginx ↔ Chatbot FALLITA"
        print_info "Possibile problema: nome servizio in nginx.conf o container non in stessa rete"
        ((issues_found++))
    fi

    # 6. Test database
    print_info "6. Test connessione database..."
    if docker-compose exec chatbot python -c "import asyncpg; print('DB import OK')" >/dev/null 2>&1; then
        print_status "Connessione database OK"
    else
        print_error "Connessione database FALLITA"
        print_info "Verifica credenziali in .env e status container PostgreSQL"
        ((issues_found++))
    fi

    echo

    if [ $issues_found -eq 0 ]; then
        print_status "NESSUN PROBLEMA RILEVATO ✓"
        print_info "Se hai ancora problemi, controlla i log con: $0 server-logs"
    else
        print_error "TROVATI $issues_found PROBLEMI"
        print_info "Risolvi i problemi segnalati e riprova"
    fi
}

# ===============================
# GESTIONE DATABASE
# ===============================

db_migrate() {
    print_header "🗄️ MIGRAZIONI DATABASE"

    print_subheader "Verifica Container Database"
    if ! docker-compose ps postgres | grep -q "Up"; then
        print_error "Container PostgreSQL non attivo"
        print_info "Avvia il database con: $0 server-start"
        exit 1
    fi

    print_subheader "Esecuzione Migrazioni Alembic"
    if docker-compose exec chatbot alembic -c /home/manu/chatbot/alembic.ini upgrade head; then
        print_status "Migrazioni eseguite con successo"
    else
        print_error "Errore nell'esecuzione delle migrazioni"
        print_info "Controlla i log del container chatbot"
        exit 1
    fi
}

db_create() {
    local message="${1:-Auto-generated migration}"

    print_header "🆕 CREAZIONE MIGRAZIONE DATABASE"

    print_subheader "Generazione Migrazione Alembic"
    if docker-compose exec chatbot alembic -c /home/manu/chatbot/alembic.ini revision --autogenerate -m "$message"; then
        print_status "Migrazione creata con successo"
        print_info "Ricorda di eseguire: $0 db-migrate"
    else
        print_error "Errore nella creazione della migrazione"
        exit 1
    fi
}

db_status() {
    print_header "📊 STATUS DATABASE"

    print_subheader "Stato Migrazioni Alembic"
    if docker-compose exec chatbot alembic current; then
        print_status "Stato migrazioni recuperato"
    else
        print_error "Errore nel recupero dello stato migrazioni"
    fi

    echo

    print_subheader "Stato Database"
    if docker-compose exec postgres pg_isready -U chatbot >/dev/null 2>&1; then
        print_status "Database accessibile"

        # Mostra tabelle esistenti
        echo "Tabelle presenti:"
        docker-compose exec postgres psql -U chatbot -c "\dt" 2>/dev/null || print_warning "Impossibile recuperare lista tabelle"
    else
        print_error "Database non accessibile"
    fi
}

db_reset() {
    print_header "🔄 RESET DATABASE"

    print_warning "ATTENZIONE: Questa operazione cancellerà tutti i dati!"
    read -p "Sei sicuro di voler resettare il database? (scrivi 'RESET' per confermare): " confirm

    if [ "$confirm" != "RESET" ]; then
        print_info "Operazione annullata"
        exit 0
    fi

    print_subheader "Arresto Servizi"
    docker-compose stop chatbot

    print_subheader "Reset Database"
    docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS chatbot;" 2>/dev/null || true
    docker-compose exec postgres psql -U postgres -c "CREATE DATABASE chatbot;" 2>/dev/null || true

    print_subheader "Riavvio Servizi"
    docker-compose start chatbot

    print_subheader "Esecuzione Migrazioni"
    db_migrate

    print_status "Database resettato con successo"
}

maintenance_update() {
    print_header "🔄 AGGIORNAMENTO SISTEMA"

    print_subheader "Aggiornamento Immagini Docker"
    docker-compose pull

    print_subheader "Ricostruzione Container"
    docker-compose build --no-cache chatbot

    print_subheader "Riavvio Servizi"
    server_restart

    print_subheader "Verifica Post-Aggiornamento"
    if monitor_health; then
        print_status "Aggiornamento completato con successo"
    else
        print_error "Problemi dopo l'aggiornamento - controlla i log"
    fi
}

maintenance_cleanup() {
    print_header "🧹 PULIZIA SISTEMA"

    print_subheader "Pulizia Immagini Docker Non Utilizzate"
    docker image prune -f

    print_subheader "Pulizia Container Arrestati"
    docker container prune -f

    print_subheader "Pulizia Volumi Non Utilizzati"
    docker volume prune -f

    print_subheader "Pulizia Rete Docker"
    docker network prune -f

    print_subheader "Pulizia Log Vecchi"
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true

    print_status "Pulizia completata"
}

# ===============================
# MENU PRINCIPALE
# ===============================

show_help() {
    echo "🚀 Script di Gestione Completo Server Chatbot"
    echo ""
    echo "Uso: $0 [CATEGORIA-COMANDO] [PARAMETRI]"
    echo ""
    echo "CATEGORIE E COMANDI:"
    echo ""
    echo "🖥️  SERVER:"
    echo "  server-start           Avvia tutti i servizi"
    echo "  server-stop            Arresta tutti i servizi"
    echo "  server-restart         Riavvia tutti i servizi"
    echo "  server-status          Mostra status completo"
    echo "  server-logs [servizio] Mostra logs (nginx|chatbot|postgres|all)"
    echo ""
    echo "🔒 SSL:"
    echo "  ssl-setup              Setup completo SSL Let's Encrypt"
    echo "  ssl-renew              Rinnova certificato SSL"
    echo "  ssl-check              Verifica configurazione SSL"
    echo ""
    echo "📦 DIPENDENZE:"
    echo "  dependencies-install   Installa dipendenze Poetry"
    echo "  dependencies-update    Aggiorna dipendenze Poetry"
    echo "  dependencies-check     Verifica stato dipendenze"
    echo "  dependencies-lock      Aggiorna poetry.lock"
    echo ""
    echo "📊 MONITORAGGIO:"
    echo "  monitor-health         Controlli health automatici"
    echo "  monitor-resources      Monitoraggio risorse"
    echo ""
    echo "🗄️  DATABASE:"
    echo "  db-migrate             Esegue migrazioni Alembic"
    echo "  db-create [messaggio]  Crea nuova migrazione"
    echo "  db-status              Mostra status database"
    echo "  db-reset               Reset completo database"
    echo ""
    echo "🔧 TROUBLESHOOTING:"
    echo "  troubleshoot           Diagnosi automatica problemi"
    echo ""
    echo "⚙️  MANUTENZIONE:"
    echo "  maintenance-update     Aggiornamento completo sistema"
    echo "  maintenance-cleanup    Pulizia sistema"
    echo ""
    echo "📖 AIUTO:"
    echo "  help                   Mostra questo aiuto"
    echo ""
    echo "ESEMPI:"
    echo "  $0 server-start        # Avvia il server"
    echo "  $0 ssl-setup          # Setup SSL"
    echo "  $0 dependencies-update # Aggiorna dipendenze"
    echo "  $0 db-migrate         # Esegue migrazioni"
    echo "  $0 db-create 'Add new table' # Crea migrazione"
    echo "  $0 monitor-health     # Controlla health"
    echo "  $0 server-logs nginx  # Logs Nginx"
    echo ""
    echo "📋 DOCUMENTAZIONE: docs/Nginx_SSL_Documentation.md"
}

# Parsing argomenti
case "${1:-help}" in
    # Server
    server-start) server_start ;;
    server-stop) server_stop ;;
    server-restart) server_restart ;;
    server-status) server_status ;;
    server-logs) server_logs "$2" "$3" ;;

    # SSL
    ssl-setup) ssl_setup ;;
    ssl-renew) ssl_renew ;;
    ssl-check) ssl_check ;;

    # Dipendenze
    dependencies-install) dependencies_install ;;
    dependencies-update) dependencies_update ;;
    dependencies-check) dependencies_check ;;
    dependencies-lock) dependencies_lock ;;

    # Monitoraggio
    monitor-health) monitor_health ;;
    monitor-resources) monitor_resources ;;

    # Database
    db-migrate) db_migrate ;;
    db-create) db_create "$2" ;;
    db-status) db_status ;;
    db-reset) db_reset ;;

    # Troubleshooting
    troubleshoot) troubleshoot ;;

    # Manutenzione
    maintenance-update) maintenance_update ;;
    maintenance-cleanup) maintenance_cleanup ;;

    # Help
    help|*) show_help ;;
esac