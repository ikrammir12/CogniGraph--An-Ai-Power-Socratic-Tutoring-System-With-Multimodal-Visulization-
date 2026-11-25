"""CPU-only regression tests for hybrid quiz context selection."""
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import api_main


class HybridQuizTests(unittest.TestCase):
    def setUp(self):
        self.pdf = SimpleNamespace(
            text="PDF passage: logistic regression estimates probabilities.",
            source="course.pdf",
            page=2,
            similarity=0.91,
        )
        self.chat_text = (
            "[Conversation: Logistic regression discussion] "
            "USER: Can you explain the sigmoid function?"
        )

    def call_quiz(self, topic, chat_text=None):
        captured = {}

        def fake_generate(brain, requested_topic, supplied_context,
                          difficulty, previous_questions):
            captured.update(
                topic=requested_topic,
                context=supplied_context,
                difficulty=difficulty,
                previous=list(previous_questions),
            )
            return SimpleNamespace(
                to_dict=lambda: {
                    "question": "What does the sigmoid function produce?",
                    "options": ["A probability", "A filename", "A page number", "A PDF"],
                    "correct_index": 0,
                    "explanation": "The supplied context supports this answer.",
                    "topic": requested_topic,
                    "difficulty": difficulty,
                    "hints": ["Hint one", "Hint two", "Hint three"],
                },
                correct_index=0,
                explanation="The supplied context supports this answer.",
            )

        with ExitStack() as stack:
            stack.enter_context(patch.object(api_main, "check_course"))
            retrieve = stack.enter_context(
                patch.object(api_main, "retrieve", return_value=[self.pdf])
            )
            sample = stack.enter_context(
                patch.object(api_main, "sample_course_context", return_value=[self.pdf])
            )
            chat_context = stack.enter_context(
                patch.object(
                    api_main, "recent_course_chat_context",
                    return_value=self.chat_text if chat_text is None else chat_text,
                )
            )
            stack.enter_context(
                patch.object(
                    api_main, "engine",
                    return_value=SimpleNamespace(
                        chat_model=SimpleNamespace(brain=object())
                    ),
                )
            )
            stack.enter_context(
                patch.object(api_main, "generate_quiz_question",
                             side_effect=fake_generate)
            )
            stack.enter_context(
                patch.object(api_main.storage, "adaptive_difficulty",
                             return_value="medium")
            )
            stack.enter_context(
                patch.object(api_main.storage, "recent_quiz_attempts",
                             return_value=[])
            )
            stack.enter_context(
                patch.object(api_main.storage, "save_pending_quiz_question")
            )
            stack.enter_context(
                patch.object(api_main.storage, "quiz_stats",
                             return_value={"attempts": 0, "correct": 0})
            )

            response = api_main.quiz_question(
                api_main.QuizStart(course_id=42, topic=topic),
                user={"id": 17},
            )

        return response, captured, retrieve, sample, chat_context

    def test_explicit_topic_is_pdf_only(self):
        response, captured, retrieve, sample, chat_context = self.call_quiz(
            "Logistic Regression"
        )
        self.assertEqual(captured["topic"], "Logistic Regression")
        self.assertIn("PDF passage", captured["context"])
        self.assertNotIn("Conversation:", captured["context"])
        retrieve.assert_called_once_with(
            "Logistic Regression", course_id=42
        )
        sample.assert_not_called()
        chat_context.assert_not_called()
        self.assertNotIn("correct_index", response["question"])
        print("PASS: explicit topic uses PDF retrieval only")

    def test_blank_topic_combines_pdf_and_chat(self):
        response, captured, retrieve, sample, chat_context = self.call_quiz("")
        self.assertEqual(captured["topic"], "course overview")
        self.assertIn("COURSE PDF MATERIAL", captured["context"])
        self.assertIn("PDF passage", captured["context"])
        self.assertIn("RECENT SOCRATIC TUTOR CHAT HISTORY", captured["context"])
        self.assertIn("sigmoid function", captured["context"])
        sample.assert_called_once_with(42, limit=5)
        retrieve.assert_not_called()
        chat_context.assert_called_once_with(
            17, 42,
            max_conversations=3,
            max_messages=6,
            max_chars=1800,
        )
        self.assertNotIn("correct_index", response["question"])
        print("PASS: blank topic combines course PDF and chat context")

    def test_chat_context_is_bounded_and_course_scoped(self):
        conversations = [{"id": 9, "title": "Revision"}]
        messages = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i} " + ("x" * 100),
                "created_at": float(i),
            }
            for i in range(20)
        ]
        with ExitStack() as stack:
            list_chats = stack.enter_context(
                patch.object(api_main.storage, "list_conversations",
                             return_value=conversations)
            )
            list_messages = stack.enter_context(
                patch.object(api_main.storage, "list_messages",
                             return_value=messages)
            )
            context = api_main.recent_course_chat_context(
                17, 42, max_conversations=5,
                max_messages=4, max_chars=500,
            )

        list_chats.assert_called_once_with(17, 42)
        list_messages.assert_called_once_with(9)
        self.assertLessEqual(len(context), 500)
        self.assertLessEqual(len(context.splitlines()), 4)
        self.assertIn("Conversation: Revision", context)
        print("PASS: chat context is bounded and scoped to the requested course")

    def test_no_chat_history_is_allowed(self):
        response, captured, _, _, _ = self.call_quiz("", chat_text="")
        self.assertTrue(response["question"]["question"])
        self.assertIn("No recent tutor chat history is available.", captured["context"])
        self.assertNotIn("RECENT SOCRATIC TUTOR CHAT HISTORY", captured["context"])
        print("PASS: no chat history falls back to PDF context")


if __name__ == "__main__":
    unittest.main(verbosity=2)
