"""GitHub MCP Server Package.

Provides MCP tools for GitHub operations via FastMCP server.
"""

from mcp.server.fastmcp import FastMCP

# Create single global MCP server instance
# This MUST be at package level to avoid double-instantiation when module is run as __main__
mcp = FastMCP("github-manager")

__all__ = ["mcp"]
