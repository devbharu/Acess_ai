"""
AccessAI Model Context Protocol (MCP) Package.
Initializes and exposes the unified MCPServer instance with 18 tools, resources, and prompts.
"""

from .server import MCPServer, mcp_server, PROTOCOL_VERSION
from .tools import register_all_mcp_tools, TOOL_CATEGORIES
from .resources import register_all_mcp_resources
from .prompts import register_all_mcp_prompts

# Register all modular primitives onto the server instance
register_all_mcp_tools(mcp_server)
register_all_mcp_resources(mcp_server)
register_all_mcp_prompts(mcp_server)

__all__ = [
    "MCPServer",
    "mcp_server",
    "PROTOCOL_VERSION",
    "TOOL_CATEGORIES",
]
