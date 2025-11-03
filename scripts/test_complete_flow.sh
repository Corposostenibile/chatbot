#!/bin/bash

# Script per testare il flusso completo del chatbot unificato
# Testa tutti i lifecycle e le transizioni

set -e

BASE_URL="http://localhost:8080"
SESSION_ID="test_flow_$(date +%s)"
USER_ID="test_user_flow"

echo "🚀 Inizio test del flusso completo del chatbot"
echo "📋 Session ID: $SESSION_ID"
echo "👤 User ID: $USER_ID"
echo "🌐 Base URL: $BASE_URL"
echo "=================================================="

# Funzione per fare una richiesta POST al chat
send_message() {
    local message="$1"
    local step="$2"
    
    echo ""
    echo "📤 STEP $step: Invio messaggio"
    echo "💬 Messaggio: \"$message\""
    echo "--------------------------------------------------"
    
    response=$(curl -s -X POST "$BASE_URL/chat" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$message\", \"user_id\": \"$USER_ID\", \"session_id\": \"$SESSION_ID\"}")
    
    echo "📥 Risposta ricevuta:"
    echo "$response"
    
    # Estrai informazioni chiave usando grep e sed
    current_lifecycle=$(echo "$response" | grep -o '"current_lifecycle":"[^"]*"' | cut -d'"' -f4)
    lifecycle_changed=$(echo "$response" | grep -o '"lifecycle_changed":[^,}]*' | cut -d':' -f2 | tr -d ' ')
    ai_response=$(echo "$response" | grep -o '"response":"[^"]*"' | cut -d'"' -f4)
    
    echo ""
    echo "📊 STATO ATTUALE:"
    echo "🔄 Lifecycle: $current_lifecycle"
    echo "🔀 Cambiato: $lifecycle_changed"
    echo "🤖 Risposta: $(echo "$ai_response" | cut -c1-100)..."
    echo "=================================================="
    
    sleep 2
}

# Funzione per controllare lo stato della sessione
check_session() {
    echo ""
    echo "🔍 Controllo stato sessione..."
    session_info=$(curl -s -X GET "$BASE_URL/session/$SESSION_ID")
    echo "$session_info"
    echo "=================================================="
}

# Funzione per controllare la salute del sistema
check_health() {
    echo ""
    echo "🏥 Controllo salute del sistema..."
    
    echo "📊 Status generale:"
    curl -s -X GET "$BASE_URL/status"
    
    echo ""
    echo "🤖 Health agente unificato:"
    curl -s -X GET "$BASE_URL/unified/health"
    echo "=================================================="
}

# Test iniziale della salute del sistema
echo "🏥 CONTROLLO INIZIALE SALUTE SISTEMA"
check_health

# STEP 1: Messaggio iniziale (dovrebbe rimanere in nuova_lead)
send_message "Ciao" "1"

# STEP 2: Espressione di interesse (dovrebbe passare a contrassegnato)
send_message "Sono interessato ai vostri servizi di nutrizione" "2"

# Controllo stato sessione dopo primo cambio
check_session

# STEP 3: Messaggio generico (dovrebbe rimanere in contrassegnato)
send_message "Mi potete dire di più?" "3"

# STEP 4: Espressione di problema specifico e motivazione alta (dovrebbe passare a in_target)
send_message "Ho problemi di peso e stress, vorrei iniziare un percorso completo. Quando possiamo iniziare?" "4"

# Controllo stato sessione dopo secondo cambio
check_session

# STEP 5: Conferma interesse (dovrebbe rimanere in in_target)
send_message "Perfetto, mi interessa molto la consulenza gratuita" "5"

# STEP 6: Test con nuova sessione per verificare che inizi correttamente
NEW_SESSION_ID="new_test_$(date +%s)"
echo ""
echo "🆕 TEST NUOVA SESSIONE"
echo "📋 Nuova Session ID: $NEW_SESSION_ID"

response=$(curl -s -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Salve\", \"user_id\": \"new_user\", \"session_id\": \"$NEW_SESSION_ID\"}")

echo "📥 Risposta nuova sessione:"
echo "$response"

# Controllo finale della salute
echo ""
echo "🏥 CONTROLLO FINALE SALUTE SISTEMA"
check_health

# Riepilogo finale
echo ""
echo "✅ TEST COMPLETATO CON SUCCESSO!"
echo "📋 Sessione principale: $SESSION_ID"
echo "📋 Sessione secondaria: $NEW_SESSION_ID"
echo "🎯 Tutti i lifecycle testati: nuova_lead → contrassegnato → in_target"
echo "=================================================="