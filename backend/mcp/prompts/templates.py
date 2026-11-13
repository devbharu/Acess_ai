"""
Standard accessibility prompt templates for AccessAI MCP Server.
"""

from typing import Dict, Any, List


def summarize_document_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    file_id = args.get("file_id", "target_doc")
    return {
        "description": "Generate an accessible, screen-reader optimized summary.",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"Please analyze document {file_id}. First use get_document_outline to inspect its "
                        "sections, then generate an accessible executive summary preserving key facts, "
                        "tables, and citations."
                    ),
                },
            }
        ],
    }


def analyze_visual_diagram_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    file_id = args.get("file_id", "target_image")
    return {
        "description": "Analyze technical diagrams, flowcharts, or engineering figures.",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"Please inspect {file_id}. Use describe_image and analyze_chart to detail "
                        "every labeled component, flow direction, and numerical trend present."
                    ),
                },
            }
        ],
    }


def compare_documents_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    doc1 = args.get("doc1", "doc_1")
    doc2 = args.get("doc2", "doc_2")
    return {
        "description": "Compare structural and semantic differences between two documents.",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"Compare {doc1} and {doc2} using compare_documents. Outline their shared topics, "
                        "unique contributions, and differing methodologies."
                    ),
                },
            }
        ],
    }
