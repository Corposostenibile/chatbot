#!/bin/bash

# Script per ottenere e rinnovare certificati SSL Let's Encrypt
set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Verifica se siamo root o abbiamo sudo
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        SUDO=""
    elif command -v sudo &> /dev/null; then
        SUDO="sudo"
    else
        print_error "Questo script richiede privilegi di root. Installa sudo o esegui come root."
        exit 1
    fi
}

# Installa Certbot se non presente
install_certbot() {
    print_header "Installazione Certbot"

    if command -v certbot &> /dev/null; then
        print_status "Certbot già installato"
        return
    fi

    print_status "Installando Certbot..."

    # Per Ubuntu/Debian
    if command -v apt &> /dev/null; then
        $SUDO apt update
        $SUDO apt install -y certbot
    # Per CentOS/RHEL
    elif command -v yum &> /dev/null; then
        $SUDO yum install -y certbot
    # Per Fedora
    elif command -v dnf &> /dev/null; then
        $SUDO dnf install -y certbot
    else
        print_error "Impossibile installare Certbot. Installalo manualmente."
        exit 1
    fi

    print_status "Certbot installato con successo"
}

# Ottieni il certificato SSL
get_certificate() {
    print_header "Ottieni Certificato SSL"

    local domain="corposostenibile.duckdns.org"
    local webroot="/home/manu/chatbot/webroot"

    print_status "Verificando raggiungibilità del dominio..."
    
    # Test DNS resolution con retry
    local max_attempts=3
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        print_status "Tentativo DNS $attempt/$max_attempts..."
        if nslookup "$domain" >/dev/null 2>&1; then
            print_status "✅ DNS risolto correttamente"
            break
        else
            if [ $attempt -eq $max_attempts ]; then
                print_error "❌ Il dominio $domain non è raggiungibile dopo $max_attempts tentativi"
                print_error "Verifica che il dominio DuckDNS sia configurato correttamente"
                exit 1
            fi
            print_warning "Tentativo $attempt fallito, riprovando in 5 secondi..."
            sleep 5
            ((attempt++))
        fi
    done
    
    print_status "Dominio raggiungibile, procedendo con SSL..."
    print_status "Otteniendo certificato SSL per $domain..."

    # Assicurati che Nginx sia attivo
    print_status "Assicurandosi che Nginx sia attivo..."
    docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d nginx

    # Aspetta che Nginx sia pronto
    sleep 5

    # Test HTTP connectivity
    if ! curl -f --max-time 10 "http://$domain:8081" >/dev/null 2>&1; then
        print_error "❌ Il dominio $domain non risponde su HTTP. Verifica:"
        print_error "   - Che il server sia avviato: ./scripts/server.sh docker-dev"
        print_error "   - Che le porte 80/443 siano aperte sul firewall/router"
        exit 1
    fi

    # Usa metodo webroot challenge (funziona con Nginx attivo)
    print_status "Usando webroot challenge (Nginx rimane attivo)..."
    
    $SUDO certbot certonly --webroot \
        --webroot-path "$webroot" \
        --agree-tos \
        --email "admin@corposostenibile.duckdns.org" \
        --domain "$domain" \
        --non-interactive

    if [ $? -eq 0 ]; then
        print_status "✅ Certificato SSL ottenuto con successo!"

        # Copia certificati nel volume Docker se necessario
        if [ -d "/etc/letsencrypt/live/$domain" ]; then
            print_status "Copiando certificati nel volume Docker..."
            $SUDO cp -r /etc/letsencrypt ./letsencrypt_backup 2>/dev/null || true
            $SUDO chown -R $(id -u):$(id -g) ./letsencrypt_backup 2>/dev/null || true
        fi

        # Riavvia Nginx per applicare i nuovi certificati
        print_status "Riavviando Nginx..."
        docker-compose -f docker-compose.yml -f docker-compose.override.yml restart nginx

        print_status "🎉 SSL configurato! Il sito è ora disponibile su https://$domain"
    else
        print_error "❌ Errore nell'ottenimento del certificato"
        print_error "Possibili cause:"
        print_error "- Il dominio non è raggiungibile pubblicamente"
        print_error "- Le porte 80/443 non sono aperte sul firewall"
        print_error "- Nginx non è configurato correttamente"
        print_error "- La directory webroot non è accessibile"
        exit 1
    fi
}

# Rinnova il certificato
renew_certificate() {
    print_header "Rinnovo Certificato SSL"

    local webroot="/home/manu/chatbot/webroot"

    print_status "Rinnovando certificato SSL..."

    # Assicurati che Nginx sia attivo per servire i file di challenge
    docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d nginx
    sleep 3

    # Rinnova usando webroot
    $SUDO certbot renew --webroot --webroot-path "$webroot"

    # Riavvia Nginx per applicare i nuovi certificati
    docker-compose -f docker-compose.yml -f docker-compose.override.yml restart nginx

    print_status "✅ Certificato rinnovato con successo!"
}

# Verifica configurazione SSL
check_ssl() {
    print_header "Verifica Configurazione SSL"

    local domain="corposostenibile.duckdns.org"

    print_status "Verificando configurazione SSL..."

    # Test HTTP (dovrebbe redirectare a HTTPS)
    if curl -I "http://$domain" 2>/dev/null | grep -q "301\|302"; then
        print_status "✅ HTTP redirecta correttamente a HTTPS"
    else
        print_warning "⚠️ HTTP non redirecta a HTTPS"
    fi

    # Test HTTPS
    if curl -I "https://$domain" 2>/dev/null | grep -q "200\|301\|302"; then
        print_status "✅ HTTPS funziona correttamente"
    else
        print_error "❌ HTTPS non funziona"
    fi

    # Verifica scadenza certificato
    if command -v openssl &> /dev/null; then
        echo | openssl s_client -servername "$domain" -connect "$domain:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || print_warning "Impossibile verificare scadenza certificato"
    fi
}

# Setup completo SSL
setup_ssl() {
    print_header "Setup Completo SSL"

    check_permissions
    install_certbot
    get_certificate
    check_ssl

    print_status ""
    print_status "🎉 Setup SSL completato!"
    print_status "Il tuo sito è ora disponibile su: https://corposostenibile.duckdns.org"
    print_status ""
    print_status "IMPORTANTE:"
    print_status "- I certificati Let's Encrypt scadono ogni 90 giorni"
    print_status "- Aggiungi questo comando a cron per rinnovo automatico:"
    print_status "  0 12 * * * /home/manu/chatbot/scripts/ssl.sh renew"
}

# Main
case "${1:-help}" in
    setup)
        setup_ssl
        ;;
    get)
        check_permissions
        install_certbot
        get_certificate
        ;;
    renew)
        renew_certificate
        ;;
    check)
        check_ssl
        ;;
    help|*)
        echo "Script per gestione certificati SSL Let's Encrypt"
        echo ""
        echo "Uso: $0 [COMANDO]"
        echo ""
        echo "Comandi disponibili:"
        echo "  setup    - Setup completo SSL (installa Certbot, ottiene certificato, configura)"
        echo "  get      - Ottiene nuovo certificato SSL"
        echo "  renew    - Rinnova certificato esistente"
        echo "  check    - Verifica configurazione SSL"
        echo "  help     - Mostra questo aiuto"
        echo ""
        echo "Esempi:"
        echo "  $0 setup    # Setup completo SSL"
        echo "  $0 renew    # Rinnovo manuale"
        echo "  $0 check    # Verifica configurazione"
        ;;
esac