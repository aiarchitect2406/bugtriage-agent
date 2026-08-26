"""ADK 2.0 Agent Application Entrypoint."""

from google.adk.apps import App
from app.workflow import bug_triage_workflow

# Primary Root Agent configured with ADK 2.0 Graph-Based Workflow
root_agent = bug_triage_workflow

# ADK App Export (name must match package name 'app')
app = App(
    root_agent=root_agent,
    name="app",
)

__all__ = [
    "root_agent",
    "bug_triage_workflow",
    "app",
]

