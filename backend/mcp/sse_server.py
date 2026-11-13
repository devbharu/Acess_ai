"""
Flask Blueprint providing HTTP/SSE transport and REST endpoints for the MCP server.
Enables frontend tool inspection and external SSE-based MCP clients.
"""

import uuid
import json
import logging
from flask import Blueprint, request, jsonify, Response, g
from .server import mcp_server, PROTOCOL_VERSION
from .tools import TOOL_CATEGORIES

logger = logging.getLogger("accessai.mcp.sse")

mcp_bp = Blueprint("mcp", __name__, url_prefix="/api/mcp")

# Store active SSE sessions
_sessions = {}


@mcp_bp.route("/status", methods=["GET"])
def get_mcp_status():
    """Returns current MCP server health, protocol version, and primitives count."""
    status = mcp_server.get_status()
    return jsonify(status)


@mcp_bp.route("/tools", methods=["GET"])
def get_mcp_tools():
    """Returns all 18 MCP tools with categories, descriptions, and schemas."""
    tools = mcp_server.list_tools()
    enriched = []
    for t in tools:
        item = dict(t)
        item["category"] = TOOL_CATEGORIES.get(t["name"], "General")
        enriched.append(item)
    return jsonify({"tools": enriched, "count": len(enriched)})


@mcp_bp.route("/resources", methods=["GET"])
def get_mcp_resources():
    """Returns all registered MCP resources."""
    resources = mcp_server.list_resources()
    return jsonify({"resources": resources, "count": len(resources)})


@mcp_bp.route("/prompts", methods=["GET"])
def get_mcp_prompts():
    """Returns all registered MCP prompts."""
    prompts = mcp_server.list_prompts()
    return jsonify({"prompts": prompts, "count": len(prompts)})


@mcp_bp.route("/execute", methods=["POST"])
def execute_tool_direct():
    """
    Direct endpoint to execute an MCP tool.
    Accepts { tool: str, arguments: dict }.
    """
    data = request.get_json(silent=True) or {}
    tool_name = data.get("tool") or data.get("name")
    arguments = data.get("arguments") or {}

    user_id = getattr(g, "user_id", None) or "usr_anonymous"
    context = {"user_id": user_id}

    res = mcp_server.execute_tool(tool_name, arguments, context=context)
    if res.get("isError"):
        return jsonify(res), 400
    return jsonify(res)


@mcp_bp.route("/sse", methods=["GET"])
def sse_transport():
    """
    MCP standard Server-Sent Events endpoint.
    Emits an initial 'endpoint' event containing the URL to which clients should post JSON-RPC messages.
    """
    session_id = f"mcp_sess_{uuid.uuid4().hex[:12]}"

    def event_stream():
        # MCP SSE handshake: send endpoint event with session_id query param
        post_endpoint = f"/api/mcp/messages?session_id={session_id}"
        yield f"event: endpoint\ndata: {post_endpoint}\n\n"

        # Keep-alive heartbeat
        yield f": ping\n\n"

    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@mcp_bp.route("/messages", methods=["POST"])
def handle_mcp_message():
    """
    Handles JSON-RPC 2.0 messages from SSE-connected clients.
    """
    req_data = request.get_json(silent=True) or {}
    session_id = request.args.get("session_id")

    user_id = getattr(g, "user_id", None) or "usr_anonymous"
    context = {"user_id": user_id, "session_id": session_id}

    response = mcp_server.handle_jsonrpc(req_data, context=context)
    if response is None:
        return ("", 204)
    return jsonify(response)
