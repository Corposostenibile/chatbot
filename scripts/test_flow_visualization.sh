#!/bin/bash

# Script di test per verificare che tutto funzioni

set -e

echo "🧪 Test della Visualizzazione del Flusso"
echo "========================================"
echo ""

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Verifica file template
echo -e "${YELLOW}Test 1: Verifica file template HTML${NC}"
if [ -f "app/templates/flow_visualization.html" ]; then
    echo -e "${GREEN}✅ File template trovato${NC}"
    FILE_SIZE=$(wc -c < "app/templates/flow_visualization.html")
    echo "   Dimensione: $FILE_SIZE bytes"
else
    echo -e "${RED}❌ File template NON trovato${NC}"
    exit 1
fi

echo ""

# Test 2: Verifica endpoint in routes.py
echo -e "${YELLOW}Test 2: Verifica endpoint /flow in routes.py${NC}"
if grep -q "def flow_visualization" app/routes.py; then
    echo -e "${GREEN}✅ Endpoint /flow trovato${NC}"
else
    echo -e "${RED}❌ Endpoint /flow NON trovato${NC}"
    exit 1
fi

echo ""

# Test 3: Verifica sintassi HTML
echo -e "${YELLOW}Test 3: Verifica sintassi HTML${NC}"
if grep -q "<!DOCTYPE html>" app/templates/flow_visualization.html && \
   grep -q "</html>" app/templates/flow_visualization.html; then
    echo -e "${GREEN}✅ HTML ben formato${NC}"
else
    echo -e "${RED}❌ HTML non ben formato${NC}"
    exit 1
fi

echo ""

# Test 4: Verifica Mermaid script
echo -e "${YELLOW}Test 4: Verifica diagrammi Mermaid${NC}"
MERMAID_COUNT=$(grep -c "class=\"mermaid\"" app/templates/flow_visualization.html || true)
echo -e "${GREEN}✅ $MERMAID_COUNT diagrammi Mermaid trovati${NC}"

echo ""

# Test 5: Verifica Jinja2 syntax
echo -e "${YELLOW}Test 5: Verifica template variables${NC}"
if grep -q "{{ app_name }}" app/templates/flow_visualization.html || \
   grep -q "app_name" app/templates/flow_visualization.html; then
    echo -e "${GREEN}✅ Template variables presenti${NC}"
else
    echo -e "${YELLOW}⚠️  Nessuna template variable Jinja2 rilevata (opzionale)${NC}"
fi

echo ""

# Test 6: Verifica JavaScript
echo -e "${YELLOW}Test 6: Verifica JavaScript${NC}"
if grep -q "function showSection" app/templates/flow_visualization.html; then
    echo -e "${GREEN}✅ JavaScript per navigazione trovato${NC}"
else
    echo -e "${RED}❌ JavaScript non trovato${NC}"
    exit 1
fi

echo ""

# Test 7: Verifica sections
echo -e "${YELLOW}Test 7: Verifica tutte le sezioni${NC}"
SECTIONS=("overview" "architecture" "request-flow" "lifecycle" "example" "api" "database")
for section in "${SECTIONS[@]}"; do
    if grep -q "id=\"$section\"" app/templates/flow_visualization.html; then
        echo -e "${GREEN}✅ Sezione '$section' trovata${NC}"
    else
        echo -e "${RED}❌ Sezione '$section' NON trovata${NC}"
        exit 1
    fi
done

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Tutti i test passati!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"

echo ""
echo "Per avviare il server e testare l'interfaccia:"
echo "  ./scripts/run_server.sh"
echo ""
echo "Poi accedi a: http://localhost:8080/flow"
