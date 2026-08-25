"""Pydantic Schemas for Human-in-the-Loop Gateway, Webhook Signal Listener & A2UI Cards."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class HITLGateState(BaseModel):
    """Session State for Human-in-the-Loop Approval Gate."""
    session_id: str = Field(..., description="ADK Session Engine identifier")
    issue_id: str = Field(..., description="Target bug ticket ID")
    status: str = Field(
        ..., 
        description="Current state: 'AWAITING_HUMAN_REVIEW', 'APPROVED', 'CHANGES_REQUESTED', or 'REJECTED'"
    )
    severity: str
    priority: str
    primary_owner: str
    failing_test_code: str
    proposed_diff_patch: str
    patch_explanation: str
    reviewer_id: Optional[str] = Field(None, description="Developer ID who signed off or requested changes")
    feedback_text: Optional[str] = Field(None, description="Iterative prompt feedback submitted by developer")

class WebhookSignalInput(BaseModel):
    """Payload Received by Webhook Endpoint from Interactive Card."""
    session_id: str
    issue_id: str
    action: str = Field(..., description="Action selected: 'APPROVE', 'REJECT', or 'MODIFY'")
    reviewer_id: str = Field(..., description="ID/handle of approving developer")
    feedback_prompt: Optional[str] = Field(None, description="Developer feedback text if action is 'MODIFY'")
    hmac_signature: str = Field(..., description="HMAC SHA-256 signature for security verification")

class ApprovalResponse(BaseModel):
    """Response Returned to Interactive Card after Webhook Processing."""
    status: str = Field(..., description="Outcome status: 'SUCCESS' or 'ERROR'")
    action_taken: str = Field(..., description="Action executed: 'PR_CREATED', 'REFINEMENT_RETRY', 'ISSUE_REJECTED'")
    message: str = Field(..., description="Detailed result message or error recovery hint")
    pr_url: Optional[str] = Field(None, description="Draft Pull Request URL if approved")
