#!/bin/bash

# Local Development Script for Chatbot
# Gestisce lo sviluppo locale senza Docker

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$PROJECT_ROOT/.venv"
DB_PATH="$PROJECT_ROOT/chatbot_local.db"
LOG_FILE="$PROJECT_ROOT/local_dev.log"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE" >&2
}

warn() {
    echo -e "${YELLOW}[WARN] $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

# Check if we're in the right directory
check_project_root() {
    if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        error "Errore: pyproject.toml non trovato. Eseguire da scripts/local.sh"
        exit 1
    fi
}

# Check if Python 3.11+ is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        error "Python 3 non trovato. Installare Python 3.11+"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ "$(printf '%s\n' "$PYTHON_VERSION" "3.11" | sort -V | head -n1)" != "3.11" ]]; then
        error "Python $PYTHON_VERSION trovato, ma serve 3.11+. Aggiornare Python."
        exit 1
    fi

    log "Python $PYTHON_VERSION trovato ✓"
}

# Setup virtual environment
setup_venv() {
    log "Configurazione ambiente virtuale..."

    if [[ ! -d "$VENV_PATH" ]]; then
        log "Creazione virtual environment in $VENV_PATH"
        python3 -m venv "$VENV_PATH"
    else
        info "Virtual environment già esistente"
    fi

    # Activate virtual environment
    source "$VENV_PATH/bin/activate"

    # Upgrade pip
    pip install --upgrade pip

    log "Ambiente virtuale configurato ✓"
}

# Install dependencies
install_deps() {
    log "Installazione dipendenze..."

    source "$VENV_PATH/bin/activate"

    # Install Poetry if not available
    if ! command -v poetry &> /dev/null; then
        pip install poetry
    fi

    # Configure Poetry
    poetry config virtualenvs.create false
    poetry config virtualenvs.in-project false

    # Install dependencies
    cd "$PROJECT_ROOT"
    poetry install

    log "Dipendenze installate ✓"
}

# Initialize local database (SQLite or PostgreSQL)
init_db() {
    log "Inizializzazione database locale..."

    source "$VENV_PATH/bin/activate"

    # Create .env.local if it doesn't exist
    if [[ ! -f "$PROJECT_ROOT/.env.local" ]]; then
        cat > "$PROJECT_ROOT/.env.local" << 'EOF'
# Configurazione dell'applicazione
APP_NAME="Chatbot API"
APP_VERSION="0.1.0"
DEBUG=true
LOG_LEVEL="DEBUG"

# Configurazione server
HOST="0.0.0.0"
PORT=8081

# Configurazione sicurezza
SECRET_KEY="dev-secret-key-change-in-production"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL="postgresql+asyncpg://chatbot:password@localhost:5432/chatbot"

# Google Cloud
GOOGLE_CLOUD_PROJECT=""

# API Keys (aggiungi le tue chiavi qui)
OPENAI_API_KEY=""
ANTHROPIC_API_KEY=""

GOOGLE_AI_API_KEY="AIzaSyDW1hsoLYeeSt0F2wMOD7txYB6o60pfryQ"
EOF
        warn "Creato .env.local - configurare le API keys e il database"
    fi

    # Load environment variables
    if [[ -f "$PROJECT_ROOT/.env.local" ]]; then
        set -a
        source "$PROJECT_ROOT/.env.local"
        set +a
    fi

    cd "$PROJECT_ROOT"

    # Check database type and initialize accordingly
    if [[ "$DATABASE_URL" == *"sqlite"* ]]; then
        log "Usando SQLite per lo sviluppo locale"
        DB_PATH=$(echo "$DATABASE_URL" | sed 's|sqlite://||')
        mkdir -p "$(dirname "$DB_PATH")"
    elif [[ "$DATABASE_URL" == *"postgresql"* ]]; then
        log "Usando PostgreSQL per lo sviluppo locale"
        # Check if PostgreSQL is running
        if ! pg_isready -h localhost -p 5432 &> /dev/null; then
            warn "PostgreSQL non sembra essere in esecuzione su localhost:5432"
            warn "Assicurati che PostgreSQL sia installato e in esecuzione"
            warn "Oppure usa SQLite modificando DATABASE_URL in .env.local"
        fi
    else
        warn "Tipo database non riconosciuto in DATABASE_URL"
    fi

    # Run database migrations
    if [[ -f "alembic.ini" ]]; then
        alembic upgrade head
        log "Migrazioni database applicate ✓"
    else
        warn "alembic.ini non trovato, saltando migrazioni"
    fi

    # Initialize system prompt
    log "Inizializzazione prompt di sistema..."
    python3 -c "
import asyncio
import os
os.environ.setdefault('DATABASE_URL', '$DATABASE_URL')

from app.database import engine, Base
from app.services.system_prompt_service import SystemPromptService

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await SystemPromptService.initialize_default_prompt()

asyncio.run(init_db())
" 2>/dev/null || warn "Impossibile inizializzare il prompt di sistema"

    log "Database locale inizializzato ✓"
}

