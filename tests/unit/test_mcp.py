"""Unit tests for the Bug Triage MCP Server."""

import json
from app.mcp.server import handle_mcp_request, TOOLS

def test_mcp_tools_list():
    """Verifies that MCP tools/list returns all available bug triage tools."""
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    resp = handle_mcp_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    
    assert "sanitize_logs_and_extract_stack" in tool_names
    assert "query_similar_bugs_by_vector" in tool_names
    assert "resolve_codeowners_and_blame" in tool_names
    assert "execute_reproduction_and_sandbox_fix" in tool_names
    assert "create_draft_pull_request" in tool_names

def test_mcp_tools_call_sanitize():
    """Verifies that MCP tools/call executes tool handlers correctly."""
    req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "sanitize_logs_and_extract_stack",
            "arguments": {
                "issue_id": "BUG-MCP-001",
                "title": "Auth failure on token parse",
                "description": "User token failed verification",
                "raw_logs": "Error: token=secret123 in /services/auth.py"
            }

        }
    }
    resp = handle_mcp_request(req)
    assert resp["jsonrpc"] == "2.0"
    assert "result" in resp
    content = resp["result"]["content"]
    assert len(content) > 0
    parsed = json.loads(content[0]["text"])
    assert parsed["status"] == "SUCCESS"

