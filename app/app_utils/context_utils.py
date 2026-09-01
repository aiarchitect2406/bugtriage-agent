"""Context bloat management and token-based history compaction utilities."""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def estimate_tokens(text: str) -> int:
    """Rough estimation of tokens based on 4 characters per token."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def compact_session_history(
    session_id: str,
    max_tokens: int = 4096,
    events: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Applies token-based sliding window compaction to session history.

    Prunes older conversational turns and events to remain within max_tokens
    budget while preserving the root directive, initial state, and recent turns.

    Args:
        session_id: The active session identifier.
        max_tokens: Maximum token budget for the retained context window.
        events: Optional list of events/messages to compact.

    Returns:
        Dict[str, Any]: Structured outcome containing compacted event count,
            estimated token usage, and status.
    """
    event_list = list(events) if events else []
    total_tokens = sum(estimate_tokens(str(getattr(e, "content", e))) for e in event_list)

    if total_tokens <= max_tokens:
        return {
            "session_id": session_id,
            "status": "NOOP",
            "original_count": len(event_list),
            "compacted_count": len(event_list),
            "pruned_count": 0,
            "estimated_tokens": total_tokens,
            "max_tokens": max_tokens,
            "compacted_events": event_list,
        }

    # Sliding window compaction: retain initial event (prompt/context) and latest events
    if len(event_list) <= 2:
        return {
            "session_id": session_id,
            "status": "BOUNDED",
            "original_count": len(event_list),
            "compacted_count": len(event_list),
            "pruned_count": 0,
            "estimated_tokens": total_tokens,
            "max_tokens": max_tokens,
            "compacted_events": event_list,
        }

    first_event = event_list[0]
    remaining = event_list[1:]
    compacted = [first_event]

    current_tokens = estimate_tokens(str(getattr(first_event, "content", first_event)))

    # Take most recent events from the end while under budget
    retained_tail = []
    for e in reversed(remaining):
        cost = estimate_tokens(str(getattr(e, "content", e)))
        if current_tokens + cost <= max_tokens:
            retained_tail.insert(0, e)
            current_tokens += cost
        else:
            break

    compacted.extend(retained_tail)
    pruned_count = len(event_list) - len(compacted)

    logger.info(
        f"Compacted session {session_id}: pruned {pruned_count} events, "
        f"retained {len(compacted)} events ({current_tokens} tokens / {max_tokens} max)."
    )

    return {
        "session_id": session_id,
        "status": "COMPACTED",
        "original_count": len(event_list),
        "compacted_count": len(compacted),
        "pruned_count": pruned_count,
        "estimated_tokens": current_tokens,
        "max_tokens": max_tokens,
        "compacted_events": compacted,
    }
