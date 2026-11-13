"""
LangChain callback handler bridging agent execution events to ActivityTracker and SSE stream.
"""

from typing import Dict, Any, List, Optional
from langchain_core.callbacks import BaseCallbackHandler

TOOL_TYPE_MAP = {
    "list_conversation_files": "catalog",
    "list_available_images": "catalog",
    "get_file_metadata": "read",
    "extract_document_text": "read",
    "get_document_outline": "outline",
    "search_document": "search",
    "get_page_content": "read",
    "get_document_images": "catalog",
    "describe_image": "inspect_image",
    "answer_question_about_image": "vision",
    "extract_table": "read",
    "analyze_chart": "diagram",
    "compare_documents": "read",
    "generate_accessible_summary": "outline",
    "generate_pdf_report": "report",
    "extract_image_text": "ocr",
    "text_to_speech": "speech",
    "speech_to_text": "read",
}

LABEL_MAP = {
    "list_conversation_files": "Listing conversation files",
    "list_available_images": "Cataloging uploaded images",
    "get_file_metadata": "Reading document metadata",
    "extract_document_text": "Extracting document text",
    "get_document_outline": "Reading document outline",
    "search_document": "Searching document pages",
    "get_page_content": "Reading page content",
    "get_document_images": "Extracting embedded images",
    "describe_image": "Analyzing visual scene",
    "answer_question_about_image": "Answering visual inquiry",
    "extract_table": "Extracting structured tables",
    "analyze_chart": "Analyzing technical diagram",
    "compare_documents": "Comparing document contents",
    "generate_accessible_summary": "Generating accessible summary",
    "generate_pdf_report": "Generating executive PDF report",
    "extract_image_text": "Running OCR on diagram",
    "text_to_speech": "Synthesizing voice audio",
    "speech_to_text": "Transcribing speech audio",
}


class ActivityTrackerCallbackHandler(BaseCallbackHandler):
    """
    Captures LangChain tool executions and token generation,
    updating ActivityTracker and dispatching real-time SSE events.
    """

    def __init__(self, tracker, event_sink: Optional[callable] = None):
        super().__init__()
        self.tracker = tracker
        self.event_sink = event_sink
        self.active_activities: Dict[str, Dict[str, Any]] = {}

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, *, run_id: Any, **kwargs):
        tool_name = serialized.get("name") or "tool"
        op_type = TOOL_TYPE_MAP.get(tool_name, "read")
        label = LABEL_MAP.get(tool_name, f"Running {tool_name.replace('_', ' ')}")

        metadata = {"tool": tool_name}
        if isinstance(input_str, str) and len(input_str) < 300:
            metadata["query"] = input_str

        act = self.tracker.start_tool(label=label, op_type=op_type, metadata=metadata)
        self.active_activities[str(run_id)] = act

    def on_tool_end(self, output: Any, *, run_id: Any, **kwargs):
        act = self.active_activities.pop(str(run_id), None)
        if not act:
            return

        detail = "Completed successfully"
        if isinstance(output, dict):
            if "total_pages" in output:
                detail = f"Extracted {output.get('total_pages', 1)} pages"
            elif "pages" in output:
                detail = f"Read {output.get('pages', 1)} pages"
            elif "outline" in output and isinstance(output["outline"], list):
                detail = f"Found {len(output['outline'])} sections"
        elif isinstance(output, list):
            detail = f"Found {len(output)} matches"

        self.tracker.complete_tool(act, detail=detail)

    def on_tool_error(self, error: BaseException, *, run_id: Any, **kwargs):
        act = self.active_activities.pop(str(run_id), None)
        if act:
            self.tracker.fail_tool(act, error=str(error))

    def on_llm_new_token(self, token: str, **kwargs):
        if self.event_sink and token:
            self.event_sink("token", {"text": token})
