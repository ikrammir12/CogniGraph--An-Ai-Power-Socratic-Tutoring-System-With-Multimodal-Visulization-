"""
Brain Layer — abstract interface.

Every "brain" CogniGraph can use (stubbed, hosted API, or your own
fine-tuned Llama-3-8B + LoRA) implements this one method. The rest of the
codebase (socratic_engine, router, Streamlit UI) only ever talks to this
interface, so swapping brains is a one-line config change
(`config.CONFIG.llm.backend`) and never touches calling code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class ChatMessage:
    role: str      # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    text: str
    raw: dict = field(default_factory=dict)  # backend-specific extra info, for debugging


class LLMBrain(ABC):
    """Implement this to plug in a new model backend."""

    @abstractmethod
    def generate(self, messages: List[ChatMessage]) -> LLMResponse:
        """Given a chat history (system + user + assistant turns), return the
        next assistant turn. Implementations should NOT apply any Socratic
        logic themselves — that orchestration lives in
        llm.socratic_engine.SocraticEngine. A brain is just "text in, text out"."""
        raise NotImplementedError


def get_brain() -> LLMBrain:
    """Factory: returns the configured brain implementation.

    This is the single place that reads config.CONFIG.llm.backend, so this
    is the only function you need to look at (or extend) to wire in a new
    model.
    """
    from config import CONFIG

    backend = CONFIG.llm.backend

    if backend == "stub":
        from llm.stub_llm import StubSocraticLLM

        return StubSocraticLLM()

    if backend == "finetuned":
        from llm.finetuned_llm import FineTunedLlamaBrain

        return FineTunedLlamaBrain()

    if backend == "claude":
        from llm.hosted_llm import ClaudeBrain

        return ClaudeBrain()

    if backend == "openai":
        from llm.hosted_llm import OpenAIBrain

        return OpenAIBrain()

    raise ValueError(
        f"Unknown LLM backend '{backend}'. Expected one of: stub, finetuned, claude, openai."
    )
