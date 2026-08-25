"""Dedupe Agent for ADK 2.0 Bug Triage System."""

from typing import Dict, Any, List, Optional
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from app.config import Config
from app.tools.vector_tools import query_similar_bugs_by_vector
from app.models.bug_report import SanitizedBugReport
from app.observability.logger import StructuredLogger
from app.observability.tracing import execute_tool_with_observability

DEDUPE_AGENT_CONSTITUTION = """
You are the Dedupe Agent for the Bug Triage System.
Core Responsibilities:
1. Query vector database using semantic embeddings of crash reports and stack traces.
2. Apply cosine similarity cutoff (threshold >= 0.85) to identify semantically identical bugs.
3. Link duplicate reports to master parent tickets to eliminate alert fatigue.
"""

dedupe_agent = Agent(
    name="dedupe_agent",
    model=Gemini(
        model=Config.FAST_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=DEDUPE_AGENT_CONSTITUTION.strip(),
    tools=[query_similar_bugs_by_vector],
)

class DedupeAgentRunner:
    """Wrapper runner executing Dedupe tasks with full OpenTelemetry and Cloud Logging observability."""
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger("DedupeAgent")
        self.agent = dedupe_agent

    def check_duplicate(
        self, 
        sanitized_report: SanitizedBugReport, 
        historical_candidates: Optional[List[Dict[str, Any]]] = None,
        request_id: str = "req-001"
    ) -> Dict[str, Any]:
        """Performs vector search to check if bug report is duplicate."""
        return execute_tool_with_observability(
            agent_name="DedupeAgent",
            tool_name="query_similar_bugs_by_vector",
            tool_fn=lambda args: query_similar_bugs_by_vector(**args),
            args={
                "issue_id": sanitized_report.issue_id,
                "bug_title": sanitized_report.title,
                "bug_description": f"{sanitized_report.cleaned_description} {sanitized_report.sanitized_logs}",
                "candidate_historical_bugs": historical_candidates,
            },
            request_id=request_id,
            logger=self.logger,
        )
