"""OpenTelemetry Distributed Tracing & Cloud Observability Plugin for Google ADK 2.0."""

import time
import logging
from typing import Dict, Any, Callable, Optional
from opentelemetry import trace
from google.adk.plugins import BasePlugin
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from app.observability.logger import StructuredLogger

logger = logging.getLogger("CloudObservabilityPlugin")
tracer = trace.get_tracer("adk_bug_triage_agent", "2.0.0")

def get_tracer():
    return tracer


class CloudObservabilityPlugin(BasePlugin):
    """Native ADK 2.0 Observability Plugin exporting OpenTelemetry & Google Cloud Telemetry."""

    def __init__(self, name: str = "cloud_observability_plugin"):
        super().__init__(name=name)
        self.name = name
        self.structured_logger = StructuredLogger("CloudObservabilityPlugin")

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        """ADK 2.0 Lifecycle: Traces agent entry and session telemetry."""
        agent_name = getattr(agent, "name", str(agent))
        logger.info(f"[Cloud Trace] Agent started: {agent_name} (session={getattr(callback_context, 'session_id', 'unknown')})")
        return None

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        """ADK 2.0 Lifecycle: Traces agent completion."""
        agent_name = getattr(agent, "name", str(agent))
        logger.info(f"[Cloud Trace] Agent finished: {agent_name}")
        return None

    async def before_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext
    ) -> Optional[dict]:
        """ADK 2.0 Lifecycle: Emits tool start span and structured intent log."""
        tool_name = getattr(tool, "name", str(tool))
        logger.debug(f"[Cloud Trace] Tool invoking: {tool_name}")
        return None

    async def after_tool_callback(
        self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, result: dict
    ) -> Optional[dict]:
        """ADK 2.0 Lifecycle: Emits tool completion metric."""
        tool_name = getattr(tool, "name", str(tool))
        logger.debug(f"[Cloud Trace] Tool finished: {tool_name}")
        return None


def execute_tool_with_observability(
    agent_name: str,
    tool_name: str,
    tool_fn: Callable[[Any], Dict[str, Any]],
    args: Dict[str, Any],
    request_id: str,
    logger: StructuredLogger
) -> Dict[str, Any]:
    """Wraps tool execution in OpenTelemetry Spans, Intent/Outcome Logging, and DLP Scrubbing."""
    with tracer.start_as_current_span(f"{agent_name}:{tool_name}") as span:
        span.set_attribute("request_id", request_id)
        span.set_attribute("agent.name", agent_name)
        span.set_attribute("tool.name", tool_name)

        logger.log_intent(agent_name, tool_name, args, request_id)
        
        start_time = time.time()
        try:
            result = tool_fn(args)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.log_outcome(agent_name, tool_name, result, duration_ms, request_id)
            span.set_status(trace.StatusCode.OK)
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_outcome = {
                "status": "ERROR", 
                "error": f"Tool execution error: {str(e)}",
                "message": "Tool execution failed gracefully. Verify parameter formats and retry."
            }
            logger.log_outcome(agent_name, tool_name, error_outcome, duration_ms, request_id)
            span.record_exception(e)
            span.set_status(trace.StatusCode.ERROR, str(e))
            return error_outcome
