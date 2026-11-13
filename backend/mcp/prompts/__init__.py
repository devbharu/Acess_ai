"""
Registers standard MCP Prompts on the AccessAI MCPServer.
"""

from .templates import (
    summarize_document_prompt,
    analyze_visual_diagram_prompt,
    compare_documents_prompt,
)


def register_all_mcp_prompts(mcp_server):
    mcp_server.prompt(
        name="summarize_document",
        description="Prompt to generate an accessible, screen-reader optimized summary.",
        arguments=[{"name": "file_id", "description": "ID of document", "required": True}],
    )(summarize_document_prompt)

    mcp_server.prompt(
        name="analyze_visual_diagram",
        description="Prompt to inspect technical schematics, flowcharts, or engineering figures.",
        arguments=[{"name": "file_id", "description": "ID of diagram/image", "required": True}],
    )(analyze_visual_diagram_prompt)

    mcp_server.prompt(
        name="compare_documents",
        description="Prompt to compare two documents across outlines and technical scope.",
        arguments=[
            {"name": "doc1", "description": "First document ID", "required": True},
            {"name": "doc2", "description": "Second document ID", "required": True},
        ],
    )(compare_documents_prompt)