# Run the application locally
run_app() {
    log "Avvio applicazione locale..."

    source "$VENV_PATH/bin/activate"

    # Load environment variables from .env.local
    if [[ -f "$PROJECT_ROOT/.env.local" ]]; then
        set -a
        source "$PROJECT_ROOT/.env.local"
        set +a
    else
        warn ".env.local non trovato, usando valori di default"
        export DATABASE_URL="sqlite:///$DB_PATH"
        export DEBUG=true
        export LOG_LEVEL=debug
        export HOST="127.0.0.1"
        export PORT=8081
    fi

    cd "$PROJECT_ROOT"

    # Verify database connection
    if [[ "$DATABASE_URL" == *"postgresql"* ]]; then
        log "Verifica connessione PostgreSQL..."
        python3 -c "
import psycopg2
import os

dsn = os.environ.get('DATABASE_URL', '').replace('postgresql+asyncpg://', 'postgresql://')
try:
    conn = psycopg2.connect(dsn)
    conn.close()
    print('✅ Connessione PostgreSQL OK')
except Exception as e:
    print(f'⚠️  Errore connessione PostgreSQL: {e}')
    print('💡 Assicurati che PostgreSQL sia in esecuzione')
" 2>/dev/null || warn "Impossibile verificare connessione database"
    fi

    log "Avvio server su http://${HOST:-127.0.0.1}:${PORT:-8081}"
    log "Premi Ctrl+C per fermare"

    # Run with uvicorn
    uvicorn app.main:app \
        --host "${HOST:-127.0.0.1}" \
        --port "${PORT:-8081}" \
        --reload \
        --log-level "${LOG_LEVEL:-info}"
}

# Run tests
run_tests() {
    log "Esecuzione test..."

    source "$VENV_PATH/bin/activate"

    # Set test database
    export DATABASE_URL="sqlite:///$PROJECT_ROOT/test.db"

    cd "$PROJECT_ROOT"

    # Install test dependencies if needed
    pip install pytest pytest-asyncio httpx

    # Run tests
    python -m pytest tests/ -v --tb=short

    # Clean up test database
    rm -f "$PROJECT_ROOT/test.db"

    log "Test completati ✓"
}

# Run linting
run_lint() {
    log "Esecuzione linting..."

    source "$VENV_PATH/bin/activate"

    cd "$PROJECT_ROOT"

    # Install linting tools
    pip install flake8 black isort mypy

    # Run linting
    echo "Running flake8..."
    flake8 app/ tests/ --max-line-length=88 --extend-ignore=E203,W503

    echo "Running black check..."
    black --check --diff app/ tests/

    echo "Running isort check..."
    isort --check-only --diff app/ tests/

    log "Linting completato ✓"
}

# Format code
format_code() {
    log "Formattazione codice..."

    source "$VENV_PATH/bin/activate"

    cd "$PROJECT_ROOT"

    # Install formatting tools
    pip install black isort

    # Format code
    black app/ tests/
    isort app/ tests/

    log "Codice formattato ✓"
}

# Clean local environment
clean_env() {
    log "Pulizia ambiente locale..."

    # Remove virtual environment
    if [[ -d "$VENV_PATH" ]]; then
        rm -rf "$VENV_PATH"
        log "Virtual environment rimosso"
    fi

    # Remove local database
    if [[ -f "$DB_PATH" ]]; then
        rm -f "$DB_PATH"
        log "Database locale rimosso"
    fi

    # Remove log file
    if [[ -f "$LOG_FILE" ]]; then
        rm -f "$LOG_FILE"
        log "File di log rimosso"
    fi

    # Remove test database if exists
    if [[ -f "$PROJECT_ROOT/test.db" ]]; then
        rm -f "$PROJECT_ROOT/test.db"
    fi

    # Remove __pycache__ directories
    find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -name "*.pyc" -delete 2>/dev/null || true

    log "Pulizia completata ✓"
}

