"""OpenTelemetry Distributed Tracing Wrapper for ADK Tools and Agents."""

import time
from typing import Dict, Any, Callable
from opentelemetry import trace
from app.observability.logger import StructuredLogger

tracer = trace.get_tracer("adk_bug_triage_agent", "2.0.0")

def get_tracer():
    return tracer

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
