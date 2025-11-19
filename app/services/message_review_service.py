"""
Service to store and retrieve human reviews/notes for AI messages.
"""
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from app.database import get_db
from app.models.database_models import MessageNoteModel, MessageModel
from loguru import logger


class MessageReviewService:
    """Service for message notes (ratings/comments)

    Methods:
    - create_note
    - get_notes_for_message
    - get_notes_for_session
    - get_note
    """

    @staticmethod
    async def create_note(message_id: int, rating: int, note: Optional[str] = None, created_by: Optional[str] = None) -> Optional[MessageNoteModel]:
        async for db in get_db():
            try:
                # Verify message exists
                message = await db.get(MessageModel, message_id)
                if not message:
                    return None

                msg_note = MessageNoteModel(
                    message_id=message_id,
                    session_id=message.session_id,
                    rating=int(rating) if rating is not None else 0,
                    note=note,
                    created_by=created_by
                )
                db.add(msg_note)
                await db.commit()
                await db.refresh(msg_note)
                return msg_note
            except Exception as e:
                logger.error(f"Errore nella creatione della note per il message {message_id}: {e}")
                return None

    @staticmethod
    async def get_notes_for_message(message_id: int) -> List[MessageNoteModel]:
        async for db in get_db():
            try:
                result = await db.execute(select(MessageNoteModel).where(MessageNoteModel.message_id == message_id).order_by(MessageNoteModel.created_at.desc()))
                return result.scalars().all()
            except Exception as e:
                logger.error(f"Errore nel recupero delle notes per message {message_id}: {e}")
                return []

    @staticmethod
    async def get_notes_for_session(session_id: int) -> List[MessageNoteModel]:
        async for db in get_db():
            try:
                result = await db.execute(select(MessageNoteModel).where(MessageNoteModel.session_id == session_id).order_by(MessageNoteModel.created_at.desc()))
                return result.scalars().all()
            except Exception as e:
                logger.error(f"Errore nel recupero delle notes per session {session_id}: {e}")
                return []

    @staticmethod
    async def get_note(note_id: int) -> Optional[MessageNoteModel]:
        async for db in get_db():
            try:
                result = await db.execute(select(MessageNoteModel).where(MessageNoteModel.id == note_id))
                return result.scalar_one_or_none()
            except Exception as e:
                logger.error(f"Errore nel recupero della message note {note_id}: {e}")
                return None