# Show status
show_status() {
    echo "=== Status Sviluppo Locale ==="
    echo ""

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        echo -e "🐍 Python: ${GREEN}$PYTHON_VERSION${NC}"
    else
        echo -e "🐍 Python: ${RED}Non trovato${NC}"
    fi

    # Check virtual environment
    if [[ -d "$VENV_PATH" ]]; then
        echo -e "📦 Virtual Environment: ${GREEN}Presente ($VENV_PATH)${NC}"
    else
        echo -e "📦 Virtual Environment: ${RED}Assente${NC}"
    fi

    # Check database
    if [[ -f "$PROJECT_ROOT/.env.local" ]]; then
        source "$PROJECT_ROOT/.env.local" 2>/dev/null || true
        if [[ "$DATABASE_URL" == *"sqlite"* ]]; then
            DB_PATH_LOCAL=$(echo "$DATABASE_URL" | sed 's|sqlite:///||')
            if [[ -f "$DB_PATH_LOCAL" ]]; then
                DB_SIZE=$(du -h "$DB_PATH_LOCAL" 2>/dev/null | cut -f1)
                echo -e "🗄️  Database: ${GREEN}SQLite ($DB_SIZE)${NC}"
            else
                echo -e "🗄️  Database: ${YELLOW}SQLite (non inizializzato)${NC}"
            fi
        elif [[ "$DATABASE_URL" == *"postgresql"* ]]; then
            if pg_isready -h localhost -p 5432 &> /dev/null; then
                echo -e "🗄️  Database: ${GREEN}PostgreSQL (localhost:5432)${NC}"
            else
                echo -e "🗄️  Database: ${YELLOW}PostgreSQL (server non raggiungibile)${NC}"
            fi
        else
            echo -e "🗄️  Database: ${YELLOW}Configurazione sconosciuta${NC}"
        fi
    else
        echo -e "🗄️  Database: ${RED}.env.local assente${NC}"
    fi

    # Check .env.local
    if [[ -f "$PROJECT_ROOT/.env.local" ]]; then
        echo -e "⚙️  Config Locale: ${GREEN}Presente${NC}"
    else
        echo -e "⚙️  Config Locale: ${RED}Assente${NC}"
    fi

    # Check if app can be imported
    if [[ -d "$VENV_PATH" ]]; then
        source "$VENV_PATH/bin/activate" 2>/dev/null || true
        if [[ -f "$PROJECT_ROOT/.env.local" ]]; then
            source "$PROJECT_ROOT/.env.local" 2>/dev/null || true
        fi
        if python3 -c "import app.main" 2>/dev/null; then
            echo -e "🚀 Applicazione: ${GREEN}Importabile${NC}"
        else
            echo -e "🚀 Applicazione: ${RED}Errori di import${NC}"
        fi
    fi

    echo ""
    echo "=== Comandi Disponibili ==="
    echo "local-setup      - Configurazione iniziale completa"
    echo "local-install    - Installa dipendenze"
    echo "local-db-init    - Inizializza database locale"
    echo "local-run        - Avvia applicazione"
    echo "local-test       - Esegue test"
    echo "local-lint       - Esegue linting"
    echo "local-format     - Formatta codice"
    echo "local-clean      - Pulisce ambiente"
    echo "local-status     - Mostra questo status"
}

# Main setup function
setup_local() {
    log "=== Configurazione Sviluppo Locale ==="

    check_project_root
    check_python
    setup_venv
    install_deps
    init_db

    log "=== Configurazione Completata ==="
    echo ""
    echo "Per avviare l'applicazione:"
    echo "  ./scripts/local.sh local-run"
    echo ""
    echo "Per eseguire i test:"
    echo "  ./scripts/local.sh local-test"
    echo ""
    echo "Dashboard disponibile su: http://127.0.0.1:8081"
}

# Main function
main() {
    case "${1:-status}" in
        "setup"|"local-setup")
            setup_local
            ;;
        "install"|"local-install")
            check_project_root
            check_python
            setup_venv
            install_deps
            ;;
        "db-init"|"local-db-init")
            check_project_root
            init_db
            ;;
        "run"|"local-run")
            check_project_root
            run_app
            ;;
        "test"|"local-test")
            check_project_root
            run_tests
            ;;
        "lint"|"local-lint")
            check_project_root
            run_lint
            ;;
        "format"|"local-format")
            check_project_root
            format_code
            ;;
        "clean"|"local-clean")
            clean_env
            ;;
        "status"|"local-status")
            show_status
            ;;
        *)
            error "Comando non riconosciuto: $1"
            echo ""
            echo "Comandi disponibili:"
            echo "  local-setup      - Configurazione iniziale completa"
            echo "  local-install    - Installa dipendenze"
            echo "  local-db-init    - Inizializza database locale"
            echo "  local-run        - Avvia applicazione"
            echo "  local-test       - Esegue test"
            echo "  local-lint       - Esegue linting"
            echo "  local-format     - Formatta codice"
            echo "  local-clean      - Pulisce ambiente"
            echo "  local-status     - Mostra status"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"