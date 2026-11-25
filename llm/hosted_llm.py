"""
Optional hosted-API brains. These are NOT part of your proposal's
architecture (which specifies a locally fine-tuned Llama-3-8B) — they exist
purely as a higher-quality stand-in than llm/stub_llm.py if you want more
convincing demo responses before your LoRA adapter is trained. They are
never required: the app runs fine with backend="stub" and no API keys.
"""
from __future__ import annotations

import os
from typing import List

from config import CONFIG
from llm.base import ChatMessage, LLMBrain, LLMResponse


class ClaudeBrain(LLMBrain):
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Set ANTHROPIC_API_KEY to use the 'claude' backend.")
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)

    def generate(self, messages: List[ChatMessage]) -> LLMResponse:
        system = next((m.content for m in messages if m.role == "system"), None)
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        response = self._client.messages.create(
            model=CONFIG.llm.claude_model,
            max_tokens=CONFIG.llm.max_new_tokens,
            temperature=CONFIG.llm.temperature,
            system=system,
            messages=turns,
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMResponse(text=text, raw={"backend": "claude"})


class OpenAIBrain(LLMBrain):
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Set OPENAI_API_KEY to use the 'openai' backend.")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)

    def generate(self, messages: List[ChatMessage]) -> LLMResponse:
        """Generate one answer through the OpenAI Responses API.

        System instructions are kept separate from conversation input, and the
        model ID/reasoning effort are controlled through config environment vars.
        """
        system_parts = [m.content for m in messages if m.role == "system" and m.content]
        input_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in {"user", "assistant"} and m.content
        ]

        kwargs = {
            "model": CONFIG.llm.openai_model,
            "input": input_messages,
            "max_output_tokens": (
                max(CONFIG.llm.max_new_tokens, 4096)
                if any("revision coach" in part.casefold()
                       for part in system_parts)
                else CONFIG.llm.max_new_tokens
            ),
        }
        if system_parts:
            kwargs["instructions"] = "\n\n".join(system_parts)

        effort = CONFIG.llm.openai_reasoning_effort.strip().lower()
        if effort in {"low", "medium", "high", "xhigh", "max"}:
            kwargs["reasoning"] = {"effort": effort}

        response = self._client.responses.create(**kwargs)
        text = str(getattr(response, "output_text", "") or "").strip()
        usage = getattr(response, "usage", None)
        usage_data = usage.model_dump() if usage is not None and hasattr(usage, "model_dump") else None
        return LLMResponse(
            text=text,
            raw={
                "backend": "openai",
                "model": CONFIG.llm.openai_model,
                "usage": usage_data,
            },
        )
