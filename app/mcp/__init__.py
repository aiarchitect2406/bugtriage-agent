"""MCP package for exposing Bug Triage tools via Model Context Protocol."""

from app.mcp.server import TOOLS, handle_mcp_request

__all__ = ["TOOLS", "handle_mcp_request"]
