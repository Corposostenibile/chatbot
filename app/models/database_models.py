"""
Modelli del database per sessioni e conversazioni
"""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.lifecycle import LifecycleStage


class SessionModel(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    current_lifecycle: Mapped[LifecycleStage] = mapped_column(SQLEnum(LifecycleStage), default=LifecycleStage.NUOVA_LEAD)
    user_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    is_conversation_finished: Mapped[bool] = mapped_column(default=False)  # Flag per conversazione finita
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    # Flag per batch aggregation: se True, l'agente sta attendendo nuovi messaggi prima di chiamare l'AI
    is_batch_waiting: Mapped[bool] = mapped_column(default=False)
    batch_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    messages: Mapped[List["MessageModel"]] = relationship("MessageModel", back_populates="session", order_by="MessageModel.timestamp")


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # "user" or "assistant"
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship
    session: Mapped["SessionModel"] = relationship("SessionModel", back_populates="messages")


class SystemPromptModel(Base):
    __tablename__ = "system_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)  # Nome identificativo del prompt
    content: Mapped[str] = mapped_column(Text)  # Contenuto del prompt
    is_active: Mapped[bool] = mapped_column(default=True)  # Se è il prompt attivo
    version: Mapped[str] = mapped_column(String, default="1.0")  # Versione del prompt
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Descrizione del prompt
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AIModelModel(Base):
    __tablename__ = "ai_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)  # Nome del modello (es. gemini-flash-latest)
    display_name: Mapped[str] = mapped_column(String)  # Nome visualizzato nell'UI
    is_active: Mapped[bool] = mapped_column(default=False)  # Se è il modello attivo
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Descrizione del modello
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class HumanTaskModel(Base):
    __tablename__ = "human_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sessions.id"), nullable=True)
    title: Mapped[str] = mapped_column(String)  # breve descrizione
    description: Mapped[str] = mapped_column(Text)  # dettagli della task
    status: Mapped[str] = mapped_column(String, default="open")  # open|in_progress|closed
    assigned_to: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string con dettagli vari
    completed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
    session: Mapped[Optional["SessionModel"]] = relationship("SessionModel")