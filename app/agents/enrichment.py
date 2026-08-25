"""Enrichment Agent for ADK 2.0 Bug Triage System."""

from typing import Dict, Any, Optional
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from app.config import Config
from app.tools.ownership_tools import resolve_codeowners_and_blame
from app.models.bug_report import SanitizedBugReport
from app.observability.logger import StructuredLogger
from app.observability.tracing import execute_tool_with_observability

ENRICHMENT_AGENT_CONSTITUTION = """
You are the Enrichment Agent for the Bug Triage System.
Core Responsibilities:
1. Parse affected file paths from stack frames.
2. Match file paths against .github/CODEOWNERS rules and execute git blame on failing lines.
3. Determine technical severity, business priority, and target SLA resolution hours.
"""

enrichment_agent = Agent(
    name="enrichment_agent",
    model=Gemini(
        model=Config.FAST_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=ENRICHMENT_AGENT_CONSTITUTION.strip(),
    tools=[resolve_codeowners_and_blame],
)

class EnrichmentAgentRunner:
    """Wrapper runner executing Context Enrichment with full OpenTelemetry and Cloud Logging observability."""
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger("EnrichmentAgent")
        self.agent = enrichment_agent

    def enrich_bug_context(
        self, 
        sanitized_report: SanitizedBugReport, 
        severity_hint: Optional[str] = "Major",
        request_id: str = "req-001"
    ) -> Dict[str, Any]:
        """Resolves CODEOWNERS, git blame authors, and SLA priority assignments."""
        stack_frame_dicts = [f.model_dump() for f in sanitized_report.stack_frames]
        
        return execute_tool_with_observability(
            agent_name="EnrichmentAgent",
            tool_name="resolve_codeowners_and_blame",
            tool_fn=lambda args: resolve_codeowners_and_blame(**args),
            args={
                "issue_id": sanitized_report.issue_id,
                "stack_frames": stack_frame_dicts,
                "severity_input": severity_hint,
            },
            request_id=request_id,
            logger=self.logger,
        )
