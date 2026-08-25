"""Agent-to-User Interface (A2UI) Declarative Review Card Renderer for Slack/Jira."""

from typing import List, Dict, Any
from app.models.hitl import HITLGateState

def render_a2ui_review_card(state: HITLGateState) -> List[Dict[str, Any]]:
    """Generates Agent-to-User Interface (A2UI) declarative JSON payload."""
    a2ui_payload = [
        {
            "beginRendering": {
                "surfaceId": f"triage-review-{state.issue_id.lower()}",
                "root": "main-card"
            }
        },
        {
            "surfaceUpdate": {
                "surfaceId": f"triage-review-{state.issue_id.lower()}",
                "components": [
                    {
                        "id": "main-card",
                        "component": { "Card": { "child": "main-col" } }
                    },
                    {
                        "id": "main-col",
                        "component": {
                            "Column": {
                                "children": {
                                    "explicitList": [
                                        "card-title",
                                        "severity-badge",
                                        "owner-text",
                                        "patch-explanation",
                                        "diff-preview",
                                        "action-button-row"
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": "card-title",
                        "component": { "Text": { "usageHint": "h2", "text": { "literalString": f"Review Fix for {state.issue_id}" } } }
                    },
                    {
                        "id": "severity-badge",
                        "component": { "Text": { "usageHint": "caption", "text": { "literalString": f"Severity: {state.severity} | Priority: {state.priority}" } } }
                    },
                    {
                        "id": "owner-text",
                        "component": { "Text": { "usageHint": "body", "text": { "literalString": f"Assigned Owner: {state.primary_owner}" } } }
                    },
                    {
                        "id": "patch-explanation",
                        "component": { "Text": { "usageHint": "body", "text": { "literalString": state.patch_explanation } } }
                    },
                    {
                        "id": "diff-preview",
                        "component": { "CodeBlock": { "language": "diff", "text": { "literalString": state.proposed_diff_patch } } }
                    },
                    {
                        "id": "action-button-row",
                        "component": {
                            "Row": {
                                "children": {
                                    "explicitList": ["approve-btn", "modify-btn", "reject-btn"]
                                }
                            }
                        }
                    },
                    {
                        "id": "approve-btn",
                        "component": {
                            "Button": {
                                "variant": "primary",
                                "child": "approve-label",
                                "action": {
                                    "name": "hitl_approve_action",
                                    "context": [
                                        { "key": "session_id", "valueString": state.session_id },
                                        { "key": "action", "valueString": "APPROVE" }
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": "approve-label",
                        "component": { "Text": { "literalString": "Approve & Push Draft PR" } }
                    },
                    {
                        "id": "modify-btn",
                        "component": {
                            "Button": {
                                "variant": "secondary",
                                "child": "modify-label",
                                "action": {
                                    "name": "hitl_modify_action",
                                    "context": [
                                        { "key": "session_id", "valueString": state.session_id },
                                        { "key": "action", "valueString": "MODIFY" }
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": "modify-label",
                        "component": { "Text": { "literalString": "Request Changes" } }
                    },
                    {
                        "id": "reject-btn",
                        "component": {
                            "Button": {
                                "variant": "destructive",
                                "child": "reject-label",
                                "action": {
                                    "name": "hitl_reject_action",
                                    "context": [
                                        { "key": "session_id", "valueString": state.session_id },
                                        { "key": "action", "valueString": "REJECT" }
                                    ]
                                }
                            }
                        }
                    },
                    {
                        "id": "reject-label",
                        "component": { "Text": { "literalString": "Reject Fix" } }
                    }
                ]
            }
        }
    ]
    return a2ui_payload
