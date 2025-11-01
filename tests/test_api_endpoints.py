#!/usr/bin/env python3
"""
Test script per verificare il funzionamento degli endpoint API del sistema lifecycle
"""

import requests
import json
from datetime import datetime

# Configurazione
BASE_URL = "http://localhost:8080"
TEST_USER_ID = "test_api_user"

def test_endpoint(method, endpoint, data=None, expected_status=200):
    """Testa un endpoint API"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
        else:
            print(f"❌ Metodo HTTP non supportato: {method}")
            return False
            
        print(f"🔍 {method.upper()} {endpoint}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == expected_status:
            try:
                result = response.json()
                print(f"   ✅ Risposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return True, result
            except:
                print(f"   ✅ Risposta: {response.text}")
                return True, response.text
        else:
            print(f"   ❌ Status atteso: {expected_status}, ricevuto: {response.status_code}")
            print(f"   Errore: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"   ❌ Errore durante la richiesta: {e}")
        return False, None

def main():
    print("🚀 Test degli endpoint API del sistema lifecycle")
    print("=" * 60)
    
    # Test 1: Health check
    print("\n📋 Test 1: Health check")
    success, _ = test_endpoint("GET", "/health")
    
    # Test 2: Gemini health check
    print("\n📋 Test 2: Gemini health check")
    success, _ = test_endpoint("GET", "/gemini/health")
    
    # Test 3: Chat con lifecycle
    print("\n📋 Test 3: Chat con lifecycle")
    chat_data = {
        "user_id": TEST_USER_ID,
        "message": "Ciao, sono interessato al vostro programma di nutrizione"
    }
    success, chat_result = test_endpoint("POST", "/chat/lifecycle", chat_data)
    
    # Test 4: Statistiche lifecycle
    print("\n📋 Test 4: Statistiche lifecycle")
    success, stats = test_endpoint("GET", f"/lifecycle/stats/{TEST_USER_ID}")
    
    # Test 5: Lifecycle corrente
    print("\n📋 Test 5: Lifecycle corrente")
    success, current = test_endpoint("GET", f"/lifecycle/current/{TEST_USER_ID}")
    
    # Test 6: Secondo messaggio per testare transizione
    print("\n📋 Test 6: Secondo messaggio (transizione)")
    chat_data2 = {
        "user_id": TEST_USER_ID,
        "message": "Sì, vorrei saperne di più sulla nutrizione"
    }
    success, chat_result2 = test_endpoint("POST", "/chat/lifecycle", chat_data2)
    
    # Test 7: Statistiche dopo transizione
    print("\n📋 Test 7: Statistiche dopo transizione")
    success, stats_after = test_endpoint("GET", f"/lifecycle/stats/{TEST_USER_ID}")
    
    # Test 8: Reset utente
    print("\n📋 Test 8: Reset utente")
    success, reset_result = test_endpoint("POST", f"/lifecycle/reset/{TEST_USER_ID}")
    
    # Test 9: Statistiche dopo reset
    print("\n📋 Test 9: Statistiche dopo reset")
    success, stats_reset = test_endpoint("GET", f"/lifecycle/stats/{TEST_USER_ID}")
    
    print("\n✅ Test degli endpoint completati!")
    print("=" * 60)

if __name__ == "__main__":
    main()