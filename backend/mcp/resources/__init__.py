"""
Registers standard MCP Resources on the AccessAI MCPServer.
"""

from .documents import get_document_resource
from .images import get_image_resource
from .artifacts import get_artifact_resource
from .metrics import get_metrics_resource


def register_all_mcp_resources(mcp_server):
    mcp_server.resource(
        uri="accessai://documents/{id}",
        name="Document Content & Outline",
        description="Reads extracted text, outline, and page count for a document ID.",
        mime_type="application/json",
    )(get_document_resource)

    mcp_server.resource(
        uri="accessai://images/{id}",
        name="Image Scene Description & OCR",
        description="Reads visual scene understanding and OCR for an image ID.",
        mime_type="application/json",
    )(get_image_resource)

    mcp_server.resource(
        uri="accessai://artifacts/{id}",
        name="Executive Summary Report Artifact",
        description="Reads generated report metadata and download link for an artifact ID.",
        mime_type="application/json",
    )(get_artifact_resource)

    mcp_server.resource(
        uri="accessai://metrics/summary",
        name="Evaluation Metrics Summary",
        description="System accuracy, latency, and benchmark scores.",
        mime_type="application/json",
    )(get_metrics_resource)
