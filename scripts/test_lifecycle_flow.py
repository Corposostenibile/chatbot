#!/usr/bin/env python3
"""
Script di test per simulare un lifecycle completo del chatbot
Chiama gli endpoint HTTP del server FastAPI in esecuzione
"""
import asyncio
import json
import time
from typing import Dict, List

import httpx

from app.config import settings

TEST_SESSION_ID = f"test_lifecycle_{int(time.time())}"
BASE_URL = f"http://localhost:{settings.port}"  # Usa la porta dalle settings

class ChatbotTester:
    """Classe per testare il lifecycle del chatbot"""

    def __init__(self, session_id: str, base_url: str = BASE_URL):
        self.session_id = session_id
        self.base_url = base_url
        self.conversation_history = []

    async def send_message(self, message: str) -> Dict:
        """Invia un messaggio al chatbot chiamando l'endpoint /chat"""
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "message": message,
                    "session_id": self.session_id
                }
                
                response = await client.post(
                    f"{self.base_url}/chat",
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    self.conversation_history.append({
                        "user": message,
                        "bot": response_data.get("response", ""),
                        "lifecycle": response_data.get("current_lifecycle", ""),
                        "changed": response_data.get("lifecycle_changed", False)
                    })
                    return response_data
                else:
                    print(f"❌ Errore HTTP {response.status_code}: {response.text}")
                    return None

        except httpx.RequestError as e:
            print(f"❌ Errore di connessione: {e}")
            return None
        except Exception as e:
            print(f"❌ Errore chiamata endpoint: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def get_session_info(self) -> Dict:
        """Ottiene informazioni sulla sessione chiamando l'endpoint /session/{session_id}"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/session/{self.session_id}",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"❌ Errore HTTP {response.status_code}: {response.text}")
                    return None

        except httpx.RequestError as e:
            print(f"❌ Errore di connessione: {e}")
            return None
        except Exception as e:
            print(f"❌ Errore chiamata get_session_info: {e}")
            return None

    def print_conversation(self):
        """Stampa la conversazione completa"""
        print("\n📝 Conversazione completa:")
        print("=" * 80)
        for i, msg in enumerate(self.conversation_history, 1):
            print(f"{i}. 👤 {msg['user']}")
            print(f"   🤖 {msg['bot']}")
            print(f"   📊 Lifecycle: {msg['lifecycle']} {'(CAMBIO)' if msg['changed'] else ''}")
            print("-" * 40)

async def check_server_health(base_url: str) -> bool:
    """Verifica se il server è in esecuzione e risponde"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health", timeout=5.0)
            return response.status_code == 200
    except Exception:
        return False


async def test_complete_lifecycle():
    """Test del lifecycle completo"""
    print("🚀 Avvio test lifecycle completo del chatbot")
    print(f"🆔 Session ID: {TEST_SESSION_ID}")
    print(f"🌐 Server URL: {BASE_URL}")
    print(f"🔌 Porta configurata: {settings.port}")

    # Verifica che il server sia in esecuzione
    print("\n🔍 Verifica connessione al server...")
    if not await check_server_health(BASE_URL):
        print("❌ Il server non è in esecuzione o non risponde!")
        print(f"   Assicurati che il server sia avviato su {BASE_URL}")
        print("   Puoi avviarlo con: ./scripts/local-dev.sh dev")
        return False
    
    print("✅ Server raggiungibile")

    tester = ChatbotTester(TEST_SESSION_ID, BASE_URL)

    # Sequenza di messaggi per testare il lifecycle
    test_messages = [
        # NUOVA_LEAD
        "Ciao, sono interessato ai vostri servizi di nutrizione",
        "Ho problemi con il peso e vorrei migliorare la mia alimentazione",

        # CONTRASSEGNATO (dopo problemi specifici)
        "Sì, ho difficoltà a perdere peso nonostante faccia sport",
        "Mi sento sempre stanco e ho poca energia",

        # IN_TARGET (dopo motivazione alta)
        "È molto importante per me, mi sta influenzando la vita quotidiana",
        "Vorrei davvero cambiare e migliorare il mio benessere",

        # LINK_DA_INVIARE (dopo interesse per consulenza)
        "Mi interessa molto la vostra consulenza gratuita",
        "Sì, vorrei saperne di più sul percorso personalizzato",

        # LINK_INVIATO (finale)
        "Perfetto, sono pronto per prenotare"
    ]

    expected_lifecycles = [
        "NUOVA_LEAD",
        "NUOVA_LEAD",  # Potrebbe rimanere o cambiare
        "CONTRASSEGNATO",
        "CONTRASSEGNATO",
        "IN_TARGET",
        "IN_TARGET",
        "LINK_DA_INVIARE",
        "LINK_DA_INVIARE",
        "LINK_INVIATO"
    ]

    print("\n📤 Invio messaggi di test...")

    for i, message in enumerate(test_messages):
        print(f"\n🔄 Messaggio {i+1}/{len(test_messages)}: '{message[:50]}...'")

        response = await tester.send_message(message)

        if response:
            current_lifecycle = response.get("current_lifecycle", "")
            expected = expected_lifecycles[i] if i < len(expected_lifecycles) else "LINK_INVIATO"

            if current_lifecycle == expected:
                print(f"✅ Lifecycle corretto: {current_lifecycle}")
            else:
                print(f"⚠️  Lifecycle diverso dal previsto: {current_lifecycle} (atteso: {expected})")

            if response.get("lifecycle_changed"):
                print(f"🔄 TRANSIZIONE LIFECYCLE rilevata!")
        else:
            print("❌ Nessuna risposta ricevuta")
            break

        # Pausa minima tra messaggi (opzionale per test)
        await asyncio.sleep(0.1)

    # Verifica finale della sessione
    print("\n🔍 Verifica informazioni sessione finale...")
    session_info = await tester.get_session_info()
    if session_info:
        print(f"✅ Sessione finale - Lifecycle: {session_info.get('current_lifecycle', 'N/A')}")
        print(f"✅ Conversazioni: {session_info.get('conversation_length', 0)} messaggi")
    else:
        print("❌ Impossibile ottenere info sessione")

    # Mostra conversazione completa
    tester.print_conversation()

    # Verifica se abbiamo raggiunto LINK_INVIATO
    final_lifecycle = session_info.get('current_lifecycle') if session_info else None
    if final_lifecycle == "LINK_INVIATO":
        print("\n🎉 SUCCESSO: Lifecycle completo raggiunto!")
        return True
    else:
        print(f"\n⚠️  ATTENZIONE: Lifecycle finale è {final_lifecycle}, non LINK_INVIATO")
        return False

async def main():
    """Funzione principale"""
    try:
        success = await test_complete_lifecycle()
        print(f"\n{'🎉 Test completato con successo!' if success else '⚠️  Test completato con avvertenze'}")
        return success
    except KeyboardInterrupt:
        print("\n⏹️  Test interrotto dall'utente")
        return False
    except Exception as e:
        print(f"\n❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)