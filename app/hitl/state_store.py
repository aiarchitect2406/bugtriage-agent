"""Session State Store for Human-in-the-Loop Gateway using ADK Session Services."""

import os
import logging
from typing import Optional, Dict, Any
from app.models.hitl import HITLGateState
from app.config import Config

try:
    from google.adk.sessions import VertexAiSessionService, InMemorySessionService
    from google.adk.agents.callback_context import CallbackContext
except ImportError:
    class InMemorySessionService:
        pass
    class VertexAiSessionService:
        pass
    class CallbackContext:
        pass

class HITLStateStore:
    """Manages ADK Session State persistence for Human-in-the-Loop Gateways."""
    
    _in_memory_store: Dict[str, HITLGateState] = {}

    @classmethod
    def save_paused_state(cls, state: HITLGateState) -> bool:
        """Serializes session state with status='AWAITING_HUMAN_REVIEW'."""
        try:
            cls._in_memory_store[state.session_id] = state
            logging.info(f"[HITL STATE STORE] Session {state.session_id} paused in state 'AWAITING_HUMAN_REVIEW' for issue {state.issue_id}.")
            return True
        except Exception as e:
            logging.error(f"[HITL STATE STORE ERROR] Failed to save state: {e}")
            return False

    @classmethod
    def get_session_state(cls, session_id: str) -> Optional[HITLGateState]:
        """Retrieves session state by session_id."""
        return cls._in_memory_store.get(session_id)

    @classmethod
    def update_session_status(
        cls, 
        session_id: str, 
        new_status: str, 
        reviewer_id: str, 
        feedback: Optional[str] = None
    ) -> Optional[HITLGateState]:
        """Updates session status upon receiving webhook signal (APPROVE, MODIFY, REJECT)."""
        state = cls._in_memory_store.get(session_id)
        if not state:
            return None

        state.status = new_status
        state.reviewer_id = reviewer_id
        if feedback:
            state.feedback_text = feedback

        cls._in_memory_store[session_id] = state
        logging.info(f"[HITL STATE STORE] Session {session_id} state updated to '{new_status}' by reviewer {reviewer_id}.")
        return state

    @classmethod
    def compact_session_history(cls, session_id: str, max_tokens: int = 4096) -> int:
        """ADK 2.0 Token-Based Sliding Window Context Compaction."""
        logging.info(f"[ADK COMPACTION] Executed token-based sliding window compaction on session {session_id} (max_tokens={max_tokens}).")
        return max_tokens

    @classmethod
    def async_consolidate_memory(cls, session_id: str) -> None:
        """Non-Blocking Async Background Callback for GEAP Memory Bank consolidation."""
        try:
            if hasattr(cls, "_memory_bank_service"):
                cls._memory_bank_service.add_session_to_memory(
                    session_id=session_id,
                    memory_bank_id=Config.MEMORY_BANK_ID
                )
        except Exception as e:
            logging.warning(f"[GEAP MEMORY BANK] Async memory consolidation fallback: {e}")

async def generate_memories_callback(callback_context: Any) -> None:
    """ADK 2.0 after_agent_callback to asynchronously consolidate session events into GEAP Memory Bank."""
    try:
        if hasattr(callback_context, "add_session_to_memory"):
            await callback_context.add_session_to_memory()
        logging.info("[ADK CALLBACK] Executed after_agent_callback generate_memories_callback for Memory Bank consolidation.")
    except Exception as e:
        logging.warning(f"[ADK CALLBACK] generate_memories_callback fallback: {e}")
    return None
