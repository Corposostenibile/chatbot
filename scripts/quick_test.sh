#!/bin/bash

# Script per test rapido del chatbot
# Verifica che tutti gli endpoint funzionino

BASE_URL="http://localhost:8080"

echo "🚀 Test rapido del chatbot unificato"
echo "🌐 Base URL: $BASE_URL"
echo "=================================="

# Test endpoint root
echo "📍 Test endpoint root (/):"
curl -s "$BASE_URL/" && echo ""

echo ""
echo "📍 Test endpoint health (/health):"
curl -s "$BASE_URL/health" && echo ""

echo ""
echo "📍 Test endpoint status (/status):"
curl -s "$BASE_URL/status" && echo ""

echo ""
echo "📍 Test endpoint unified health (/unified/health):"
curl -s "$BASE_URL/unified/health" && echo ""

echo ""
echo "📍 Test messaggio chat (/chat):"
curl -s -X POST "$BASE_URL/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "Test rapido", "user_id": "quick_test", "session_id": "quick_session"}' && echo ""

echo ""
echo "✅ Test rapido completato!"