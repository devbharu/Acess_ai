"""
Adapts AccessAI MCP tools into LangChain StructuredTool instances.
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import StructuredTool
from ..mcp import mcp_server


def mcp_to_langchain_tools(context: Dict[str, Any]) -> List[StructuredTool]:
    """
    Converts registered MCP tools into LangChain StructuredTools,
    injecting runtime user, conversation, and model context.
    """
    langchain_tools = []
    for tool_dict in mcp_server.list_tools():
        name = tool_dict["name"]
        description = tool_dict["description"]
        schema = tool_dict.get("inputSchema") or {}

        def make_wrapper(tool_name: str):
            def tool_wrapper(**kwargs):
                res = mcp_server.execute_tool(tool_name, kwargs, context=context)
                if res.get("isError"):
                    return f"Error executing {tool_name}: {res.get('error')}"
                return res.get("result")
            return tool_wrapper

        wrapped_fn = make_wrapper(name)
        wrapped_fn.__name__ = name
        wrapped_fn.__doc__ = description

        try:
            lc_tool = StructuredTool.from_function(
                func=wrapped_fn,
                name=name,
                description=description,
            )
            langchain_tools.append(lc_tool)
        except Exception:
            # Fallback for dynamic signatures
            pass

    return langchain_tools
