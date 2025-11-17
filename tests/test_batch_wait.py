import asyncio
from datetime import datetime
import pytest

from app.services.unified_agent import UnifiedAgent
from app.models.database_models import SessionModel

pytestmark = pytest.mark.asyncio

async def test_batch_wait_basic(db_session):
    agent = UnifiedAgent()
    async for db in db_session():
        # Create session
        s = SessionModel(session_id='test-batch-1')
        db.add(s)
        await db.commit()
        await db.refresh(s)

        # First call should set batch and not call AI immediately
        # We'll simulate by calling agent.chat and cancel after short wait
        task = asyncio.create_task(agent.chat('test-batch-1', 'First message'))
        await asyncio.sleep(0.1)
        # there should be session waiting flag set
        s = await db.get(SessionModel, s.id)
        assert s.is_batch_waiting

        # Send a second message while waiting
        resp2 = await agent.chat('test-batch-1', 'Second message')
        assert resp2.messages == []

        # Cancel first, cleanup
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
*** End Patch