"""Isolated CPU-only tests for quiz scoring and legacy history."""
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import storage


def main():
    original_path = storage.DB_PATH
    with tempfile.TemporaryDirectory(prefix="cognigraph-quiz-storage-") as temp:
        db_path = Path(temp) / "legacy.sqlite3"
        conn = sqlite3.connect(db_path)
        conn.executescript("""
        CREATE TABLE users(
          id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, created_at REAL NOT NULL);
        CREATE TABLE courses(
          id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT NOT NULL,
          description TEXT DEFAULT '', created_at REAL NOT NULL,
          UNIQUE(user_id,name));
        CREATE TABLE quiz_attempts(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
          topic TEXT NOT NULL, difficulty TEXT NOT NULL, question TEXT NOT NULL,
          options_json TEXT NOT NULL, correct_index INTEGER NOT NULL,
          selected_index INTEGER, is_correct INTEGER NOT NULL,
          explanation TEXT DEFAULT '', hints_used INTEGER DEFAULT 0,
          created_at REAL NOT NULL);
        INSERT INTO users VALUES(1, 'test-user', 'unused', 1.0);
        INSERT INTO courses VALUES(1, 1, 'Test Course', '', 1.0);
        """)
        conn.execute(
            """INSERT INTO quiz_attempts(
                user_id,course_id,topic,difficulty,question,options_json,
                correct_index,selected_index,is_correct,explanation,hints_used,created_at
            ) VALUES(1,1,?,?,?,?,?,?,?,?,?,?)""",
            (
                "Supervised Learning",
                "medium",
                "Which statement is directly supported by the course material about learning?",
                json.dumps([
                    "Labeled examples",
                    "A statement not supported by the supplied course material",
                    "A statement that changes the main relationship described in the material",
                    "A statement about an unrelated topic",
                ]),
                0, 1, 0, "Old generic fallback question.", 0, time.time() - 50,
            ),
        )
        conn.commit()
        conn.close()

        storage.DB_PATH = db_path
        try:
            storage.init_db()

            with storage._conn() as conn:
                columns = {
                    row["name"] for row in conn.execute("PRAGMA table_info(quiz_attempts)")
                }
                assert "quality_status" in columns
                legacy = conn.execute("SELECT * FROM quiz_attempts").fetchone()
                assert legacy["quality_status"] == "legacy_unverified"

            assert storage.quiz_stats(1, 1)["attempts"] == 0
            assert storage.quiz_stats(1, 1)["unverified_attempts"] == 1

            options = [
                "Labeled examples", "Unlabeled examples",
                "Only images", "Only charts"
            ]
            explanation = (
                "The course context says supervised learning uses labeled examples."
            )

            # Supplied Boolean is False, but matching indices must score correct.
            storage.record_quiz_attempt(
                1, 1, "Supervised Learning", "medium",
                "What does supervised learning use?", options, 0, 0, False,
                explanation,
            )
            # Supplied Boolean is True, but mismatched indices must score incorrect.
            storage.record_quiz_attempt(
                1, 1, "Supervised Learning", "medium",
                "What does supervised learning use?", options, 0, 1, True,
                explanation,
            )

            stats = storage.quiz_stats(1, 1)
            assert stats["attempts"] == 2, stats
            assert stats["correct"] == 1, stats
            assert stats["incorrect"] == 1, stats
            assert stats["unverified_attempts"] == 1, stats

            with storage._conn() as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM quiz_attempts"
                ).fetchone()[0]
                new_statuses = [
                    row["quality_status"]
                    for row in conn.execute(
                        "SELECT quality_status FROM quiz_attempts WHERE id > 1"
                    )
                ]
            assert count == 3, "Historical row must remain present"
            assert new_statuses == ["validated", "validated"], new_statuses

            print("PASS: old schema migrated; history preserved")
            print("PASS: caller-supplied correctness flag is ignored")
            print("PASS: unverified attempts excluded from statistics")
            print("All storage tests passed.")
        finally:
            storage.DB_PATH = original_path


if __name__ == "__main__":
    main()
