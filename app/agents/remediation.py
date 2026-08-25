"""Code Remediation Agent for ADK 2.0 Bug Triage System."""

from typing import Dict, Any, Optional
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from app.config import Config
from app.tools.sandbox_tools import execute_reproduction_and_sandbox_fix
from app.models.bug_report import SanitizedBugReport, EnrichmentContext
from app.observability.logger import StructuredLogger
from app.observability.tracing import execute_tool_with_observability

REMEDIATION_AGENT_CONSTITUTION = """
You are the Code Remediation Agent driven by Gemini 3.1 Pro.
Core Responsibilities:
1. Perform deep reasoning on exception stack traces and source codebase.
2. Synthesize a standalone, self-contained failing unit test (pytest) that reproduces the issue.
3. Generate a root-cause unified diff patch fixing the defect.
4. Run local test suite in containerized sandbox to verify tests pass post-patch before submitting to review gate.
"""

remediation_agent = Agent(
    name="remediation_agent",
    model=Gemini(
        model=Config.REASONING_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=REMEDIATION_AGENT_CONSTITUTION.strip(),
    tools=[execute_reproduction_and_sandbox_fix],
)

class CodeRemediationAgentRunner:
    """Wrapper runner executing Code Remediation with full OpenTelemetry and Cloud Logging observability."""
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        self.logger = logger or StructuredLogger("CodeRemediationAgent")
        self.agent = remediation_agent

    def generate_remediation_and_sandbox_fix(
        self,
        sanitized_report: SanitizedBugReport,
        enrichment_context: EnrichmentContext,
        request_id: str = "req-001"
    ) -> Dict[str, Any]:
        """Synthesizes reproduction test and unified diff, running sandbox validation with observability."""
        primary_file = enrichment_context.affected_files[0] if enrichment_context.affected_files else "app/services/payment_checkout.py"
        
        return execute_tool_with_observability(
            agent_name="CodeRemediationAgent",
            tool_name="execute_reproduction_and_sandbox_fix",
            tool_fn=lambda args: execute_reproduction_and_sandbox_fix(**args),
            args={
                "issue_id": sanitized_report.issue_id,
                "stack_trace": sanitized_report.sanitized_logs,
                "source_file_path": primary_file,
                "existing_source_code": None,
            },
            request_id=request_id,
            logger=self.logger,
        )
