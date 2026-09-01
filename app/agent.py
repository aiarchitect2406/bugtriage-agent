from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig, ContextCacheConfig
from app.workflow import bug_triage_workflow
from app.constitution import SYSTEM_CONSTITUTION
from app.app_utils.context_utils import compact_session_history

# Primary Root Agent configured with ADK 2.0 Graph-Based Workflow
bug_triage_workflow.description = (
    f"Autonomous Bug Triage & Peer Review Workflow governed by Enterprise Constitution.\n\n{SYSTEM_CONSTITUTION}"
)
root_agent = bug_triage_workflow

# ADK App Export with Context History Compaction & Server-Side Context Caching
app = App(
    root_agent=root_agent,
    name="app",
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=5,
        overlap_size=1,
        token_threshold=32000,
        event_retention_size=5,
    ),
    context_cache_config=ContextCacheConfig(
        min_tokens=2048,
        ttl_seconds=1800,
    ),
)

__all__ = [
    "root_agent",
    "bug_triage_workflow",
    "app",
    "SYSTEM_CONSTITUTION",
    "compact_session_history",
]

