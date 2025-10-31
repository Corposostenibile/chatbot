"""
Test per l'applicazione principale
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test dell'endpoint root"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_health_check():
    """Test dell'health check"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


def test_status_endpoint():
    """Test dell'endpoint di stato"""
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "app_name" in data
    assert "version" in data


def test_chat_endpoint():
    """Test dell'endpoint chat"""
    message_data = {
        "message": "Ciao",
        "user_id": "test_user"
    }
    
    response = client.post("/chat", json=message_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "response" in data
    assert "user_id" in data
    assert "timestamp" in data
    assert data["user_id"] == "test_user"


def test_chat_endpoint_with_help():
    """Test dell'endpoint chat con richiesta di aiuto"""
    message_data = {
        "message": "aiuto",
        "user_id": "test_user"
    }
    
    response = client.post("/chat", json=message_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "chatbot di esempio" in data["response"].lower()


def test_chat_endpoint_invalid_data():
    """Test dell'endpoint chat con dati invalidi"""
    response = client.post("/chat", json={})
    assert response.status_code == 422  # Validation error