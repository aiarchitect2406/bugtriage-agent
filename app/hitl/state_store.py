"""Session State Store for Human-in-the-Loop Gateway using ADK Session Services."""

import os
import logging
from typing import Optional, Dict, Any
from app.models.hitl import HITLGateState
from app.config import Config
from app.app_utils.services import get_session_service

logger = logging.getLogger("HITLStateStore")


class HITLStateStore:
    """Manages ADK Session State persistence for Human-in-the-Loop Gateways."""

    @classmethod
    def get_session_service(cls):
        """Returns the process-wide ADK SessionService (VertexAiSessionService or DatabaseSessionService)."""
        return get_session_service()

    @classmethod
    def async_consolidate_memory(cls, session_id: str) -> None:
        """Non-blocking async background callback for GEAP Memory Bank consolidation."""
        try:
            session_svc = cls.get_session_service()
            if hasattr(session_svc, "add_session_to_memory"):
                session_svc.add_session_to_memory(
                    session_id=session_id,
                    memory_bank_id=Config.MEMORY_BANK_ID
                )
        except Exception as e:
            logger.warning(f"[GEAP MEMORY BANK] Memory consolidation: {e}")


async def generate_memories_callback(callback_context: Any) -> None:
    """ADK 2.0 after_agent_callback to asynchronously consolidate session events into GEAP Memory Bank."""
    try:
        if hasattr(callback_context, "add_session_to_memory"):
            await callback_context.add_session_to_memory()
            logger.info("[ADK CALLBACK] Consolidated session into GEAP Memory Bank.")
    except Exception as e:
        logger.warning(f"[ADK CALLBACK] generate_memories_callback: {e}")
    return None

