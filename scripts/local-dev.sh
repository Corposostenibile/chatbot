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

# Funzione per configurazione totale dell'ambiente
configurazione_totale() {
    print_header "Configurazione Totale Ambiente di Sviluppo"
    
    # Verifica se Python è installato
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 non è installato. Installalo prima di continuare."
        exit 1
    fi
    
    print_status "Python trovato: $(python3 --version)"
    
    # Verifica e installa Poetry se necessario
    if ! command -v poetry &> /dev/null; then
        print_warning "Poetry non trovato. Installando Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
        if ! command -v poetry &> /dev/null; then
            print_error "Installazione Poetry fallita. Installalo manualmente."
            exit 1
        fi
        print_status "Poetry installato con successo."
    else
        print_status "Poetry già installato."
    fi
    
    # Rimuovi eventuali venv esistenti per forzare la creazione nel progetto
    print_status "Rimuovendo eventuali ambienti virtuali esistenti..."
    poetry env remove --all 2>/dev/null || true
    
    # Configura Poetry per creare venv nel progetto
    print_status "Configurando Poetry per ambiente virtuale nel progetto..."
    poetry config virtualenvs.in-project true
    
    # Installa dipendenze Python
    print_status "Installando dipendenze Python con Poetry..."
    poetry install
    
    # Verifica se Docker è installato
    if ! command -v docker &> /dev/null; then
        print_warning "Docker non trovato. Assicurati che sia installato per il database."
    else
        print_status "Docker trovato."
    fi
    
    # Verifica se Docker Compose è installato
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_warning "Docker Compose non trovato. Assicurati che sia installato per il database."
    else
        print_status "Docker Compose trovato."
    fi
    
    # Crea file .env se non esiste
    if [ ! -f .env ]; then
        print_status "Creando file .env da .env.example..."
        cp .env.example .env
        print_warning "⚠️  IMPORTANTE: Configura le variabili d'ambiente in .env prima di continuare!"
        print_warning "   In particolare: GOOGLE_AI_API_KEY, DATABASE_URL, ecc."
    else
        print_status "File .env già esistente."
    fi
    
    # Verifica configurazione essenziale
    if [ -f .env ]; then
        if ! grep -q "GOOGLE_AI_API_KEY" .env; then
            print_warning "GOOGLE_AI_API_KEY non trovata in .env. Aggiungila!"
        fi
    fi
    
    # Test connessione database (se possibile)
    print_status "Tentando test connessione database..."
    if poetry run python scripts/test_db_connection.py 2>/dev/null; then
        print_status "✅ Connessione database OK"
    else
        print_warning "❌ Database non raggiungibile. Avvia con './scripts/local-dev.sh dev'"
    fi
    
    print_status "🎉 Configurazione totale completata!"
    print_status "Ora puoi avviare l'applicazione con: ./scripts/local-dev.sh dev"
}

# Funzione per uccidere il server esistente se attivo
kill_existing_server() {
    local port=$1
    print_status "Controllando se il server è già attivo sulla porta $port..."
    
    # Trova i PID che usano la porta
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        print_warning "Server attivo trovato sulla porta $port (PID: $pids). Uccidendo..."
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 2  # Aspetta che il processo termini
        print_status "Server precedente ucciso."
    else
        print_status "Nessun server attivo sulla porta $port."
    fi
}

# Funzione per liberare la porta del database
kill_existing_db() {
    local port=5432
    print_status "Controllando se la porta del database $port è occupata..."
    
    # Ferma eventuali container Docker che usano la porta
    local containers=$(docker ps --filter "publish=$port" --format "{{.Names}}" 2>/dev/null || true)
    if [ -n "$containers" ]; then
        print_warning "Container Docker trovati che usano la porta $port: $containers. Fermandoli..."
        echo "$containers" | xargs docker stop 2>/dev/null || true
        echo "$containers" | xargs docker rm 2>/dev/null || true
        sleep 2
    fi
    
    # Trova i PID che usano la porta
    local pids=$(sudo lsof -ti:$port 2>/dev/null || true)
    
    if [ -n "$pids" ]; then
        print_warning "Processo trovato sulla porta $port (PID: $pids). Uccidendo..."
        echo "$pids" | xargs sudo kill -9 2>/dev/null || true
        sleep 2  # Aspetta che il processo termini
        print_status "Processo precedente ucciso."
    else
        print_status "Porta $port libera."
    fi
}

# Funzione per avviare l'app in modalità sviluppo
run_dev() {
    print_header "Avvio Applicazione (Modalità Sviluppo)"
    
    check_poetry
    
    # Ottieni la porta dalle impostazioni
    PORT=$(get_port)
    print_status "Usando porta: $PORT"
    
    # Uccidi il server esistente se attivo
    kill_existing_server $PORT
    
    # Avvia il database con Docker se non è già attivo
    if ! docker-compose -f docker-compose.dev.yml ps postgres | grep -q "Up"; then
        print_status "Avviando database PostgreSQL con Docker..."
        # Libera la porta del database se occupata
        kill_existing_db
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
        configurazione_totale
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
    db-stop)
        stop_db
        ;;
    help|*)
        show_help
        ;;
esac