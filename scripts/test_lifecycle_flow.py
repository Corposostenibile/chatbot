#!/usr/bin/env python3
"""
Script di test per simulare un lifecycle completo del chatbot
Chiama direttamente gli endpoint FastAPI
"""
import asyncio
import asyncio
import json
import time
from typing import Dict, List

# Import dell'agente unificato
from app.services.unified_agent import unified_agent

TEST_SESSION_ID = f"test_lifecycle_{int(time.time())}"

class ChatbotTester:
    """Classe per testare il lifecycle del chatbot"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation_history = []

    async def send_message(self, message: str) -> Dict:
        """Invia un messaggio al chatbot chiamando direttamente l'agente"""
        try:
            # Chiama direttamente l'agente unificato
            response = await unified_agent.chat(self.session_id, message)
            
            # Converte la risposta in dict per compatibilità
            response_data = {
                "response": response.message,
                "session_id": self.session_id,
                "current_lifecycle": response.current_lifecycle.value,
                "lifecycle_changed": response.lifecycle_changed,
                "previous_lifecycle": response.previous_lifecycle.value if response.previous_lifecycle else None,
                "next_actions": response.next_actions,
                "ai_reasoning": response.ai_reasoning,
                "timestamp": str(int(time.time()))
            }
            
            self.conversation_history.append({
                "user": message,
                "bot": response_data.get("response", ""),
                "lifecycle": response_data.get("current_lifecycle", ""),
                "changed": response_data.get("lifecycle_changed", False)
            })
            return response_data

        except Exception as e:
            print(f"❌ Errore chiamata agente: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def get_session_info(self) -> Dict:
        """Ottiene informazioni sulla sessione chiamando direttamente l'agente"""
        try:
            response = await unified_agent.get_session_info(self.session_id)
            return response
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

async def test_complete_lifecycle():
    """Test del lifecycle completo"""
    print("🚀 Avvio test lifecycle completo del chatbot")
    print(f"🆔 Session ID: {TEST_SESSION_ID}")

    tester = ChatbotTester(TEST_SESSION_ID)

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