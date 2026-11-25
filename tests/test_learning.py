"""CPU-only tests for CogniGraph quiz generation."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from learning import generate_quiz_question
from llm.base import ChatMessage, LLMBrain, LLMResponse

VALID = {
    "question": "What does supervised learning use?",
    "options": [
        "Labeled examples",
        "Unlabeled examples",
        "Only images",
        "Only charts",
    ],
    "correct_index": 0,
    "explanation": (
        "The course context says supervised learning uses labeled examples."
    ),
    "topic": "Supervised Learning",
    "difficulty": "medium",
    "hints": [
        "Look for the kind of examples mentioned in the notes.",
        "Think about whether the examples have known target outputs.",
        "Choose the option that mentions labels.",
    ],
}


class SequenceBrain(LLMBrain):
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def generate(self, messages: list[ChatMessage]) -> LLMResponse:
        self.calls += 1
        output = self.outputs.pop(0)
        if isinstance(output, dict):
            output = json.dumps(output)
        return LLMResponse(output)


CONTEXT = "Supervised learning uses labeled examples."


def generate(brain, context=CONTEXT):
    return generate_quiz_question(
        brain, "Supervised Learning", context, "medium"
    )


def expect_rejected(payload, context=CONTEXT):
    brain = SequenceBrain([payload] * 5)
    try:
        generate(brain, context)
    except ValueError:
        assert brain.calls == 5
        return
    raise AssertionError("Invalid question must be rejected after retry.")


def main():
    q = generate(SequenceBrain([VALID]))
    assert q.correct_index == 0
    assert len(q.options) == 4
    assert len(q.hints) == 3
    print("PASS: valid question accepted")

    brain = SequenceBrain([
        "What is the primary motivation for attackers to take deliberate actions?",
        VALID,
    ])
    q = generate(brain)
    assert brain.calls == 2 and q.correct_index == 0
    print("PASS: plain text output retried")

    wrapped = SequenceBrain(["Here is the question:\\n```json\\n"
                             + json.dumps(VALID) + "\\n```"])
    assert generate(wrapped).correct_index == 0
    print("PASS: JSON inside a code fence extracted")

    duplicate = dict(VALID)
    duplicate["options"] = [
        "Labeled examples", "labeled examples.", "Only images", "Only charts"
    ]
    expect_rejected(duplicate)
    print("PASS: duplicate options rejected")

    copied = (
        "This long course passage explains a relationship among concepts and "
        "provides details that students should understand thoroughly."
    )
    assert len(copied) >= 90
    passage = dict(VALID)
    passage["options"] = [
        "Labeled examples", copied, "Only images", "Only charts"
    ]
    expect_rejected(passage, CONTEXT + " " + copied)
    print("PASS: copied passage rejected")

    long_option = dict(VALID)
    long_option["options"] = ["x" * 161, "Unlabeled examples", "Only images", "Only charts"]
    expect_rejected(long_option)
    print("PASS: oversized answer rejected")

    bad_key = dict(VALID)
    bad_key["correct_index"] = True
    expect_rejected(bad_key)
    print("PASS: Boolean answer index rejected")

    print("All quiz-generation tests passed.")


if __name__ == "__main__":
    main()
