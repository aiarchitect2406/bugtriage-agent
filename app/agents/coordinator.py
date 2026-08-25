"""Coordinator Agent for ADK 2.0 Bug Triage System."""

import uuid
import logging
from typing import Dict, Any, List, Optional
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from app.config import Config
from app.models.bug_report import BugReport, SanitizedBugReport, EnrichmentContext
from app.models.hitl import HITLGateState
from app.agents.ingestion import ingestion_agent, IngestionAgentRunner
from app.agents.dedupe import dedupe_agent, DedupeAgentRunner
from app.agents.enrichment import enrichment_agent, EnrichmentAgentRunner
from app.agents.remediation import remediation_agent, CodeRemediationAgentRunner
from app.agents.review import code_review_agent, CodeReviewAgentRunner
from app.plugins.guardrails import GuardrailPolicyPlugin
from app.observability.tracing import CloudObservabilityPlugin
from app.hitl.state_store import HITLStateStore, generate_memories_callback
from app.hitl.card_renderer import render_a2ui_review_card
from app.observability.logger import StructuredLogger
from app.skills.loader import (
    get_skill_catalog,
    discover_available_skills,
    load_skill_instruction,
)
from app.agents.dynamic_subagent import get_subagent_factory
from app.tools import (
    sanitize_logs_and_extract_stack,
    query_similar_bugs_by_vector,
    resolve_codeowners_and_blame,
    execute_reproduction_and_sandbox_fix,
    create_draft_pull_request,
    review_code_patch_with_claude,
)

_catalog = get_skill_catalog()

COORDINATOR_AGENT_CONSTITUTION = f"""
You are the Lead Bug Triage Coordinator Agent implementing Maker-Checker multi-model orchestration on Google ADK 2.0 with Progressive Disclosure.

Operational Workflow:
1. INGESTION: Sanitize raw logs, redact PII via DLP/Model Armor, and extract structured stack frames.
2. DEDUPLICATION: Query vector similarity. If duplicate, STOP immediately and link to parent ticket.
3. ENRICHMENT: Resolve microservice CODEOWNERS and calculate SLA priority (Blocker -> P0).
4. REMEDIATION [MAKER]: Synthesize reproduction pytest in isolated sandbox with Gemini 3.1 Pro.
5. PEER REVIEW [CHECKER]: Conduct independent Maker-Checker code & security audit using Claude Sonnet on Vertex AI.
6. HITL REVIEW & PR: Prepare high-confidence Draft Pull Request with Maker-Checker review badge.

{_catalog.get_skills_manifest()}
"""

