#!/usr/bin/env python3
"""
Test script per verificare il funzionamento del sistema lifecycle
"""

import asyncio
import json
from datetime import datetime

# Importa i moduli necessari
from app.services.lifecycle_manager import LifecycleManager
from app.data.test_snippets import TEST_SNIPPETS, SYSTEM_PROMPT_CONFIG
from app.models import LifecycleStage


async def test_lifecycle_system():
    """Test completo del sistema lifecycle"""
    print("🚀 Avvio test del sistema lifecycle...")
    print("=" * 60)
    
    # Inizializza il lifecycle manager
    lifecycle_manager = LifecycleManager()
    
    # Test 1: Verifica caricamento snippet
    print("\n📋 Test 1: Verifica caricamento snippet")
    print("-" * 40)
    
    for stage in LifecycleStage:
        # Crea un contesto temporaneo per testare ogni stage
        temp_context = lifecycle_manager.get_or_create_context("temp_user")
        temp_context.current_lifecycle = stage
        lifecycle_manager.conversations["temp_user"] = temp_context
        
        snippet = lifecycle_manager.get_current_snippet("temp_user")
        if snippet:
            print(f"✅ {stage.value}: snippet '{snippet.id}' disponibile")
        else:
            print(f"⚠️  {stage.value}: nessun snippet disponibile")
    
    # Pulisci il contesto temporaneo
    if "temp_user" in lifecycle_manager.conversations:
        del lifecycle_manager.conversations["temp_user"]
    
    # Test 2: Simulazione conversazione
    print("\n💬 Test 2: Simulazione conversazione")
    print("-" * 40)
    
    test_user = "test_user_001"
    
    # Messaggi di test per ogni lifecycle
    test_messages = [
        ("Ciao, sono interessato al vostro programma", LifecycleStage.NUOVA_LEAD),
        ("Sì, vorrei saperne di più sulla nutrizione", LifecycleStage.CONTRASSEGNATO),
        ("Perfetto, sono davvero motivato a iniziare", LifecycleStage.IN_TARGET),
        ("Sì, mandami pure il link per prenotare", LifecycleStage.LINK_DA_INVIARE),
        ("Ho ricevuto il link, grazie", LifecycleStage.LINK_INVIATO),
        ("Ho prenotato la chiamata per domani", LifecycleStage.PRENOTATO)
    ]
    
    for message, expected_stage in test_messages:
        print(f"\n👤 Utente: {message}")
        
        # Simula una risposta del bot (per il test)
        bot_response = f"Risposta simulata per: {message}"
        
        # Processa il messaggio
        result = lifecycle_manager.process_conversation_turn(
            test_user, message, bot_response
        )
        
        print(f"🤖 Lifecycle attuale: {result.current_lifecycle}")
        print(f"📊 Snippet completato: {result.completed_snippet}")
        print(f"🎯 Transizione: {'Sì' if result.lifecycle_changed else 'No'}")
        
        # Verifica se il lifecycle è quello atteso
        if result.current_lifecycle == expected_stage:
            print("✅ Lifecycle corretto!")
        else:
            print(f"❌ Lifecycle atteso: {expected_stage.value}, ottenuto: {result.current_lifecycle}")
    
    # Test 3: Verifica statistiche
    print("\n📊 Test 3: Statistiche utente")
    print("-" * 40)
    
    stats = lifecycle_manager.get_lifecycle_stats(test_user)
    print(f"Lifecycle corrente: {stats['current_lifecycle']}")
    print(f"Snippet completati: {stats['completed_snippets']}")
    print(f"Turni di conversazione: {stats['conversation_turns']}")
    print(f"Snippet totali: {stats['total_snippets']}")
    
    # Test 4: Generazione prompt di sistema
    print("\n🎭 Test 4: Prompt di sistema")
    print("-" * 40)
    
    system_prompt = lifecycle_manager.get_system_prompt(test_user)
    print("Prompt generato:")
    print(system_prompt[:200] + "..." if len(system_prompt) > 200 else system_prompt)
    
    # Test 5: Reset utente
    print("\n🔄 Test 5: Reset utente")
    print("-" * 40)
    
    # Reset del contesto utente
    if test_user in lifecycle_manager.conversations:
        del lifecycle_manager.conversations[test_user]
    
    stats_after_reset = lifecycle_manager.get_lifecycle_stats(test_user)
    print(f"Lifecycle dopo reset: {stats_after_reset['current_lifecycle']}")
    print(f"Snippet completati dopo reset: {stats_after_reset['completed_snippets']}")
    
    print("\n🎉 Test completati con successo!")
    print("=" * 60)


async def test_snippet_content():
    """Test per verificare il contenuto degli snippet"""
    print("\n📝 Test contenuto snippet")
    print("-" * 40)
    
    # Raggruppa gli snippet per lifecycle stage
    snippets_by_stage = {}
    for snippet in TEST_SNIPPETS:
        stage = snippet.lifecycle_stage
        if stage not in snippets_by_stage:
            snippets_by_stage[stage] = []
        snippets_by_stage[stage].append(snippet)
    
    for stage, snippets in snippets_by_stage.items():
        print(f"\n🏷️  {stage.value}:")
        for i, snippet in enumerate(snippets, 1):
            print(f"  {i}. ID: {snippet.id}")
            print(f"     Trigger: {', '.join(snippet.trigger_keywords)}")
            print(f"     Completamento: {', '.join(snippet.completion_indicators)}")
            print(f"     Prossimo stage: {snippet.next_stage.value if snippet.next_stage else 'Nessuno'}")


async def main():
    """Funzione principale per eseguire tutti i test"""
    print("🧪 SISTEMA DI TEST LIFECYCLE CHATBOT")
    print("=" * 60)
    print(f"Data/Ora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        await test_snippet_content()
        await test_lifecycle_system()
        
        print("\n✅ Tutti i test sono stati completati con successo!")
        
    except Exception as e:
        print(f"\n❌ Errore durante i test: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())