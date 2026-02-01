"""GitHub MCP Server - Main entry point.

FastMCP server that provides GitHub operation tools to Claude Code via MCP protocol.
"""

import logging
import os
import sys

# Import the singleton mcp instance from package level
from . import mcp

__all__ = ["mcp", "main"]

# Configure logging to stderr (stdout is used for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Validate GITHUB_TOKEN is available
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    logger.error("GITHUB_TOKEN not found in environment!")
    logger.error("Set GITHUB_TOKEN in your .mcp.json configuration.")
    logger.error("GitHub API operations will fail without authentication.")
else:
    logger.info("GITHUB_TOKEN loaded successfully")

# Import tool modules to register tools
# Tools are registered via @mcp.tool() decorators in each module
try:
    from .tools import batch_operations, ci, issues, milestones, pulls  # noqa: F401

    logger.info("All tool modules loaded successfully")
except ImportError as e:
    logger.error(f"Failed to import tool modules: {e}")
    raise


def main() -> None:
    """
    Run the MCP server.

    Starts the FastMCP server which listens on stdio for MCP protocol messages.
    Claude Code will communicate with this server to invoke GitHub operations.
    """
    logger.info("GitHub MCP Server starting...")

    # Verify tools are registered before starting server
    try:
        tools = mcp._tool_manager.list_tools()
        tool_count = len(tools)
        logger.info(f"✅ {tool_count} tools registered: {', '.join(t.name for t in tools)}")

        if tool_count == 0:
            logger.error("❌ CRITICAL: No tools registered before server start!")
            logger.error("Check that tool modules are importing correctly")
            raise RuntimeError("Tool registration failed - cannot start server")

        logger.info(f"✅ Server ready with {tool_count} tools")
    except Exception as e:
        logger.error(f"Tool verification failed: {e}", exc_info=True)
        raise

    logger.info("Server name: github-manager")
    logger.info("Listening on stdio for MCP protocol messages")

    try:
        # Run the MCP server (blocks until terminated)
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
