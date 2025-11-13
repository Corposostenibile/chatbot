"""
Servizio per la gestione dei system prompts nel database
"""
from typing import List, Optional
from sqlalchemy import select
from loguru import logger

from app.database import get_db
from app.models.database_models import SystemPromptModel


class SystemPromptService:
    """Servizio per gestire i system prompts"""

    @staticmethod
    async def get_active_prompt() -> Optional[str]:
        """Ottiene il prompt di sistema attivo"""
        async for db in get_db():
            try:
                result = await db.execute(
                    select(SystemPromptModel).where(SystemPromptModel.is_active == True)
                )
                prompt = result.scalar_one_or_none()
                return prompt.content if prompt else None
            except Exception as e:
                logger.error(f"Errore nel recupero del prompt attivo: {e}")
                return None

    @staticmethod
    async def get_all_prompts() -> List[SystemPromptModel]:
        """Ottiene tutti i system prompts"""
        async for db in get_db():
            try:
                result = await db.execute(
                    select(SystemPromptModel).order_by(SystemPromptModel.created_at.desc())
                )
                return result.scalars().all()
            except Exception as e:
                logger.error(f"Errore nel recupero dei prompts: {e}")
                return []

    @staticmethod
    async def create_prompt(name: str, content: str, version: str = "1.0", description: Optional[str] = None) -> Optional[SystemPromptModel]:
        """Crea un nuovo system prompt"""
        async for db in get_db():
            try:
                # Disattiva tutti i prompt esistenti se questo è il primo o se specificato
                new_prompt = SystemPromptModel(
                    name=name,
                    content=content,
                    version=version,
                    description=description,
                    is_active=False  # Di default non attivo
                )
                db.add(new_prompt)
                await db.commit()
                await db.refresh(new_prompt)
                logger.info(f"Prompt creato: {name}")
                return new_prompt
            except Exception as e:
                logger.error(f"Errore nella creazione del prompt: {e}")
                return None

    @staticmethod
    async def update_prompt(prompt_id: int, name: Optional[str] = None, content: Optional[str] = None,
                           version: Optional[str] = None, description: Optional[str] = None) -> bool:
        """Aggiorna un system prompt esistente"""
        async for db in get_db():
            try:
                result = await db.execute(
                    select(SystemPromptModel).where(SystemPromptModel.id == prompt_id)
                )
                prompt = result.scalar_one_or_none()
                if not prompt:
                    return False

                if name is not None:
                    prompt.name = name
                if content is not None:
                    prompt.content = content
                if version is not None:
                    prompt.version = version
                if description is not None:
                    prompt.description = description

                await db.commit()
                logger.info(f"Prompt aggiornato: {prompt_id}")
                return True
            except Exception as e:
                logger.error(f"Errore nell'aggiornamento del prompt: {e}")
                return False

    @staticmethod
    async def set_active_prompt(prompt_id: int) -> bool:
        """Imposta un prompt come attivo (disattivando tutti gli altri)"""
        async for db in get_db():
            try:
                # Disattiva tutti i prompt
                await db.execute(
                    SystemPromptModel.__table__.update().values(is_active=False)
                )

                # Attiva il prompt selezionato
                result = await db.execute(
                    select(SystemPromptModel).where(SystemPromptModel.id == prompt_id)
                )
                prompt = result.scalar_one_or_none()
                if not prompt:
                    return False

                prompt.is_active = True
                await db.commit()
                logger.info(f"Prompt attivo impostato: {prompt_id}")
                return True
            except Exception as e:
                logger.error(f"Errore nell'impostazione del prompt attivo: {e}")
                return False

    @staticmethod
    async def delete_prompt(prompt_id: int) -> bool:
        """Elimina un system prompt"""
        async for db in get_db():
            try:
                result = await db.execute(
                    select(SystemPromptModel).where(SystemPromptModel.id == prompt_id)
                )
                prompt = result.scalar_one_or_none()
                if not prompt:
                    return False

                await db.delete(prompt)
                await db.commit()
                logger.info(f"Prompt eliminato: {prompt_id}")
                return True
            except Exception as e:
                logger.error(f"Errore nell'eliminazione del prompt: {e}")
                return False

    @staticmethod
    async def initialize_default_prompt() -> None:
        """Inizializza il prompt di default se non esiste"""
        async for db in get_db():
            try:
                # Verifica se esiste già un prompt attivo
                result = await db.execute(
                    select(SystemPromptModel).where(SystemPromptModel.is_active == True)
                )
                existing_active = result.scalar_one_or_none()

                if existing_active:
                    logger.info("Prompt attivo già esistente")
                    return

                # Verifica se esiste già un prompt con questo nome
                result = await db.execute(
                    select(SystemPromptModel).where(SystemPromptModel.name == "default")
                )
                existing_default = result.scalar_one_or_none()

                if existing_default:
                    # Attiva quello esistente
                    existing_default.is_active = True
                    await db.commit()
                    logger.info("Prompt default esistente attivato")
                    return
                else:
                    logger.error("Prompt default non trovato, errore.")
            except Exception as e:
                logger.error(f"Errore nell'inizializzazione del prompt di default: {e}")