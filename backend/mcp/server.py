"""
AccessAI Model Context Protocol (MCP) Server.
Implements the 2024-11-05 MCP specification with support for Tools, Resources, and Prompts.
Provides FastMCP-style decorators and handles standard JSON-RPC 2.0 messages.
"""

import inspect
import json
import logging
from typing import Dict, Any, List, Optional, Callable, Union

logger = logging.getLogger("accessai.mcp.server")

PROTOCOL_VERSION = "2024-11-05"


class MCPServer:
    """
    Model Context Protocol Server for AccessAI.
    Manages tools, resources, and prompt templates.
    """

    def __init__(self, name: str = "AccessAI-MCP-Server", version: str = "1.0.0", description: str = ""):
        self.name = name
        self.version = version
        self.description = description or "AccessAI Multimodal Accessibility MCP Server"
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}

    # -------------------------------------------------------------
    # Tool Registration
    # -------------------------------------------------------------
    def tool(self, name: Optional[str] = None, description: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None):
        """
        Decorator to register a function as an MCP tool.
        """
        def decorator(func: Callable):
            tool_name = name or func.__name__
            tool_desc = (description or func.__doc__ or f"Tool: {tool_name}").strip()

            # Infer JSON Schema from signature if parameters not provided
            if parameters:
                schema = parameters
            else:
                schema = self._infer_schema(func)

            self._tools[tool_name] = {
                "name": tool_name,
                "description": tool_desc,
                "inputSchema": schema,
                "func": func,
            }
            return func
        return decorator

    def register_tool(self, name: str, description: str, parameters: Dict[str, Any], func: Callable):
        """Direct method to register an MCP tool."""
        self._tools[name] = {
            "name": name,
            "description": description.strip(),
            "inputSchema": parameters,
            "func": func,
        }

    # -------------------------------------------------------------
    # Resource Registration
    # -------------------------------------------------------------
    def resource(self, uri: str, name: Optional[str] = None, description: Optional[str] = None, mime_type: str = "application/json"):
        """
        Decorator to register a resource getter.
        URI can be static or a pattern (e.g., accessai://documents/{doc_id}).
        """
        def decorator(func: Callable):
            res_name = name or func.__name__
            res_desc = (description or func.__doc__ or f"Resource: {uri}").strip()
            self._resources[uri] = {
                "uri": uri,
                "name": res_name,
                "description": res_desc,
                "mimeType": mime_type,
                "func": func,
            }
            return func
        return decorator

    # -------------------------------------------------------------
    # Prompt Registration
    # -------------------------------------------------------------
    def prompt(self, name: str, description: Optional[str] = None, arguments: Optional[List[Dict[str, Any]]] = None):
        """
        Decorator to register an MCP prompt template.
        """
        def decorator(func: Callable):
            p_desc = (description or func.__doc__ or f"Prompt: {name}").strip()
            self._prompts[name] = {
                "name": name,
                "description": p_desc,
                "arguments": arguments or [],
                "func": func,
            }
            return func
        return decorator

    # -------------------------------------------------------------
    # Metadata & Introspection
    # -------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        """Returns MCP server health and capabilities summary."""
        return {
            "status": "active",
            "server": self.name,
            "version": self.version,
            "protocol_version": PROTOCOL_VERSION,
            "transports": ["stdio", "sse"],
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": False, "listChanged": True},
                "prompts": {"listChanged": True},
            },
            "tools_count": len(self._tools),
            "resources_count": len(self._resources),
            "prompts_count": len(self._prompts),
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns tools formatted according to MCP tools/list."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            }
            for t in self._tools.values()
        ]

    def list_resources(self) -> List[Dict[str, Any]]:
        """Returns resources formatted according to MCP resources/list."""
        return [
            {
                "uri": r["uri"],
                "name": r["name"],
                "description": r["description"],
                "mimeType": r["mimeType"],
            }
            for r in self._resources.values()
        ]

    def list_prompts(self) -> List[Dict[str, Any]]:
        """Returns prompts formatted according to MCP prompts/list."""
        return [
            {
                "name": p["name"],
                "description": p["description"],
                "arguments": p["arguments"],
            }
            for p in self._prompts.values()
        ]

    # -------------------------------------------------------------
    # Execution & Request Dispatch (JSON-RPC 2.0)
    # -------------------------------------------------------------
    def execute_tool(self, name: str, arguments: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a registered tool by name with arguments and optional injected context.
        """
        tool = self._tools.get(name)
        if not tool:
            return {"isError": True, "error": f"Tool '{name}' not found."}

        func = tool["func"]
        try:
            sig = inspect.signature(func)
            merged = dict(context or {})
            merged.update(arguments or {})

            filtered_args = {}
            for param_name, param in sig.parameters.items():
                if param_name in merged:
                    filtered_args[param_name] = merged[param_name]
                elif param.default is not inspect.Parameter.empty:
                    pass

            result = func(**filtered_args)
            return {"isError": False, "result": result}
        except Exception as e:
            logger.error("MCP tool '%s' error: %s", name, e)
            return {"isError": True, "error": str(e)}

    def read_resource(self, uri: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Reads a resource by exact URI or pattern."""
        # Check exact match
        if uri in self._resources:
            res = self._resources[uri]
            try:
                data = res["func"](context=context)
                text_content = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
                return {
                    "contents": [{
                        "uri": uri,
                        "mimeType": res["mimeType"],
                        "text": text_content,
                    }]
                }
            except Exception as e:
                return {"isError": True, "error": str(e)}

        # Check parameterized URI (e.g. accessai://documents/{id})
        for pattern, res in self._resources.items():
            if "{" in pattern and "}" in pattern:
                prefix = pattern.split("{")[0]
                if uri.startswith(prefix):
                    param_val = uri[len(prefix):]
                    try:
                        data = res["func"](param_val, context=context)
                        text_content = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
                        return {
                            "contents": [{
                                "uri": uri,
                                "mimeType": res["mimeType"],
                                "text": text_content,
                            }]
                        }
                    except Exception as e:
                        return {"isError": True, "error": str(e)}

        return {"isError": True, "error": f"Resource '{uri}' not found."}

    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generates prompt template messages."""
        p = self._prompts.get(name)
        if not p:
            return {"isError": True, "error": f"Prompt '{name}' not found."}
        try:
            return p["func"](arguments or {})
        except Exception as e:
            return {"isError": True, "error": str(e)}

    def handle_jsonrpc(self, request: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Dispatches a JSON-RPC 2.0 request according to the MCP specification.
        """
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        # Notifications (no id)
        if method == "notifications/initialized":
            logger.info("MCP client initialized.")
            return None

        # Ping
        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        # Initialize
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": False, "listChanged": True},
                        "prompts": {"listChanged": True},
                    },
                    "serverInfo": {
                        "name": self.name,
                        "version": self.version,
                    },
                },
            }

        # Tools List
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.list_tools()}}

        # Tools Call
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            exec_res = self.execute_tool(tool_name, arguments, context=context)
            if exec_res.get("isError"):
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {exec_res.get('error')}"}],
                        "isError": True,
                    },
                }
            res_val = exec_res.get("result")
            text_out = json.dumps(res_val, indent=2) if isinstance(res_val, (dict, list)) else str(res_val)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": text_out}],
                    "isError": False,
                },
            }

        # Resources List
        if method == "resources/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": self.list_resources()}}

        # Resources Read
        if method == "resources/read":
            uri = params.get("uri")
            read_res = self.read_resource(uri, context=context)
            if read_res.get("isError"):
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": read_res.get("error")},
                }
            return {"jsonrpc": "2.0", "id": req_id, "result": read_res}

        # Prompts List
        if method == "prompts/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": self.list_prompts()}}

        # Prompts Get
        if method == "prompts/get":
            p_name = params.get("name")
            p_args = params.get("arguments") or {}
            p_res = self.get_prompt(p_name, p_args)
            if p_res.get("isError"):
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": p_res.get("error")},
                }
            return {"jsonrpc": "2.0", "id": req_id, "result": p_res}

        # Unknown method
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found."},
        }

    def _infer_schema(self, func: Callable) -> Dict[str, Any]:
        """Infers JSON Schema for a callable from its inspect signature."""
        sig = inspect.signature(func)
        properties = {}
        required = []

        for p_name, param in sig.parameters.items():
            if p_name in ("context", "user_id"):
                continue  # Injected runtime context
            type_name = "string"
            if param.annotation == int:
                type_name = "integer"
            elif param.annotation == float:
                type_name = "number"
            elif param.annotation == bool:
                type_name = "boolean"
            elif param.annotation in (list, List):
                type_name = "array"
            elif param.annotation in (dict, Dict):
                type_name = "object"

            properties[p_name] = {"type": type_name}
            if param.default is inspect.Parameter.empty:
                required.append(p_name)

        schema = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema


# Global default server instance
mcp_server = MCPServer(
    name="AccessAI-MCP-Server",
    version="1.0.0",
    description="Multimodal accessibility agent exposing 18 tools, document/image resources, and prompt templates.",
)
