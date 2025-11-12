"""
Modelli del database per sessioni e conversazioni
"""
from datetime import datetime
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    messages: Mapped[List["MessageModel"]] = relationship("MessageModel", back_populates="session", order_by="MessageModel.timestamp")


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # "user" or "assistant"
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)