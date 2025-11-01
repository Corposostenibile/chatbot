#!/usr/bin/env python3
"""
Test E2E Semplificato - Focus su User Journey
Traccia: Messaggio Utente → Risposta AI → Lifecycle
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any
from colorama import Fore, Style, init

# Inizializza colorama
init(autoreset=True)

from app.services.lifecycle_manager import LifecycleManager
from app.services.gemini_service import GeminiService
from app.models import LifecycleStage


class SimpleE2ERunner:
    """Runner semplificato per tracciare il percorso utente"""
    
    def __init__(self):
        self.lifecycle_manager = LifecycleManager()
        self.gemini_service = GeminiService()
    
    def print_separator(self, title: str = ""):
        """Stampa un separatore"""
        if title:
            print(f"\n{Fore.CYAN}{'='*20} {title} {'='*20}")
        else:
            print(f"{Fore.WHITE}{'-'*60}")
    
    def print_flow_step(self, step_num: int, user_msg: str, ai_response: str, lifecycle: LifecycleStage, changed: bool = False):
        """Stampa un singolo step del flusso"""
        print(f"\n{Fore.YELLOW}📍 STEP {step_num}")
        print(f"{Fore.CYAN}👤 USER: {user_msg}")
        print(f"{Fore.MAGENTA}🤖 AI:   {ai_response[:150]}{'...' if len(ai_response) > 150 else ''}")
        
        lifecycle_color = Fore.GREEN if changed else Fore.WHITE
        change_indicator = " ✨ CAMBIATO!" if changed else ""
        print(f"{lifecycle_color}🔄 LIFECYCLE: {lifecycle.value}{change_indicator}")
    
    async def simulate_user_journey(self, user_id: str) -> Dict[str, Any]:
        """Simula il percorso utente completo con tracciamento chiaro"""
        
        self.print_separator("SIMULAZIONE PERCORSO UTENTE")
        print(f"{Fore.WHITE}🆔 User ID: {user_id}")
        print(f"{Fore.WHITE}⏰ Inizio: {datetime.now().strftime('%H:%M:%S')}")
        
        # Messaggi del percorso utente
        user_messages = [
            "Ciao! Ho visto la vostra pubblicità sulla nutrizione e sono interessato",
            "Sì, vorrei saperne di più sui vostri programmi nutrizionali", 
            "Perfetto! Mandatemi pure il link, sono molto motivato",
            "Ho guardato il materiale, è molto interessante. Vorrei prenotare una chiamata"
        ]
        
        journey_data = []
        
        for i, message in enumerate(user_messages, 1):
            self.print_separator(f"INTERAZIONE {i}")
            
            # Stato prima del messaggio
            stats_before = self.lifecycle_manager.get_lifecycle_stats(user_id)
            lifecycle_before = LifecycleStage(stats_before['current_lifecycle'])
            
            try:
                # Invia messaggio e ottieni risposta
                if self.gemini_service.is_available():
                    print(f"{Fore.BLUE}🔄 Invio a Gemini...")
                    chat_response = await self.gemini_service.chat_with_lifecycle(
                        user_id=user_id,
                        message=message
                    )
                    ai_response = chat_response.message
                    lifecycle_after = chat_response.current_lifecycle
                    lifecycle_changed = chat_response.lifecycle_changed
                else:
                    print(f"{Fore.YELLOW}⚠️  Gemini non disponibile - simulazione locale")
                    ai_response = f"Risposta simulata per: {message[:50]}..."
                    result = self.lifecycle_manager.process_conversation_turn(
                        user_id=user_id,
                        user_message=message,
                        bot_response=ai_response
                    )
                    lifecycle_after = result.current_lifecycle
                    lifecycle_changed = result.lifecycle_changed
                
                # Stampa il flusso
                self.print_flow_step(i, message, ai_response, lifecycle_after, lifecycle_changed)
                
                # Salva i dati
                step_data = {
                    "step": i,
                    "user_message": message,
                    "ai_response": ai_response,
                    "lifecycle_before": lifecycle_before.value,
                    "lifecycle_after": lifecycle_after.value,
                    "lifecycle_changed": lifecycle_changed,
                    "timestamp": datetime.now().isoformat()
                }
                journey_data.append(step_data)
                
                # Pausa per leggibilità
                time.sleep(0.5)
                
            except Exception as e:
                print(f"{Fore.RED}❌ ERRORE: {str(e)}")
                journey_data.append({
                    "step": i,
                    "error": str(e),
                    "user_message": message
                })
        
        # Riepilogo finale
        self.print_separator("RIEPILOGO PERCORSO")
        
        print(f"{Fore.WHITE}📊 Totale interazioni: {len(user_messages)}")
        print(f"{Fore.WHITE}✅ Completate: {len([d for d in journey_data if 'error' not in d])}")
        print(f"{Fore.WHITE}❌ Errori: {len([d for d in journey_data if 'error' in d])}")
        
        # Mostra evoluzione lifecycle
        print(f"\n{Fore.CYAN}🔄 EVOLUZIONE LIFECYCLE:")
        for data in journey_data:
            if 'error' not in data:
                arrow = "→" if data['lifecycle_changed'] else "="
                print(f"   Step {data['step']}: {data['lifecycle_before']} {arrow} {data['lifecycle_after']}")
        
        # Stato finale
        final_stats = self.lifecycle_manager.get_lifecycle_stats(user_id)
        print(f"\n{Fore.GREEN}🎯 STATO FINALE:")
        print(f"   Lifecycle: {final_stats['current_lifecycle']}")
        print(f"   Snippet completati: {final_stats['completed_snippets']}")
        print(f"   Conversazioni: {final_stats['conversation_turns']}")
        
        return {
            "user_id": user_id,
            "journey_data": journey_data,
            "final_stats": final_stats
        }


async def main():
    """Esegue il test semplificato"""
    
    runner = SimpleE2ERunner()
    test_user_id = f"simple_test_{int(time.time())}"
    
    print(f"{Fore.CYAN}{Style.BRIGHT}🧪 TEST E2E SEMPLIFICATO")
    print(f"{Fore.WHITE}Focus: Messaggio Utente → Risposta AI → Lifecycle")
    
    try:
        result = await runner.simulate_user_journey(test_user_id)
        
        print(f"\n{Fore.GREEN}✅ Test completato con successo!")
        print(f"{Fore.WHITE}⏰ Completato alle: {datetime.now().strftime('%H:%M:%S')}")
        
    except Exception as e:
        print(f"\n{Fore.RED}❌ Errore durante il test: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())