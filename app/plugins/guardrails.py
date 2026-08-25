"""Guardrail Policy Plugin for ADK 2.0 Agent validating SLA severity-to-priority rules."""

import logging
from typing import Dict, Any, Optional

try:
    from google.adk.plugins import BasePlugin
except ImportError:
    class BasePlugin:
        pass

class GuardrailPolicyPlugin(BasePlugin):
    """ADK 2.0 Plugin for Self-Evaluation & Policy Enforcement."""
    
    def __init__(self, name: str = "guardrail_policy_plugin"):
        try:
            super().__init__(name=name)
        except TypeError:
            super().__init__()
        self.name = name

    def validate_triage_decision(self, severity: str, priority: str, primary_owner: str) -> Dict[str, Any]:
        """Self-evaluation guardrail verifying that severity-to-priority SLA rules are strictly met."""
        severity = severity.capitalize()
        priority = priority.upper()
        
        valid = True
        violations = []
        
        # Rule 1: Blocker must map to P0
        if severity == "Blocker" and priority != "P0":
            valid = False
            violations.append(f"Policy Violation: Severity 'Blocker' MUST map to Priority 'P0' (found {priority}).")
            
        # Rule 2: P0 requires explicit team owner
        if priority == "P0" and (not primary_owner or primary_owner == "@core-triage-team"):
            valid = False
            violations.append("Policy Violation: P0 Blocker requires explicit domain owner, cannot fall back to @core-triage-team.")

        return {
            "is_valid": valid,
            "violations": violations,
            "status": "APPROVED" if valid else "REJECTED_BY_GUARDRAIL"
        }
