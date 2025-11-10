"""
Configurazione logger per capturare i log e renderli disponibili all'API
"""
from typing import List
from datetime import datetime
from io import StringIO
from loguru import logger

class LogCapture:
    """Classe per catturare i log dall'agente unificato"""
    
    def __init__(self):
        self.logs: List[str] = []
        self.current_session_logs: List[str] = []
        self.buffer = StringIO()
        
    def add_log(self, level: str, message: str):
        """Aggiunge un log semplice senza timestamp"""
        log_line = message
        self.logs.append(log_line)
        self.current_session_logs.append(log_line)
        
    def start_session(self):
        """Inizia una nuova sessione di log"""
        self.current_session_logs = []
        
    def get_session_logs(self) -> List[str]:
        """Ritorna i log della sessione corrente"""
        return self.current_session_logs
    
    def get_session_logs_str(self) -> str:
        """Ritorna i log della sessione corrente come stringa formattata"""
        return "\n".join(self.current_session_logs)

# Istanza globale
log_capture = LogCapture()
