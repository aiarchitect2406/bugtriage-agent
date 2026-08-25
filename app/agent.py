"""ADK 2.0 Agent Application Entrypoint."""

from google.adk.apps import App
from app.agents.coordinator import coordinator_agent, TriageCoordinator
from app.workflow import bug_triage_workflow
from app.plugins.guardrails import GuardrailPolicyPlugin

# Primary Root Agent configured with ADK 2.0
root_agent = coordinator_agent

# ADK App Export (name must match directory name 'app')
app = App(
    root_agent=root_agent,
    name="app",
    plugins=[GuardrailPolicyPlugin()],
)

__all__ = [
    "root_agent",
    "coordinator_agent",
    "bug_triage_workflow",
    "TriageCoordinator",
    "app",
]
