#!/bin/bash

# Script per avviare il server FastAPI e accedere alla visualizzazione del flusso

set -e

echo "🚀 Avvio del server FastAPI..."

# Verifica che siamo nella directory corretta
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Errore: esegui questo script dalla root del progetto"
    exit 1
fi

# Attiva l'ambiente virtuale se esiste
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Ambiente virtuale attivato"
fi

# Installa dipendenze se necessario
if ! python -m pip show fastapi > /dev/null 2>&1; then
    echo "📦 Installando dipendenze..."
    pip install -e .
fi

# Avvia il server
echo "🌐 Server avviato su http://localhost:8080"
echo "📊 Visualizzazione flusso: http://localhost:8080/flow"
echo "📖 Documentazione API: http://localhost:8080/docs"
echo ""
echo "Premi Ctrl+C per fermare il server"
echo ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
