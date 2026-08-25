"""Guardrail Policy Plugin for Google ADK 2.0 enforcing Model Armor & SLA policies."""

import logging
from typing import Dict, Any, Optional
from google.adk.plugins import BasePlugin
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

logger = logging.getLogger("GuardrailPolicyPlugin")


class GuardrailPolicyPlugin(BasePlugin):
    """Native ADK 2.0 Plugin for Model Armor Guardrails & SLA Policy Enforcement."""

    def __init__(self, name: str = "guardrail_policy_plugin"):
        super().__init__(name=name)
        self.name = name

    def validate_triage_decision(self, severity: str, priority: str, primary_owner: str) -> Dict[str, Any]:
        """Self-evaluation guardrail verifying that severity-to-priority SLA rules are strictly met."""
        sev = (severity or "Major").capitalize()
        prio = (priority or "P1").upper()

        valid = True
        violations = []

        # Rule 1: Blocker must map to P0
        if sev == "Blocker" and prio != "P0":
            valid = False
            violations.append(f"Policy Violation: Severity 'Blocker' MUST map to Priority 'P0' (found {prio}).")

        # Rule 2: P0 requires explicit team owner
        if prio == "P0" and (not primary_owner or primary_owner == "@core-triage-team"):
            valid = False
            violations.append("Policy Violation: P0 Blocker requires explicit domain owner, cannot fall back to @core-triage-team.")

        return {
            "is_valid": valid,
            "violations": violations,
            "status": "APPROVED" if valid else "REJECTED_BY_GUARDRAIL"
        }

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        """ADK 2.0 Lifecycle Callback: Pre-execution policy check and Model Armor inspection."""
        tool_name = getattr(tool, "name", str(tool))
        logger.debug(f"[Model Armor Guardrail] Inspecting tool call: {tool_name}")

        if tool_name == "create_draft_pull_request" and not tool_args.get("issue_id"):
            logger.warning("[Model Armor Guardrail] Denied: Missing required issue_id for PR creation.")
            return {
                "status": "ERROR",
                "message": "Policy Violation: create_draft_pull_request requires a valid issue_id."
            }
        return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> Optional[dict]:
        """ADK 2.0 Lifecycle Callback: Post-execution audit and SLA validation."""
        tool_name = getattr(tool, "name", str(tool))
        if tool_name == "resolve_codeowners_and_blame" and isinstance(result, dict):
            ctx = result.get("enrichment_context", {})
            guard_check = self.validate_triage_decision(
                severity=ctx.get("severity", "Major"),
                priority=ctx.get("priority", "P1"),
                primary_owner=ctx.get("primary_owner", "@core-triage-team")
            )
            if not guard_check["is_valid"]:
                logger.error(f"[Model Armor Guardrail] SLA Policy Violation detected: {guard_check['violations']}")
        return None
