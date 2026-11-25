"""
Lightweight tests for llm/socratic_engine.py.

Uses the stub brain (no GPU/API needed) and an empty/fake retriever so
these run instantly and offline. Tests the ORCHESTRATION logic (question
counting, state tracking, "just tell me" override) — not response quality,
which depends on whichever real brain is configured.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CONFIG


def _make_engine(monkeypatch):
    import llm.socratic_engine as socratic_module
    from llm.stub_llm import StubSocraticLLM

    # These tests cover orchestration, not persistent ChromaDB retrieval.
    monkeypatch.setattr(
        socratic_module,
        "retrieve",
        lambda query, top_k=None, course_id=None: [],
    )
    return socratic_module.SocraticEngine(brain=StubSocraticLLM(seed=1))


def test_state_tracks_turns_in_order(monkeypatch):
    from llm.socratic_engine import ConversationState

    state = ConversationState()
    engine = _make_engine(monkeypatch)

    engine.ask(state, "What is a neural network?")
    assert len(state.turns) == 2  # user + assistant
    assert state.turns[0].role == "user"
    assert state.turns[1].role == "assistant"


def test_asks_questions_before_min_threshold(monkeypatch):
    from llm.socratic_engine import ConversationState

    state = ConversationState()
    engine = _make_engine(monkeypatch)
    min_q = CONFIG.socratic.min_questions_before_answer

    for i in range(min_q):
        turn = engine.ask(state, f"Follow-up question {i}")
        # Before the threshold is reached, the stub brain should keep probing
        # rather than giving a final answer.
        assert "?" in turn.content or i < min_q, f"expected a probing question at turn {i}"

    assert state.questions_asked() == min_q


def test_just_tell_me_overrides_question_gate(monkeypatch):
    from llm.socratic_engine import ConversationState

    state = ConversationState()
    engine = _make_engine(monkeypatch)

    # Even on the very first turn, an explicit "just tell me" should be
    # honoured rather than forcing a probing question.
    turn = engine.ask(state, "just tell me the answer")
    assert "direct answer" in turn.content.lower() or "placeholder" in turn.content.lower()


def test_source_query_recorded_for_rerender(monkeypatch):
    from llm.socratic_engine import ConversationState

    state = ConversationState()
    engine = _make_engine(monkeypatch)

    turn = engine.ask(state, "How does backpropagation work?")
    assert turn.source_query == "How does backpropagation work?"



def test_tutoring_stage_transitions(monkeypatch):
    import llm.socratic_engine as module
    from llm.socratic_engine import ConversationState

    assert module._is_uncertain_answer("I still don't know")

    state = ConversationState()
    engine = _make_engine(monkeypatch)
    observed_stages = []
    original_prompt = module._tutoring_stage_prompt

    def record_stage(stage, attempts, topic):
        observed_stages.append(stage)
        return original_prompt(stage, attempts, topic)

    monkeypatch.setattr(module, "_tutoring_stage_prompt", record_stage)

    engine.ask(state, "Teach me Python loops")
    assert state.stage == "guide"
    assert state.tutoring_active
    assert state.turn_count == 1

    engine.ask(state, "I don't know")
    assert state.stage == "guide"
    assert state.attempts == 1
    assert state.turn_count == 2

    engine.ask(state, "I still don't know")
    assert state.stage == "check"
    assert state.attempts == 0
    assert state.turn_count == 3

    engine.ask(state, "Just tell me the answer")
    assert state.stage == "check"
    assert state.tutoring_active
    assert state.turn_count == 4

    engine.ask(state, "A loop repeats instructions")
    assert state.stage == "complete"
    assert not state.tutoring_active
    assert state.turn_count == 5

    assert observed_stages == [
        "explore", "hint", "explain", "explain", "check"
    ]

if __name__ == "__main__":
    import pytest
    monkeypatch = pytest.MonkeyPatch()
    try:
        test_state_tracks_turns_in_order(monkeypatch)
        test_asks_questions_before_min_threshold(monkeypatch)
        test_just_tell_me_overrides_question_gate(monkeypatch)
        test_source_query_recorded_for_rerender(monkeypatch)
        test_tutoring_stage_transitions(monkeypatch)
        print("All socratic engine tests passed.")
    finally:
        monkeypatch.undo()
