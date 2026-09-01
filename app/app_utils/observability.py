"""Production Observability, Structured JSON Logging, and OpenTelemetry Tracing."""

import json
import logging
import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import Status, StatusCode

    # Initialize Global Tracer Provider if not set
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        trace.set_tracer_provider(TracerProvider())
    TRACER = trace.get_tracer("adk-bugtriage", "2.0.0")
    HAS_OTEL = True
except Exception:
    HAS_OTEL = False
    TRACER = None


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records into structured JSON payloads with rich metadata."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": f"{record.filename}:{record.lineno}",
        }
        if hasattr(record, "phase"):
            log_payload["phase"] = record.phase
        if hasattr(record, "node"):
            log_payload["node"] = record.node
        if hasattr(record, "issue_id"):
            log_payload["issue_id"] = record.issue_id
        if hasattr(record, "extra_data"):
            log_payload["metadata"] = record.extra_data

        return json.dumps(log_payload)


def configure_structured_logging(logger: logging.Logger):
    """Attaches the StructuredJsonFormatter to the given logger if not already attached."""
    if not any(isinstance(h.formatter, StructuredJsonFormatter) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False


def log_intent(
    logger: logging.Logger,
    node: str,
    action: str,
    issue_id: Optional[str] = None,
    **kwargs
) -> None:
    """Explicitly records the agent's INTENDED action before execution (Criterion 14)."""
    extra = {
        "phase": "INTENT",
        "node": node,
        "issue_id": issue_id or "UNKNOWN",
        "extra_data": kwargs,
    }
    logger.info(f"[INTENT] Node {node}: Starting {action} for {issue_id or request}", extra=extra)


def log_outcome(
    logger: logging.Logger,
    node: str,
    action: str,
    status: str,
    issue_id: Optional[str] = None,
    **kwargs
) -> None:
    """Explicitly records the ACTUAL OUTCOME after execution (Criterion 14)."""
    extra = {
        "phase": "OUTCOME",
        "node": node,
        "issue_id": issue_id or "UNKNOWN",
        "extra_data": {"status": status, **kwargs},
    }
    logger.info(f"[OUTCOME] Node {node}: Completed {action} [status={status}] for {issue_id or request}", extra=extra)


@contextmanager
def trace_span(span_name: str, attributes: Optional[Dict[str, Any]] = None):
    """OpenTelemetry context manager creating distributed tracing spans (Criterion 15)."""
    if HAS_OTEL and TRACER:
        with TRACER.start_as_current_span(span_name) as span:
            if attributes:
                for k, v in attributes.items():
                    if v is not None:
                        span.set_attribute(k, str(v) if not isinstance(v, (int, float, bool)) else v)
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.record_exception(exc)
                raise
    else:
        yield None