coordinator_agent = Agent(
    name="coordinator_agent",
    model=Gemini(
        model=Config.FAST_MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=COORDINATOR_AGENT_CONSTITUTION.strip(),
    tools=[
        discover_available_skills,
        load_skill_instruction,
        sanitize_logs_and_extract_stack,
        query_similar_bugs_by_vector,
        resolve_codeowners_and_blame,
        execute_reproduction_and_sandbox_fix,
        create_draft_pull_request,
        review_code_patch_with_claude,
    ],
    sub_agents=[
        ingestion_agent,
        dedupe_agent,
        enrichment_agent,
        remediation_agent,
        code_review_agent,
    ],
    after_agent_callback=generate_memories_callback,
)


_HISTORICAL_ISSUES_STORE: List[Dict[str, Any]] = [
    {
        "issue_id": "BUG-2026-001",
        "title": "NullPointerException in payment_gateway.py during checkout",
        "description": "Crash when processing checkout with null shipping address or None payload",
        "stack_trace": "File \"services/payment_gateway.py\", line 42, in process_checkout\nTypeError: 'NoneType' object is not subscriptable",
    }
]


class TriageCoordinator:
    """Lead Bug Triage Coordinator Engine implementing end-to-end multi-agent orchestration."""

    def __init__(self):
        self.logger = StructuredLogger("TriageCoordinator")
        self.ingestion_runner = IngestionAgentRunner(self.logger)
        self.dedupe_runner = DedupeAgentRunner(self.logger)
        self.enrichment_runner = EnrichmentAgentRunner(self.logger)
        self.remediation_runner = CodeRemediationAgentRunner(self.logger)
        self.review_runner = CodeReviewAgentRunner(self.logger)
        self.guardrail_plugin = GuardrailPolicyPlugin()
        self.agent = coordinator_agent

    def execute_triage_pipeline(
        self,
        bug_report: BugReport,
        historical_candidates: Optional[List[Dict[str, Any]]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Executes full bug triage lifecycle from intake to HITL pause."""
        req_id = request_id or f"req-{uuid.uuid4().hex[:8]}"
        session_id = f"session-{uuid.uuid4().hex[:8]}"
        
        # Step 1: Ingestion & Log Sanitization
        ingest_res = self.ingestion_runner.process_raw_report(bug_report, request_id=req_id)
        if ingest_res.get("status") == "ERROR":
            return {"status": "ERROR", "step": "INGESTION", "message": ingest_res.get("message")}
        
        sanitized_report = SanitizedBugReport(**ingest_res["sanitized_report"])

        # Step 2: Vector Duplicate Detection
        candidates = historical_candidates if historical_candidates is not None else list(_HISTORICAL_ISSUES_STORE)
        dedupe_res = self.dedupe_runner.check_duplicate(
            sanitized_report, 
            historical_candidates=candidates, 
            request_id=req_id
        )
        if dedupe_res.get("status") == "ERROR":
            return {"status": "ERROR", "step": "DEDUPLICATION", "message": dedupe_res.get("message")}
        
        dedupe_info = dedupe_res.get("dedupe_result", {})
        if dedupe_info.get("is_duplicate"):
            return {
                "status": "DUPLICATE_LINKED",
                "issue_id": sanitized_report.issue_id,
                "parent_issue_id": dedupe_info.get("matching_parent_issue_id"),
                "similarity_score": dedupe_info.get("similarity_score"),
                "explanation": dedupe_info.get("explanation"),
            }

        # Store newly triaged issue in historical store for subsequent deduplication
        _HISTORICAL_ISSUES_STORE.append({
            "issue_id": sanitized_report.issue_id,
            "title": sanitized_report.title,
            "description": sanitized_report.cleaned_description,
            "stack_trace": bug_report.stack_trace or sanitized_report.sanitized_logs,
        })

        # Step 3: Ownership & Context Enrichment
        severity_hint = bug_report.metadata.get("severity") or (
            "Blocker" if any(k in bug_report.title.lower() for k in ["critical", "blocker", "npe"]) else "Major"
        )
        enrich_res = self.enrichment_runner.enrich_bug_context(
            sanitized_report, 
            severity_hint=severity_hint, 
            request_id=req_id
        )
        if enrich_res.get("status") == "ERROR":
            return {"status": "ERROR", "step": "ENRICHMENT", "message": enrich_res.get("message")}
        
        enrichment_context = EnrichmentContext(**enrich_res["enrichment_context"])

        # Step 4: Guardrail Policy Check
        guardrail_res = self.guardrail_plugin.validate_triage_decision(
            severity=enrichment_context.severity,
            priority=enrichment_context.priority,
            primary_owner=enrichment_context.primary_owner
        )
        if not guardrail_res.get("is_valid"):
            return {
                "status": "REJECTED_BY_GUARDRAIL",
                "violations": guardrail_res.get("violations"),
                "issue_id": sanitized_report.issue_id
            }

        # Step 5: Code Remediation & Sandbox Fix (Maker: Gemini 3.1 Pro)
        remed_res = self.remediation_runner.generate_remediation_and_sandbox_fix(
            sanitized_report,
            enrichment_context,
            request_id=req_id
        )
        if remed_res.get("status") == "ERROR":
            return {"status": "ERROR", "step": "REMEDIATION", "message": remed_res.get("message")}

        repro_test = remed_res.get("reproduction_test", {})
        fix_patch = remed_res.get("fix_patch", {})
        sandbox_res = remed_res.get("sandbox_result", {})

        # Step 5.5: Independent Peer Code Review (Checker: Claude Sonnet)
        review_res = self.review_runner.review_patch(
            sanitized_report=sanitized_report,
            enrichment_context=enrichment_context,
            diff_patch=fix_patch.get("diff_patch", ""),
            patch_explanation=fix_patch.get("explanation", ""),
            reproduction_test_code=repro_test.get("test_code", ""),
            request_id=req_id
        )
        code_review_info = review_res

        # Step 6: Automated PR Creation upon Claude Sonnet Review Approval
        gate_state = HITLGateState(
            session_id=session_id,
            issue_id=sanitized_report.issue_id,
            status="APPROVED",
            severity=enrichment_context.severity,
            priority=enrichment_context.priority,
            primary_owner=enrichment_context.primary_owner,
            failing_test_code=repro_test.get("test_code", ""),
            proposed_diff_patch=fix_patch.get("diff_patch", ""),
            patch_explanation=fix_patch.get("explanation", ""),
            claude_review=code_review_info,
        )
        a2ui_card = render_a2ui_review_card(gate_state)
        HITLStateStore.async_consolidate_memory(session_id)

        # Directly open PR when Claude Maker-Checker review verdict is APPROVED
        if code_review_info.get("verdict") == "APPROVED":
            pr_output = create_draft_pull_request(
                issue_id=sanitized_report.issue_id,
                repository_name=Config.GITHUB_REPO,
                diff_patch=fix_patch.get("diff_patch", ""),
                test_code=repro_test.get("test_code", ""),
                reviewer_handle=enrichment_context.primary_owner,
                review_verdict=code_review_info.get("verdict", "APPROVED"),
                review_score=code_review_info.get("score", 95),
                reviewer_model=code_review_info.get("reviewer_model", "claude-sonnet-4-6"),
                commit_message=f"fix({sanitized_report.issue_id}): Automated remediation verified by Claude Sonnet peer review",
            )
            pr_res = pr_output if isinstance(pr_output, dict) else pr_output.model_dump()
            return {
                "status": "PR_CREATED",
                "session_id": session_id,
                "issue_id": sanitized_report.issue_id,
                "primary_owner": enrichment_context.primary_owner,
                "severity": enrichment_context.severity,
                "priority": enrichment_context.priority,
                "sla_target_hours": enrichment_context.sla_target_hours,
                "sandbox_status": sandbox_res.get("status"),
                "proposed_diff_patch": fix_patch.get("diff_patch"),
                "failing_test_code": repro_test.get("test_code"),
                "code_review": code_review_info,
                "pull_request_url": pr_res.get("pull_request_url"),
                "pull_request_number": pr_res.get("pull_request_number"),
                "branch_name": pr_res.get("branch_name"),
                "message": pr_res.get("message"),
                "a2ui_card": a2ui_card,
            }

        return {
            "status": "NEEDS_ATTENTION",
            "session_id": session_id,
            "issue_id": sanitized_report.issue_id,
            "primary_owner": enrichment_context.primary_owner,
            "severity": enrichment_context.severity,
            "priority": enrichment_context.priority,
            "sla_target_hours": enrichment_context.sla_target_hours,
            "sandbox_status": sandbox_res.get("status"),
            "proposed_diff_patch": fix_patch.get("diff_patch"),
            "failing_test_code": repro_test.get("test_code"),
            "code_review": code_review_info,
            "a2ui_card": a2ui_card,
        }

    @classmethod
    def run_triage_pipeline(
        cls, bug_report: BugReport, historical_candidates: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Class method convenience runner for autonomous bug triage pipeline."""
        coordinator = cls()
        return coordinator.execute_triage_pipeline(
            bug_report=bug_report,
            historical_candidates=historical_candidates
        )



# Direct re-export of the ADK 2.0 Graph Workflow DAG
from app.workflow import bug_triage_workflow as triage_workflow, bug_triage_workflow
