"""
Configurazione dell'applicazione
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurazione dell'applicazione"""
    
    # Configurazione app
    app_name: str = "Chatbot API"
    app_version: str = "0.1.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Configurazione server
    host: str = "0.0.0.0"
    port: int = 8081
    
    # Configurazione sicurezza
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Google Cloud
    google_cloud_project: str = ""
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_ai_api_key: Optional[str] = None
    
    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/chatbot"
    
    model_config = {"env_file": ".env"}


# Istanza globale delle impostazioni
settings = Settings()


def get_settings() -> Settings:
    """Dependency per ottenere le impostazioni"""
    return settings