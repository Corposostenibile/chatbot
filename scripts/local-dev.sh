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

# Funzione per ottenere la porta dalle impostazioni
get_port() {
    if [ -f .env ]; then
        PORT=$(grep '^PORT=' .env | cut -d '=' -f2 | tr -d '"')
        echo "${PORT:-8080}"  # Default a 8080 se non trovato
    else
        echo "8080"
    fi
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
    
    # Ottieni la porta dalle impostazioni
    PORT=$(get_port)
    print_status "Usando porta: $PORT"
    
    # Avvia il database con Docker se non è già attivo
    if ! docker-compose -f docker-compose.dev.yml ps postgres | grep -q "Up"; then
        print_status "Avviando database PostgreSQL con Docker..."
        docker-compose -f docker-compose.dev.yml up -d postgres
        sleep 3  # Aspetta che il DB sia pronto
    else
        print_status "Database PostgreSQL già attivo"
    fi
    
    print_status "Avviando il server di sviluppo..."
    poetry run uvicorn app.main:app --host 0.0.0.0 --port $PORT --reload
}

# Funzione per testare la connessione al database
test_db() {
    print_header "Test Connessione Database"
    
    check_poetry
    
    print_status "Testando connessione PostgreSQL..."
    poetry run python scripts/test_db_connection.py
    
    if [ $? -eq 0 ]; then
        print_status "✅ Connessione database OK"
    else
        print_error "❌ Problemi con il database"
    fi
}

# Funzione per testare il lifecycle completo
test_lifecycle() {
    print_header "Test Lifecycle Completo"
    
    check_poetry
    
    # Verifica che il database sia attivo
    if ! docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
        print_error "Il database non sembra essere attivo"
        print_status "Avvia il database con: ./scripts/local-dev.sh dev"
        exit 1
    fi
    
    print_status "Testando lifecycle completo del chatbot..."
    poetry run python scripts/test_lifecycle_flow.py
    
    if [ $? -eq 0 ]; then
        print_status "✅ Test lifecycle completato"
    else
        print_error "❌ Test lifecycle fallito"
    fi
}

# Funzione per fermare il database
stop_db() {
    print_header "Fermando Database"
    
    print_status "Fermando PostgreSQL..."
    docker-compose -f docker-compose.dev.yml down
    
    print_status "Database fermato"
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
    sudo docker build -t chatbot:latest .
    
    print_status "Immagine Docker creata: chatbot:latest"
}

# Funzione per avviare con Docker Compose
run_docker() {
    print_header "Avvio con Docker Compose"
    
    print_status "Avviando con docker-compose..."
    sudo docker-compose -f docker-compose.dev.yml up --build
}

# Funzione per mostrare l'aiuto
show_help() {
    echo "Script per lo sviluppo locale del Chatbot"
    echo ""
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandi disponibili:"
    echo "  setup     - Configura l'ambiente di sviluppo"
    echo "  dev       - Avvia l'applicazione in modalità sviluppo (con DB)"
    echo "  test      - Esegue i test"
    echo "  test-db   - Test connessione database"
    echo "  test-lifecycle - Test flusso completo lifecycle"
    echo "  format    - Formatta il codice"
    echo "  build     - Build dell'immagine Docker"
    echo "  docker    - Avvia con Docker Compose"
    echo "  db-stop   - Ferma il database PostgreSQL"
    echo "  help      - Mostra questo aiuto"
    echo ""
    echo "Esempi:"
    echo "  $0 setup    # Prima configurazione"
    echo "  $0 dev      # Sviluppo locale con DB"
    echo "  $0 test     # Esegui test"
    echo "  $0 test-db  # Test connessione DB"
    echo "  $0 test-lifecycle # Test flusso lifecycle"
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
    test-db)
        test_db
        ;;
    test-lifecycle)
        test_lifecycle
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
    db-stop)
        stop_db
        ;;
    help|*)
        show_help
        ;;
esac