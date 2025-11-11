#!/bin/bash

# 🚀 Script di Gestione Completo Server Chatbot
# Gestisce Nginx, SSL, Docker, Database, Backup e Monitoraggio
set -e

# Configurazione
DOMAIN="corposostenibile.duckdns.org"
PROJECT_DIR="/home/manu/chatbot"
BACKUP_DIR="$PROJECT_DIR/backups"
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

    local deps=("docker" "docker-compose" "curl" "openssl")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        print_error "Dipendenze mancanti: ${missing[*]}"
        print_info "Installa con: sudo apt update && sudo apt install -y ${missing[*]}"
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

    mkdir -p "$BACKUP_DIR" "$LOG_DIR" "$WEBROOT_DIR/.well-known/acme-challenge"

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
    docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

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
    docker-compose -f docker-compose.yml -f docker-compose.override.yml down

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
    docker-compose ps

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
    echo "Container attivi:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
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
    docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d nginx
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
        docker-compose -f docker-compose.yml -f docker-compose.override.yml restart nginx

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
    docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d nginx
    sleep 3

    print_subheader "Rinnovo Certificato"
    sudo certbot renew --webroot --webroot-path "$WEBROOT_DIR"

    if [ $? -eq 0 ]; then
        print_status "Certificato rinnovato"

        print_subheader "Riavvio Nginx"
        docker-compose -f docker-compose.yml -f docker-compose.override.yml restart nginx

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
# GESTIONE BACKUP
# ===============================

backup_create() {
    print_header "💾 CREAZIONE BACKUP"

    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/backup_$timestamp.tar.gz"

    print_subheader "Creazione Directory Backup"
    mkdir -p "$BACKUP_DIR"

    print_subheader "Backup Database"
    local db_backup="$BACKUP_DIR/db_$timestamp.sql"
    docker-compose exec -T postgres pg_dump -U chatbot chatbot > "$db_backup"

    if [ $? -eq 0 ]; then
        print_status "Database backup creato: $db_backup"
    else
        print_error "Errore nel backup del database"
        rm -f "$db_backup"
        exit 1
    fi

    print_subheader "Backup File Sistema"
    tar -czf "$backup_file" \
        --exclude='backups' \
        --exclude='logs' \
        --exclude='*.log' \
        --exclude='.git' \
        ssl/ \
        webroot/ \
        nginx.conf \
        docker-compose*.yml \
        .env \
        "$db_backup"

    if [ $? -eq 0 ]; then
        print_status "Backup completo creato: $backup_file"

        # Calcola dimensione
        local size=$(du -h "$backup_file" | cut -f1)
        print_info "Dimensione backup: $size"

        # Pulisci backup database temporaneo
        rm -f "$db_backup"

        # Mantieni solo gli ultimi 10 backup
        print_subheader "Pulizia Vecchi Backup"
        ls -t "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm -f
        print_status "Mantenuti ultimi 10 backup"
    else
        print_error "Errore nella creazione del backup"
        rm -f "$backup_file" "$db_backup"
        exit 1
    fi
}

backup_list() {
    print_header "📋 ELENCO BACKUP"

    if [ -d "$BACKUP_DIR" ]; then
        echo "Backup disponibili in $BACKUP_DIR:"
        ls -la "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null || echo "Nessun backup trovato"
    else
        print_warning "Directory backup non esistente"
    fi
}

backup_restore() {
    local backup_file="$1"

    if [ -z "$backup_file" ]; then
        print_error "Specifica il file di backup da ripristinare"
        echo "Uso: $0 backup-restore <file_backup.tar.gz>"
        backup_list
        exit 1
    fi

    if [ ! -f "$backup_file" ]; then
        print_error "File backup non trovato: $backup_file"
        exit 1
    fi

    print_header "🔄 RIPRISTINO BACKUP"
    print_warning "ATTENZIONE: Questa operazione sovrascriverà i dati esistenti!"

    read -p "Sei sicuro di voler ripristinare il backup? (y/N): " -r
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Ripristino annullato"
        exit 0
    fi

    print_subheader "Arresto Servizi"
    server_stop

    print_subheader "Estrazione Backup"
    local temp_dir=$(mktemp -d)
    tar -xzf "$backup_file" -C "$temp_dir"

    print_subheader "Ripristino File Sistema"
    cp -r "$temp_dir/ssl" ./
    cp -r "$temp_dir/webroot" ./
    cp "$temp_dir/nginx.conf" ./
    cp "$temp_dir/docker-compose.yml" ./
    cp "$temp_dir/docker-compose.override.yml" ./
    cp "$temp_dir/.env" ./

    print_subheader "Ripristino Database"
    local db_backup=$(find "$temp_dir" -name "db_*.sql" | head -1)
    if [ -n "$db_backup" ] && [ -f "$db_backup" ]; then
        docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d postgres
        sleep 5
        docker-compose exec -T postgres psql -U chatbot chatbot < "$db_backup"
        print_status "Database ripristinato"
    else
        print_warning "Backup database non trovato nel file"
    fi

    print_subheader "Pulizia"
    rm -rf "$temp_dir"

    print_subheader "Riavvio Servizi"
    server_start

    print_status "Ripristino completato"
}

# ===============================
# MONITORAGGIO
# ===============================

monitor_health() {
    print_header "🏥 MONITORAGGIO HEALTH"

    local issues=0

    print_subheader "Controlli Automatici"

    # Controllo container
    if ! docker-compose ps | grep -q "Up"; then
        print_error "Alcuni container non sono attivi"
        ((issues++))
    else
        print_status "Tutti i container sono attivi"
    fi

    # Controllo applicazione
    if ! curl -f -s "https://$DOMAIN/health" > /dev/null 2>&1; then
        print_error "Applicazione non risponde"
        ((issues++))
    else
        print_status "Applicazione risponde correttamente"
    fi

    # Controllo database
    if ! docker-compose exec -T postgres pg_isready -U chatbot >/dev/null 2>&1; then
        print_error "Database non accessibile"
        ((issues++))
    else
        print_status "Database accessibile"
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
# MANUTENZIONE
# ===============================

maintenance_update() {
    print_header "🔄 AGGIORNAMENTO SISTEMA"

    print_subheader "Backup Pre-Aggiornamento"
    backup_create

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
        print_info "Rollback possibile con: $0 backup-restore <backup_file>"
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

    print_subheader "Pulizia Backup Vecchi (mantieni ultimi 5)"
    ls -t "$BACKUP_DIR"/backup_*.tar.gz 2>/dev/null | tail -n +6 | xargs -r rm -f

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
    echo "💾 BACKUP:"
    echo "  backup-create          Crea backup completo"
    echo "  backup-list            Elenca backup disponibili"
    echo "  backup-restore <file>  Ripristina da backup"
    echo ""
    echo "📊 MONITORAGGIO:"
    echo "  monitor-health         Controlli health automatici"
    echo "  monitor-resources      Monitoraggio risorse"
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
    echo "  $0 backup-create      # Crea backup"
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

    # Backup
    backup-create) backup_create ;;
    backup-list) backup_list ;;
    backup-restore) backup_restore "$2" ;;

    # Monitoraggio
    monitor-health) monitor_health ;;
    monitor-resources) monitor_resources ;;

    # Troubleshooting
    troubleshoot) troubleshoot ;;

    # Manutenzione
    maintenance-update) maintenance_update ;;
    maintenance-cleanup) maintenance_cleanup ;;

    # Help
    help|*) show_help ;;
esac