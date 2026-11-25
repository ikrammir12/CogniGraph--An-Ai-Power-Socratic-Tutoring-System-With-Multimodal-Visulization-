"""
Stub brain — lets you run and demo the ENTIRE CogniGraph pipeline (ingestion,
RAG, router, visualization, UI) with zero API keys and zero GPU, before your
fine-tuned Llama-3-8B is ready.

It is deliberately simple: template-based question generation plus naive
keyword extraction. It is NOT meant to be pedagogically good — it exists so
every other component can be built, wired, and demoed against a working
brain. Swap `config.CONFIG.llm.backend` to "finetuned" once your LoRA
adapter is trained; see llm/finetuned_llm.py for exactly where your model
plugs in.
"""
from __future__ import annotations

import random
import re
from typing import List

from config import CONFIG
from llm.base import ChatMessage, LLMBrain, LLMResponse

_QUESTION_TEMPLATES = [
    "Before I answer — what do you already know about {topic}, and where does your understanding break down?",
    "What do you think would happen if {topic} worked differently than you expect? Why?",
    "Can you walk me through the steps you'd take to reason through {topic} yourself?",
    "What's the core assumption behind {topic} that everything else depends on?",
    "How does {topic} relate to something you've already learned in this course?",
    "If you had to explain {topic} to a classmate in one sentence, what would you say — and what's missing from that sentence?",
]

_TOPIC_STOPWORDS = {
    "what", "is", "the", "how", "does", "do", "a", "an", "of", "in", "on",
    "explain", "please", "can", "you", "tell", "me", "about", "why",
}


def _extract_topic(text: str) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text.lower())
    candidates = [w for w in words if w not in _TOPIC_STOPWORDS]
    if not candidates:
        return "this topic"
    # crude but effective: longest remaining word is usually the technical term
    return max(candidates, key=len)


def _count_prior_questions(messages: List[ChatMessage]) -> int:
    return sum(1 for m in messages if m.role == "assistant")


class StubSocraticLLM(LLMBrain):
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def generate(self, messages: List[ChatMessage]) -> LLMResponse:
        user_turns = [m for m in messages if m.role == "user"]
        latest_user = user_turns[-1].content if user_turns else ""
        # The system prompt carries the retrieved course context block; find it
        # so the stub can at least quote it back for the "final answer" turn.
        system_text = next((m.content for m in messages if m.role == "system"), "")

        topic = _extract_topic(latest_user)
        questions_asked = _count_prior_questions(messages)
        min_q = CONFIG.socratic.min_questions_before_answer

        wants_direct_answer = bool(
            re.search(r"just (tell|give) me|i give up|skip.*question", latest_user, re.I)
        )

        if questions_asked < min_q and not wants_direct_answer:
            template = self._rng.choice(_QUESTION_TEMPLATES)
            text = template.format(topic=topic)
            return LLMResponse(text=text, raw={"mode": "probing_question", "questions_asked": questions_asked})

        context_excerpt = self._extract_context_excerpt(system_text)
        text = (
            f"Good — you've worked through {topic} step by step, so here's the direct answer, "
            f"grounded in your course material:\n\n{context_excerpt}\n\n"
            f"[This is a placeholder answer from the stub brain. Swap "
            f"config.CONFIG.llm.backend to 'finetuned' to get a real, fine-tuned response here.]"
        )
        return LLMResponse(text=text, raw={"mode": "final_answer", "questions_asked": questions_asked})

    @staticmethod
    def _extract_context_excerpt(system_text: str, max_chars: int = 400) -> str:
        marker = "COURSE CONTEXT:"
        if marker in system_text:
            excerpt = system_text.split(marker, 1)[1].strip()
            return excerpt[:max_chars] + ("..." if len(excerpt) > max_chars else "")
        return "[No course context was retrieved for this query.]"
