"""
Brain Layer — LangChain adapter.

Wraps our model-agnostic LLMBrain (stub / finetuned / claude / openai — see
llm/base.py) as a LangChain BaseChatModel, so LangChain owns the actual
orchestration between the LLM, the vector store, and the prompt — as your
proposal's Backend section specifies — instead of us hand-rolling message
lists and function calls.

This is a thin adapter, not a new brain: swapping COGNIGRAPH_LLM_BACKEND
still changes which model actually runs. This file just lets LangChain's
LCEL (`prompt | model`) call whatever that brain is.
"""
from __future__ import annotations

from typing import Any, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from llm.base import ChatMessage as CGMessage
from llm.base import LLMBrain, get_brain


def _to_cg_role(message: BaseMessage) -> str:
    if isinstance(message, SystemMessage):
        return "system"
    if isinstance(message, AIMessage):
        return "assistant"
    return "user"  # HumanMessage and any generic fallback


class CogniGraphChatModel(BaseChatModel):
    """LangChain BaseChatModel backed by whichever LLMBrain is configured."""

    brain: Any = Field(default=None, exclude=True)

    def __init__(self, brain: Optional[LLMBrain] = None, **kwargs: Any):
        super().__init__(brain=brain or get_brain(), **kwargs)

    @property
    def _llm_type(self) -> str:
        return "cognigraph-brain"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        cg_messages = [CGMessage(role=_to_cg_role(m), content=m.content) for m in messages]
        response = self.brain.generate(cg_messages)
        generation = ChatGeneration(message=AIMessage(content=response.text))
        return ChatResult(generations=[generation])
