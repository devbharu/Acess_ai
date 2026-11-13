"""
AccessAI Model Context Protocol (MCP) Stdio Server.
Enables external MCP clients (Claude Desktop, Cursor, Zed, Claude Code CLI)
to interact with AccessAI tools, resources, and prompts over standard I/O.

Usage:
    python -m backend.mcp.stdio_server
"""

import sys
import os
import json
import logging

# Ensure project root is in path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.mcp import mcp_server

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="[MCP-Stdio] %(asctime)s: %(message)s")
logger = logging.getLogger("accessai.mcp.stdio")


def main():
    logger.info("Starting AccessAI MCP stdio server (%s tools registered)...", len(mcp_server._tools))
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            res = mcp_server.handle_jsonrpc(req)
            if res is not None:
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
        except Exception as e:
            logger.error("Error processing stdio line: %s", e)
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
