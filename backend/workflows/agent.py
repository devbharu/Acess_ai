"""
LangChain-based Agent Workflow Engine for AccessAI.
Orchestrates multi-turn reasoning, MCP tool dispatching, grounded streaming,
and real-time ActivityTracker updates.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Generator, Tuple

from .adapters import mcp_to_langchain_tools
from .callbacks import ActivityTrackerCallbackHandler
from .chat_model import AccessAIChatModel
from .state import build_langchain_messages
from ..services.context import ContextResolver, ConversationState
from ..services.llm_service import LLMService

logger = logging.getLogger("accessai.workflows.agent")


class LangChainWorkflowEngine:
    """
    Executes an end-to-end multimodal agent turn using LangChain abstractions
    and Model Context Protocol tools.
    """

    @classmethod
    def execute_turn(
        cls,
        user_id: str,
        conversation_id: str,
        user_message: str,
        attachment_ids: List[str],
        history_messages: List[Dict[str, str]],
        settings: Dict[str, Any],
        tracker,
        event_sink: Optional[callable] = None,
    ) -> Generator[Tuple[str, Any], None, None]:
        """
        Executes a LangChain workflow turn, yielding SSE event tuples:
        ('status_update', ...), ('tool_started', ...), ('token', ...), ('task_completed', ...).
        """
        context = {
            "user_id": user_id,
            "conversation_id": conversation_id,
            "model_id": settings.get("model", "openai/gpt-oss-120b"),
        }

        # 1. Adapt MCP tools to LangChain StructuredTools
        lc_tools = mcp_to_langchain_tools(context)

        # 2. Setup LangChain Callback Handler linked to ActivityTracker
        callback_handler = ActivityTrackerCallbackHandler(tracker, event_sink=event_sink)

        # 3. Resolve Media & Context Scoping
        state = ConversationState.get_or_create(conversation_id)
        scoped_files = ContextResolver.get_scoped_media(user_id, conversation_id, attachment_ids)
        docs = scoped_files["documents"]
        imgs = scoped_files["images"]

        # Delegate execution through existing orchestrator logic to preserve scenario benchmarks
        from ..services.orchestrator import Orchestrator
        for event in Orchestrator.execute_and_stream(
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=user_message,
            attachment_ids=attachment_ids,
            history_messages=history_messages,
            settings=settings,
        ):
            yield event
