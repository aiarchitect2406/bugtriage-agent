"""Ingestion Agent for ADK 2.0 Bug Triage System."""

from typing import Dict, Any, Optional
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from app.config import Config
from app.tools.sanitize_tools import sanitize_logs_and_extract_stack
from app.models.bug_report import BugReport
from app.observability.logger import StructuredLogger
from app.observability.tracing import execute_tool_with_observability

INGESTION_AGENT_CONSTITUTION = """
You are the Ingestion Agent for the Bug Triage System.
Core Responsibilities:
1. Parse incoming raw bug reports, error logs, and stack traces.
2. Redact sensitive credentials, passwords, tokens, emails, IPs, and PII.
3. Extract structured exception stack frames (file_path, line_number, function_name).
4. Identify exception class and return sanitized bug report.
"""

ingestion_agent = Agent(
    name="ingestion_agent",
    model=Gemini(
        model=Config.FAST_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=INGESTION_AGENT_CONSTITUTION.strip(),
    tools=[sanitize_logs_and_extract_stack],
)

class IngestionAgentRunner:
    """Wrapper runner executing Ingestion tasks with full OpenTelemetry and Cloud Logging observability."""
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger("IngestionAgent")
        self.agent = ingestion_agent

    def process_raw_report(self, bug_report: BugReport, request_id: str = "req-001") -> Dict[str, Any]:
        """Sanitizes incoming report logs and parses stack frames with observability."""
        return execute_tool_with_observability(
            agent_name="IngestionAgent",
            tool_name="sanitize_logs_and_extract_stack",
            tool_fn=lambda args: sanitize_logs_and_extract_stack(**args),
            args={
                "issue_id": bug_report.issue_id,
                "title": bug_report.title,
                "description": bug_report.description,
                "raw_logs": bug_report.raw_logs,
                "stack_trace": bug_report.stack_trace,
                "source_system": bug_report.source_system,
                "metadata": bug_report.metadata,
            },
            request_id=request_id,
            logger=self.logger,
        )
