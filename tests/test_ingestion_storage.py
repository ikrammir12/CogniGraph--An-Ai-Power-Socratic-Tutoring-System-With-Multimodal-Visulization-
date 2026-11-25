"""Focused tests for safe ingestion metadata migrations and persistent job status."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import storage


def main() -> None:
    original_db = storage.DB_PATH
    original_saved = storage.SAVED_DIR
    with tempfile.TemporaryDirectory(prefix="cognigraph-ingestion-test-") as tmp:
        root = Path(tmp)
        storage.DB_PATH = root / "cognigraph.db"
        storage.SAVED_DIR = root / "saved_visualizations"
        storage.SAVED_DIR.mkdir()

        # Simulate a pre-patch database: source table has no hash column or job table.
        with sqlite3.connect(storage.DB_PATH) as conn:
            conn.executescript("""
                PRAGMA foreign_keys=ON;
                CREATE TABLE users(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE courses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    UNIQUE(user_id, name),
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE TABLE course_sources(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    chunks INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    UNIQUE(course_id, filename),
                    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
                );
                INSERT INTO users(username,password_hash,created_at) VALUES('test','hash',1);
                INSERT INTO courses(user_id,name,description,created_at) VALUES(1,'Course','',1);
                INSERT INTO course_sources(course_id,filename,chunks,created_at)
                    VALUES(1,'existing.pdf',42,1);
            """)

        storage.init_db()
        with sqlite3.connect(storage.DB_PATH) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(course_sources)")}
            job_table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ingestion_jobs'"
            ).fetchone()
            source = conn.execute(
                "SELECT filename,chunks FROM course_sources WHERE id=1"
            ).fetchone()
        assert "content_sha256" in columns
        assert job_table is not None
        assert source == ("existing.pdf", 42), source

        storage.set_source_content_hash(1, 1, "a" * 64)
        assert storage.get_source_by_hash(1, "a" * 64)["filename"] == "existing.pdf"

        job = storage.create_ingestion_job("job-1", 1, "new.pdf", "b" * 64)
        assert job and job["status"] == "queued"
        assert storage.get_active_ingestion_job(1, "b" * 64)["id"] == "job-1"
        storage.update_ingestion_job("job-1", status="processing", stage="Embedding chunks")
        assert storage.get_ingestion_job("job-1", 1)["status"] == "processing"
        storage.update_ingestion_job(
            "job-1", status="succeeded", stage="Indexed successfully", chunks=10, pages=3
        )
        completed = storage.get_ingestion_job("job-1", 1)
        assert completed["status"] == "succeeded"
        assert completed["chunks"] == 10 and completed["pages"] == 3

        job2 = storage.create_ingestion_job("job-2", 1, "retry.pdf", "c" * 64)
        assert job2 and job2["status"] == "queued"
        storage.fail_interrupted_ingestion_jobs()
        assert storage.get_ingestion_job("job-2", 1)["status"] == "failed"

    storage.DB_PATH = original_db
    storage.SAVED_DIR = original_saved
    print("PASS: migration preserves old source rows; hash lookup and ingestion-job lifecycle work.")


if __name__ == "__main__":
    main()
