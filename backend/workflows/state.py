"""
State definitions and context bridge for LangChain agent workflows.
"""

from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from ..services.context import ContextResolver, ConversationState


def build_langchain_messages(history_messages: List[Dict[str, str]], user_message: str) -> List[BaseMessage]:
    """Converts raw dictionary history into LangChain messages."""
    lc_messages = []
    for m in history_messages:
        role = m.get("role")
        content = m.get("content") or ""
        if role == "user":
            lc_messages.append(HumanMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))

    if user_message and (not lc_messages or lc_messages[-1].content != user_message):
        lc_messages.append(HumanMessage(content=user_message))

    return lc_messages
