"""Structured JSON Logger for Cloud Logging capturing INTENT and OUTCOME states."""

import json
import logging
import time
from typing import Dict, Any
from app.observability.pii_scrubber import EnterprisePIIRedactor

class StructuredLogger:
    """Structured JSON Logger for Google Cloud Logging."""
    
    def __init__(self, logger_name: str = "BugTriageAgent"):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            self.logger.addHandler(handler)

    def log_intent(self, agent_name: str, tool_name: str, args: Dict[str, Any], request_id: str) -> None:
        """Intent vs. Outcome Capture: Logs INTENT state before tool execution."""
        raw_json = json.dumps(args, default=str)
        redacted_json, _ = EnterprisePIIRedactor.redact_text(raw_json)
        
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "phase": "INTENT",
            "request_id": request_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "intended_args": json.loads(redacted_json)
        }
        self.logger.info(json.dumps(payload))

    def log_outcome(self, agent_name: str, tool_name: str, outcome: Dict[str, Any], duration_ms: float, request_id: str) -> None:
        """Intent vs. Outcome Capture: Logs OUTCOME state after tool execution."""
        raw_json = json.dumps(outcome, default=str)
        redacted_json, _ = EnterprisePIIRedactor.redact_text(raw_json)
        
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "phase": "OUTCOME",
            "request_id": request_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "duration_ms": round(duration_ms, 2),
            "actual_outcome": json.loads(redacted_json)
        }
        self.logger.info(json.dumps(payload))
