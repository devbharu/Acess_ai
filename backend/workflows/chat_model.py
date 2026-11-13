"""
Custom LangChain Chat Model for AccessAI.
Integrates with Groq API and provides grounded fallback for multimodal accessibility.
"""

from typing import Any, List, Optional, Iterator
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, AIMessageChunk
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
from ..services.llm_service import LLMService


class AccessAIChatModel(BaseChatModel):
    """
    LangChain ChatModel that interfaces with AccessAI's LLMService via Groq.
    Supports token streaming and grounded answers.
    """
    model_name: str = "openai/gpt-oss-120b"
    temperature: float = 0.3
    evidence: Optional[List[dict]] = None
    images: Optional[List[dict]] = None

    @property
    def _llm_type(self) -> str:
        return "accessai_groq"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        hist = [{"role": "user" if m.type == "human" else "assistant", "content": m.content} for m in messages]
        full_text = ""
        settings = {
            "model": self.model_name,
            "temperature": self.temperature,
        }
        for chunk in LLMService.stream_chat(
            messages=hist,
            evidence=self.evidence or [],
            settings=settings,
            images=self.images or [],
        ):
            full_text += chunk
            if run_manager:
                run_manager.on_llm_new_token(chunk)

        message = AIMessage(content=full_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        hist = [{"role": "user" if m.type == "human" else "assistant", "content": m.content} for m in messages]
        settings = {
            "model": self.model_name,
            "temperature": self.temperature,
        }
        for chunk in LLMService.stream_chat(
            messages=hist,
            evidence=self.evidence or [],
            settings=settings,
            images=self.images or [],
        ):
            if run_manager:
                run_manager.on_llm_new_token(chunk)
            yield ChatGenerationChunk(message=AIMessageChunk(content=chunk))
