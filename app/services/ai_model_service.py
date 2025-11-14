"""
Servizio per la gestione dei modelli AI nel database
"""
from typing import List, Optional
from sqlalchemy import select
from loguru import logger

from app.database import get_db_session
from app.models.database_models import AIModelModel


class AIModelService:
    """Servizio per gestire i modelli AI"""

    @staticmethod
    async def get_all_models() -> List[AIModelModel]:
        """Ottiene tutti i modelli AI disponibili"""
        db = await get_db_session()
        try:
            result = await db.execute(
                select(AIModelModel).order_by(AIModelModel.created_at)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Errore nel recupero dei modelli: {e}")
            return []
        finally:
            await db.close()

    @staticmethod
    async def get_model_by_name(name: str) -> Optional[AIModelModel]:
        """Ottiene un modello per nome"""
        db = await get_db_session()
        try:
            result = await db.execute(
                select(AIModelModel).where(AIModelModel.name == name)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Errore nel recupero del modello {name}: {e}")
            return None
        finally:
            await db.close()

    @staticmethod
    async def get_active_model() -> Optional[AIModelModel]:
        """Ottiene il modello AI attivo"""
        db = await get_db_session()
        try:
            result = await db.execute(
                select(AIModelModel).where(AIModelModel.is_active == True)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Errore nel recupero del modello attivo: {e}")
            return None
        finally:
            await db.close()

    @staticmethod
    async def create_model(name: str, display_name: str, description: Optional[str] = None, is_active: bool = False) -> Optional[AIModelModel]:
        """Crea un nuovo modello AI"""
        db = await get_db_session()
        try:
            new_model = AIModelModel(
                name=name,
                display_name=display_name,
                description=description,
                is_active=is_active
            )
            db.add(new_model)
            await db.commit()
            await db.refresh(new_model)
            logger.info(f"Creato modello AI: {name}")
            return new_model
        except Exception as e:
            await db.rollback()
            logger.error(f"Errore nella creazione del modello {name}: {e}")
            return None
        finally:
            await db.close()

    @staticmethod
    async def set_active_model(model_id: int) -> bool:
        """Imposta un modello come attivo (disattiva gli altri)"""
        db = await get_db_session()
        try:
            # Disattiva tutti i modelli
            await db.execute(
                select(AIModelModel).where(AIModelModel.is_active == True)
            )
            all_models = (await db.execute(select(AIModelModel))).scalars().all()
            for model in all_models:
                model.is_active = False
            
            # Attiva il modello specificato
            result = await db.execute(
                select(AIModelModel).where(AIModelModel.id == model_id)
            )
            model = result.scalar_one_or_none()
            if model:
                model.is_active = True
                await db.commit()
                logger.info(f"Modello attivo impostato: {model.name}")
                return True
            
            await db.rollback()
            return False
        except Exception as e:
            await db.rollback()
            logger.error(f"Errore nell'impostazione del modello attivo: {e}")
            return False
        finally:
            await db.close()

    @staticmethod
    async def initialize_default_models() -> None:
        """Inizializza i modelli di default nel database"""
        existing = await AIModelService.get_all_models()
        
        if existing:
            logger.info("Modelli AI già inizializzati nel database")
            return
        
        # Crea i modelli di default
        default_models = [
            {
                "name": "gemini-flash-latest",
                "display_name": "Gemini Flash Latest",
                "description": "Modello Gemini Flash più recente, veloce e ottimizzato",
                "is_active": True
            },
            {
                "name": "gemini-2.5-pro",
                "display_name": "Gemini 2.5 Pro",
                "description": "Modello Gemini 2.5 Pro, più avanzato e preciso",
                "is_active": False
            }
        ]
        
        for model_data in default_models:
            await AIModelService.create_model(**model_data)
        
        logger.info("Modelli AI di default inizializzati")
