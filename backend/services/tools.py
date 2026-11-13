"""
AccessAI Tool Registry & Compatibility Facade.
Provides the ToolRegistry class and re-exports all 18 tools from backend.mcp.tools.
Ensures full backward compatibility with all existing orchestrator services and test suites.
"""

import logging
from typing import Dict, Any, List, Optional, Callable

# Re-export all 18 tools from modular MCP tools package
from ..mcp.tools import (
    list_conversation_files,
    list_available_images,
    get_file_metadata,
    extract_document_text,
    get_document_outline,
    search_document,
    get_page_content,
    get_document_images,
    describe_image,
    answer_question_about_image,
    extract_table,
    analyze_chart,
    compare_documents,
    generate_accessible_summary,
    generate_pdf_report,
    extract_image_text,
    text_to_speech,
    speech_to_text,
    register_all_mcp_tools,
    TOOL_CATEGORIES,
)
from ..mcp import mcp_server

logger = logging.getLogger("accessai.tools")


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any], func: Callable):
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func,
        }

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """
        Returns schemas formatted for LLM tool calling (OpenAI / Ollama format).
        """
        schemas = []
        for t in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                }
            })
        return schemas

    def execute(self, name: str, arguments: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a registered tool with argument validation and error containment.
        """
        tool = self.get_tool(name)
        if not tool:
            return {"success": False, "error": f"Tool '{name}' is not registered."}

        func = tool["func"]
        try:
            import inspect
            sig = inspect.signature(func)
            merged = dict(context or {})
            merged.update(arguments or {})

            filtered_args = {}
            for param_name, param in sig.parameters.items():
                if param_name in merged:
                    filtered_args[param_name] = merged[param_name]
                elif param.default is not inspect.Parameter.empty:
                    pass

            res = func(**filtered_args)
            return {"success": True, "result": res}
        except TypeError as te:
            logger.error("Tool '%s' invalid arguments: %s", name, te)
            return {"success": False, "error": f"Invalid arguments for {name}: {str(te)}"}
        except Exception as e:
            logger.error("Tool '%s' execution failed: %s", name, e)
            return {"success": False, "error": str(e)}


registry = ToolRegistry()

# Initialize registry with all tools from MCP
for t in mcp_server.list_tools():
    t_obj = mcp_server._tools.get(t["name"])
    if t_obj:
        registry.register(
            name=t["name"],
            description=t["description"],
            parameters=t["inputSchema"],
            func=t_obj["func"],
        )
