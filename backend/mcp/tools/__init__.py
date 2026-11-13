"""
MCP Tools Registry and Exports for AccessAI.
Exposes all 18 specialized multimodal, accessibility, and analysis tools.
"""

from typing import Dict, Any, List

# 1. Catalog tools
from .catalog_tools import (
    list_conversation_files,
    list_available_images,
)

# 2. Document tools
from .document_tools import (
    get_file_metadata,
    extract_document_text,
    get_document_outline,
    search_document,
    get_page_content,
)

# 3. Vision tools
from .vision_tools import (
    describe_image,
    answer_question_about_image,
    extract_image_text,
    get_document_images,
)

# 4. Analysis & report tools
from .analysis_tools import (
    extract_table,
    analyze_chart,
    compare_documents,
    generate_accessible_summary,
    generate_pdf_report,
)

# 5. Audio & speech tools
from .audio_tools import (
    text_to_speech,
    speech_to_text,
)

TOOL_CATEGORIES = {
    "list_conversation_files": "Catalog",
    "list_available_images": "Catalog",
    "get_file_metadata": "Document",
    "extract_document_text": "Document",
    "get_document_outline": "Document",
    "search_document": "Document",
    "get_page_content": "Document",
    "describe_image": "Vision",
    "answer_question_about_image": "Vision",
    "extract_image_text": "Vision",
    "get_document_images": "Vision",
    "extract_table": "Analysis",
    "analyze_chart": "Analysis",
    "compare_documents": "Analysis",
    "generate_accessible_summary": "Analysis",
    "generate_pdf_report": "Analysis",
    "text_to_speech": "Audio",
    "speech_to_text": "Audio",
}


def register_all_mcp_tools(mcp_server):
    """
    Registers all 18 tools with their exact schemas on the provided MCPServer.
    """
    mcp_server.register_tool(
        name="list_conversation_files",
        description="Lists all documents and images uploaded in the conversation or user library.",
        parameters={
            "type": "object",
            "properties": {
                "conversation_id": {"type": "string", "description": "Optional conversation ID to filter scoped uploads"},
            },
        },
        func=list_conversation_files,
    )

    mcp_server.register_tool(
        name="list_available_images",
        description="Catalogs all image attachments available with AI scene descriptions and OCR text.",
        parameters={
            "type": "object",
            "properties": {
                "conversation_id": {"type": "string", "description": "Optional conversation ID to filter scoped images"},
            },
        },
        func=list_available_images,
    )

    mcp_server.register_tool(
        name="get_file_metadata",
        description="Retrieves page counts, character length, OCR usage status, and file size for a file.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the target document or image"},
            },
            "required": ["file_id"],
        },
        func=get_file_metadata,
    )

    mcp_server.register_tool(
        name="extract_document_text",
        description="Extracts the raw textual content across all pages in a document.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the document"},
            },
            "required": ["file_id"],
        },
        func=extract_document_text,
    )

    mcp_server.register_tool(
        name="get_document_outline",
        description="Extracts native table of contents or prominent page heading blocks with page numbers.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the document"},
            },
            "required": ["file_id"],
        },
        func=get_document_outline,
    )

    mcp_server.register_tool(
        name="search_document",
        description="Performs high-precision keyword and semantic regex searches across all pages.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the document"},
                "query": {"type": "string", "description": "Search term or concept"},
            },
            "required": ["file_id", "query"],
        },
        func=search_document,
    )

    mcp_server.register_tool(
        name="get_page_content",
        description="Retrieves the exact text, OCR content, and metadata for a specific 1-indexed page.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the document"},
                "page_number": {"type": "integer", "description": "1-indexed page number"},
            },
            "required": ["file_id", "page_number"],
        },
        func=get_page_content,
    )

    mcp_server.register_tool(
        name="get_document_images",
        description="Extracts and catalogs raster images embedded within document pages.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the PDF document"},
                "page_number": {"type": "integer", "description": "Optional page number filter"},
            },
            "required": ["file_id"],
        },
        func=get_document_images,
    )

    mcp_server.register_tool(
        name="describe_image",
        description="Generates a comprehensive visual scene description combined with OCR text.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the image"},
            },
            "required": ["file_id"],
        },
        func=describe_image,
    )

    mcp_server.register_tool(
        name="answer_question_about_image",
        description="Answers visual questions about objects, colors, layout, and visible text.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the image"},
                "question": {"type": "string", "description": "Specific question about visual features"},
            },
            "required": ["file_id", "question"],
        },
        func=answer_question_about_image,
    )

    mcp_server.register_tool(
        name="extract_table",
        description="Parses structured table cells into clean, screen-reader-friendly Markdown tables.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the document"},
                "page_number": {"type": "integer", "description": "Optional page number"},
            },
            "required": ["file_id"],
        },
        func=extract_table,
    )

    mcp_server.register_tool(
        name="analyze_chart",
        description="Analyzes engineering schematics, charts, flow diagrams, and mechanical figures.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the image or document"},
                "page_number": {"type": "integer", "description": "Optional page number if document"},
            },
            "required": ["file_id"],
        },
        func=analyze_chart,
    )

    mcp_server.register_tool(
        name="compare_documents",
        description="Compares thematic scope, headings, mechanical concepts, and document differences.",
        parameters={
            "type": "object",
            "properties": {
                "file_id_1": {"type": "string", "description": "ID of the first document"},
                "file_id_2": {"type": "string", "description": "ID of the second document"},
            },
            "required": ["file_id_1", "file_id_2"],
        },
        func=compare_documents,
    )

    mcp_server.register_tool(
        name="generate_accessible_summary",
        description="Creates an accessible, structured, screen-reader-optimized document overview.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the document or image"},
            },
            "required": ["file_id"],
        },
        func=generate_accessible_summary,
    )

    mcp_server.register_tool(
        name="generate_pdf_report",
        description="Compiles an executive summary PDF using ReportLab and delivers it as an artifact.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the source document"},
                "focus_topic": {"type": "string", "description": "Optional specific focus topic for summary"},
            },
            "required": ["file_id"],
        },
        func=generate_pdf_report,
    )

    mcp_server.register_tool(
        name="extract_image_text",
        description="Extracts text from an image or screenshot preserving top-to-bottom reading order.",
        parameters={
            "type": "object",
            "properties": {
                "file_id": {"type": "string", "description": "ID of the image"},
            },
            "required": ["file_id"],
        },
        func=extract_image_text,
    )

    mcp_server.register_tool(
        name="text_to_speech",
        description="Synthesizes text into high-fidelity 16-bit PCM WAV audio.",
        parameters={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to read aloud"},
                "voice": {"type": "string", "description": "Voice profile name"},
                "speed": {"type": "number", "description": "Speech speed multiplier"},
            },
            "required": ["text"],
        },
        func=text_to_speech,
    )

    mcp_server.register_tool(
        name="speech_to_text",
        description="Transcribes spoken audio recordings into text using Faster-Whisper.",
        parameters={
            "type": "object",
            "properties": {
                "audio_id": {"type": "string", "description": "ID of the uploaded audio record"},
                "language": {"type": "string", "description": "Language code or auto"},
            },
            "required": ["audio_id"],
        },
        func=speech_to_text,
    )
