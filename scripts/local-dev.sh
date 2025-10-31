#!/bin/bash

# Script per lo sviluppo locale
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

# Funzione per verificare se Poetry è installato
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry non è installato. Installalo con:"
        echo "curl -sSL https://install.python-poetry.org | python3 -"
        exit 1
    fi
}

# Funzione per setup dell'ambiente
setup_environment() {
    print_header "Setup Ambiente di Sviluppo"
    
    # Verifica Poetry
    check_poetry
    
    # Installa dipendenze
    print_status "Installando dipendenze con Poetry..."
    poetry install
    
    # Crea file .env se non esiste
    if [ ! -f .env ]; then
        print_status "Creando file .env da .env.example..."
        cp .env.example .env
        print_warning "Ricordati di configurare le variabili in .env!"
    fi
    
    print_status "Setup completato!"
}

# Funzione per avviare l'app in modalità sviluppo
run_dev() {
    print_header "Avvio Applicazione (Modalità Sviluppo)"
    
    check_poetry
    
    print_status "Avviando il server di sviluppo..."
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
}

# Funzione per eseguire i test
run_tests() {
    print_header "Esecuzione Test"
    
    check_poetry
    
    print_status "Eseguendo i test..."
    poetry run pytest tests/ -v --cov=app --cov-report=term-missing
}

# Funzione per formattare il codice
format_code() {
    print_header "Formattazione Codice"
    
    check_poetry
    
    print_status "Formattando il codice con Black..."
    poetry run black app/ tests/
    
    print_status "Ordinando gli import con isort..."
    poetry run isort app/ tests/
    
    print_status "Verificando con flake8..."
    poetry run flake8 app/ tests/
}

# Funzione per build Docker locale
build_docker() {
    print_header "Build Docker Locale"
    
    print_status "Building immagine Docker..."
    docker build -t chatbot:latest .
    
    print_status "Immagine Docker creata: chatbot:latest"
}

# Funzione per avviare con Docker Compose
run_docker() {
    print_header "Avvio con Docker Compose"
    
    print_status "Avviando con docker-compose..."
    docker-compose -f docker-compose.dev.yml up --build
}

# Funzione per mostrare l'aiuto
show_help() {
    echo "Script per lo sviluppo locale del Chatbot"
    echo ""
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandi disponibili:"
    echo "  setup     - Configura l'ambiente di sviluppo"
    echo "  dev       - Avvia l'applicazione in modalità sviluppo"
    echo "  test      - Esegue i test"
    echo "  format    - Formatta il codice"
    echo "  build     - Build dell'immagine Docker"
    echo "  docker    - Avvia con Docker Compose"
    echo "  help      - Mostra questo aiuto"
    echo ""
    echo "Esempi:"
    echo "  $0 setup    # Prima configurazione"
    echo "  $0 dev      # Sviluppo locale"
    echo "  $0 test     # Esegui test"
}

# Main
case "${1:-help}" in
    setup)
        setup_environment
        ;;
    dev)
        run_dev
        ;;
    test)
        run_tests
        ;;
    format)
        format_code
        ;;
    build)
        build_docker
        ;;
    docker)
        run_docker
        ;;
    help|*)
        show_help
        ;;
esac