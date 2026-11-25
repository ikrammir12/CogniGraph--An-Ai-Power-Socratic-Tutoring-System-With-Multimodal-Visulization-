
"""CogniGraph persistence layer for local auth, courses, chats, saves and progress."""
from __future__ import annotations
import hashlib, hmac, json, os, secrets, sqlite3, time
from pathlib import Path
from typing import Any

from config import DATA_DIR

DB_PATH = DATA_DIR / "cognigraph.db"
SAVED_DIR = DATA_DIR / "saved_visualizations"
SAVED_DIR.mkdir(parents=True, exist_ok=True)

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, created_at REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS courses(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
          name TEXT NOT NULL, description TEXT DEFAULT '', created_at REAL NOT NULL,
          UNIQUE(user_id,name), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS course_sources(
          id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL,
          filename TEXT NOT NULL, chunks INTEGER DEFAULT 0, created_at REAL NOT NULL,
          content_sha256 TEXT,
          UNIQUE(course_id,filename), FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS ingestion_jobs(
          id TEXT PRIMARY KEY, course_id INTEGER NOT NULL, filename TEXT NOT NULL,
          content_sha256 TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'queued',
          stage TEXT NOT NULL DEFAULT 'Queued for indexing', chunks INTEGER NOT NULL DEFAULT 0,
          pages INTEGER NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '',
          created_at REAL NOT NULL, updated_at REAL NOT NULL,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS conversations(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, course_id INTEGER,
          title TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL,
          chat_mode TEXT NOT NULL DEFAULT 'socratic',
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS messages(
          id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL,
          role TEXT NOT NULL, content TEXT NOT NULL, mode TEXT DEFAULT 'text',
          source_query TEXT DEFAULT '', context_json TEXT DEFAULT '[]', created_at REAL NOT NULL,
          FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS visualizations(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
          conversation_id INTEGER, kind TEXT NOT NULL, title TEXT NOT NULL, query TEXT NOT NULL,
          file_path TEXT, source_text TEXT, created_at REAL NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE,
          FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE SET NULL);
        CREATE TABLE IF NOT EXISTS activity(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
          event_type TEXT NOT NULL, detail TEXT DEFAULT '', created_at REAL NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS quiz_attempts(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, course_id INTEGER NOT NULL,
          topic TEXT NOT NULL, difficulty TEXT NOT NULL, question TEXT NOT NULL,
          options_json TEXT NOT NULL, correct_index INTEGER NOT NULL, selected_index INTEGER,
          is_correct INTEGER NOT NULL, explanation TEXT DEFAULT '', hints_used INTEGER DEFAULT 0,
          created_at REAL NOT NULL,
          quality_status TEXT NOT NULL DEFAULT 'legacy_unverified',
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS pending_quiz_questions(
          question_id TEXT PRIMARY KEY,
          user_id INTEGER NOT NULL,
          course_id INTEGER NOT NULL,
          topic TEXT NOT NULL,
          difficulty TEXT NOT NULL,
          question TEXT NOT NULL,
          options_json TEXT NOT NULL,
          correct_index INTEGER NOT NULL,
          explanation TEXT DEFAULT '',
          created_at REAL NOT NULL,
          answered_at REAL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS idx_pending_quiz_user_course
          ON pending_quiz_questions(user_id,course_id,created_at);
        CREATE TABLE IF NOT EXISTS sessions(
          token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
          created_at REAL NOT NULL, expires_at REAL NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS study_plans(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          course_id INTEGER NOT NULL,
          week_start TEXT NOT NULL,
          plan_json TEXT NOT NULL,
          created_at REAL NOT NULL,
          updated_at REAL NOT NULL,
          UNIQUE(user_id, course_id, week_start),
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_study_plans_user_course_week
          ON study_plans(user_id, course_id, week_start);
        CREATE TABLE IF NOT EXISTS study_session_progress(
          user_id INTEGER NOT NULL,
          course_id INTEGER NOT NULL,
          week_start TEXT NOT NULL,
          session_date TEXT NOT NULL,
          completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
          updated_at REAL NOT NULL,
          PRIMARY KEY(user_id, course_id, week_start, session_date),
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
        """)
        source_columns = {
            row["name"] for row in c.execute("PRAGMA table_info(course_sources)")
        }
        if "content_sha256" not in source_columns:
            c.execute("ALTER TABLE course_sources ADD COLUMN content_sha256 TEXT")
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_course_sources_hash "
            "ON course_sources(course_id, content_sha256)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_course_updated "
            "ON ingestion_jobs(course_id, updated_at DESC)"
        )
        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_ingestion_jobs_active_hash "
            "ON ingestion_jobs(course_id, content_sha256) "
            "WHERE status IN ('queued', 'processing')"
        )
        quiz_columns = {
            row["name"] for row in c.execute("PRAGMA table_info(quiz_attempts)")
        }
        if "quality_status" not in quiz_columns:
            c.execute(
                "ALTER TABLE quiz_attempts ADD COLUMN "
                "quality_status TEXT NOT NULL DEFAULT 'legacy_unverified'"
            )
        c.execute("""
        CREATE TABLE IF NOT EXISTS revision_sheets(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          course_id INTEGER NOT NULL,
          request_topic TEXT NOT NULL DEFAULT '',
          content TEXT NOT NULL,
          sources_json TEXT NOT NULL DEFAULT '[]',
          topics_json TEXT NOT NULL DEFAULT '[]',
          created_at REAL NOT NULL,
          FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        )
        """)
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_revision_sheets_user_course "
            "ON revision_sheets(user_id, course_id, created_at DESC)"
        )
        c.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_reminder_preferences(
              user_id INTEGER PRIMARY KEY,
              phone_number TEXT NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
              timezone TEXT NOT NULL DEFAULT 'Asia/Karachi',
              reminder_time TEXT NOT NULL DEFAULT '19:00',
              consent_at REAL,
              updated_at REAL NOT NULL,
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_reminder_deliveries(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              course_id INTEGER NOT NULL,
              week_start TEXT NOT NULL,
              session_date TEXT NOT NULL,
              status TEXT NOT NULL
                CHECK(status IN ('processing','sent','failed')),
              attempt_count INTEGER NOT NULL DEFAULT 1,
              last_error TEXT NOT NULL DEFAULT '',
              created_at REAL NOT NULL,
              updated_at REAL NOT NULL,
              sent_at REAL,
              UNIQUE(user_id, course_id, week_start, session_date),
              FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
              FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_whatsapp_delivery_status
            ON whatsapp_reminder_deliveries(status, updated_at)
        """)
        delivery_columns = {
            row["name"]
            for row in c.execute(
                "PRAGMA table_info(whatsapp_reminder_deliveries)"
            )
        }
        additions = {
            "provider_message_id": "TEXT",
            "provider_status": "TEXT NOT NULL DEFAULT ''",
            "provider_error_code": "TEXT NOT NULL DEFAULT ''",
            "provider_status_at": "REAL",
        }
        for column, definition in additions.items():
            if column not in delivery_columns:
                c.execute(
                    f"ALTER TABLE whatsapp_reminder_deliveries "
                    f"ADD COLUMN {column} {definition}"
                )

        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "idx_whatsapp_delivery_provider_message "
            "ON whatsapp_reminder_deliveries(provider_message_id) "
            "WHERE provider_message_id IS NOT NULL"
        )
        c.execute("""
            CREATE TABLE IF NOT EXISTS tutoring_states (
                conversation_id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT 'explore'
                    CHECK(stage IN (
                        'explore', 'guide', 'hint',
                        'explain', 'check', 'complete'
                    )),
                attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts >= 0),
                turn_count INTEGER NOT NULL DEFAULT 0 CHECK(turn_count >= 0),
                updated_at REAL NOT NULL,
                FOREIGN KEY(conversation_id)
                    REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        c.commit()
    _migrate_conversation_schema()


def _migrate_conversation_schema():
    """Add chat modes and allow conversations without a course."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        columns = {
            row[1]: row
            for row in conn.execute("PRAGMA table_info(conversations)")
        }
        if not columns:
            raise RuntimeError("The conversations table does not exist.")

        if "chat_mode" not in columns:
            conn.execute(
                "ALTER TABLE conversations ADD COLUMN "
                "chat_mode TEXT NOT NULL DEFAULT 'socratic'"
            )
            conn.commit()
            columns = {
                row[1]: row
                for row in conn.execute("PRAGMA table_info(conversations)")
            }

        # Rebuild only if this database has the old NOT NULL course_id.
        if columns["course_id"][3]:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("""
                CREATE TABLE conversations_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    course_id INTEGER,
                    title TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    chat_mode TEXT NOT NULL DEFAULT 'socratic',
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                INSERT INTO conversations_new
                    (id, user_id, course_id, title, created_at, updated_at, chat_mode)
                SELECT id, user_id, course_id, title, created_at, updated_at, chat_mode
                FROM conversations
            """)
            conn.execute("DROP TABLE conversations")
            conn.execute("ALTER TABLE conversations_new RENAME TO conversations")

            violations = list(conn.execute("PRAGMA foreign_key_check"))
            if violations:
                raise RuntimeError(
                    f"Foreign-key check failed after conversation migration: {violations[:5]}"
                )
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return salt.hex() + "$" + digest.hex()

def _verify(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000).hex()
        return hmac.compare_digest(actual, digest_hex)
    except Exception:
        return False

def create_user(username: str, password: str):
    username = username.strip()
    if not username or len(password) < 6:
        return None, "Username is required and password must be at least 6 characters."
    try:
        with _conn() as c:
            cur = c.execute("INSERT INTO users(username,password_hash,created_at) VALUES(?,?,?)",
                            (username, _hash_password(password), time.time()))
            c.commit()
            return cur.lastrowid, None
    except sqlite3.IntegrityError:
        return None, "That username already exists."

def authenticate(username: str, password: str):
    with _conn() as c:
        row = c.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
    if row and _verify(password, row["password_hash"]):
        return dict(row)
    return None

def get_or_create_demo_course(user_id: int):
    with _conn() as c:
        row = c.execute("SELECT * FROM courses WHERE user_id=? ORDER BY id LIMIT 1", (user_id,)).fetchone()
        if row:
            return dict(row)
        now = time.time()
        cur = c.execute("INSERT INTO courses(user_id,name,description,created_at) VALUES(?,?,?,?)",
                        (user_id, "Machine Learning", "Your first CogniGraph course workspace.", now))
        c.commit()
        return dict(c.execute("SELECT * FROM courses WHERE id=?", (cur.lastrowid,)).fetchone())

def create_course(user_id: int, name: str, description: str = ""):
    name = name.strip()
    if not name: return None, "Course name is required."
    try:
        with _conn() as c:
            cur = c.execute("INSERT INTO courses(user_id,name,description,created_at) VALUES(?,?,?,?)",
                            (user_id,name,description.strip(),time.time()))
            c.commit()
            return dict(c.execute("SELECT * FROM courses WHERE id=?", (cur.lastrowid,)).fetchone()), None
    except sqlite3.IntegrityError:
        return None, "You already have a course with that name."

def list_courses(user_id: int):
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM courses WHERE user_id=? ORDER BY created_at", (user_id,))]

def get_course(course_id: int, user_id: int):
    with _conn() as c:
        r=c.execute("SELECT * FROM courses WHERE id=? AND user_id=?", (course_id,user_id)).fetchone()
        return dict(r) if r else None

def add_source(course_id: int, filename: str, chunks: int, content_sha256: str | None = None):
    with _conn() as c:
        c.execute("""INSERT INTO course_sources(course_id,filename,chunks,created_at,content_sha256)
                     VALUES(?,?,?,?,?)
                     ON CONFLICT(course_id,filename) DO UPDATE SET
                       chunks=excluded.chunks,
                       content_sha256=COALESCE(excluded.content_sha256, course_sources.content_sha256)""",
                  (course_id,filename,chunks,time.time(),content_sha256))
        c.commit()

def set_source_content_hash(source_id: int, course_id: int, content_sha256: str) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE course_sources SET content_sha256=? WHERE id=? AND course_id=? AND content_sha256 IS NULL",
            (content_sha256, int(source_id), int(course_id)),
        )
        c.commit()

def get_source_by_hash(course_id: int, content_sha256: str):
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM course_sources WHERE course_id=? AND content_sha256=? ORDER BY id LIMIT 1",
            (int(course_id), content_sha256),
        ).fetchone()
        return dict(row) if row else None

def get_source_by_filename(course_id: int, filename: str):
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM course_sources WHERE course_id=? AND filename=? LIMIT 1",
            (int(course_id), filename),
        ).fetchone()
        return dict(row) if row else None

def create_ingestion_job(job_id: str, course_id: int, filename: str, content_sha256: str):
    now = time.time()
    try:
        with _conn() as c:
            c.execute(
                "INSERT INTO ingestion_jobs(id,course_id,filename,content_sha256,status,stage,created_at,updated_at) "
                "VALUES(?,?,?,?, 'queued', 'Queued for indexing', ?, ?)",
                (job_id, int(course_id), filename, content_sha256, now, now),
            )
            c.commit()
        return get_ingestion_job(job_id, course_id)
    except sqlite3.IntegrityError:
        # A concurrent upload of this same content may already own the active job.
        return get_active_ingestion_job(course_id, content_sha256)

def get_active_ingestion_job(course_id: int, content_sha256: str):
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM ingestion_jobs WHERE course_id=? AND content_sha256=? "
            "AND status IN ('queued','processing') ORDER BY created_at DESC LIMIT 1",
            (int(course_id), content_sha256),
        ).fetchone()
        return dict(row) if row else None

def get_ingestion_job(job_id: str, course_id: int):
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM ingestion_jobs WHERE id=? AND course_id=?",
            (job_id, int(course_id)),
        ).fetchone()
        return dict(row) if row else None

def list_ingestion_jobs(course_id: int, limit: int = 10):
    cutoff = time.time() - 86400
    with _conn() as c:
        return [dict(row) for row in c.execute(
            "SELECT * FROM ingestion_jobs WHERE course_id=? "
            "AND (status IN ('queued','processing') OR updated_at>=?) "
            "ORDER BY updated_at DESC LIMIT ?",
            (int(course_id), cutoff, max(1, min(int(limit), 25))),
        )]

def update_ingestion_job(
    job_id: str, *, status: str, stage: str, chunks: int = 0, pages: int = 0, error: str = ""
) -> None:
    with _conn() as c:
        c.execute(
            "UPDATE ingestion_jobs SET status=?, stage=?, chunks=?, pages=?, error=?, updated_at=? WHERE id=?",
            (status, stage, int(chunks), int(pages), error[:1000], time.time(), job_id),
        )
        c.commit()

def fail_interrupted_ingestion_jobs() -> None:
    """Mark jobs interrupted by an API process restart so users can safely retry."""
    with _conn() as c:
        c.execute(
            "UPDATE ingestion_jobs SET status='failed', stage='Interrupted', "
            "error='The API restarted before indexing completed. Please upload the PDF again.', updated_at=? "
            "WHERE status IN ('queued','processing')",
            (time.time(),),
        )
        c.commit()

def list_sources(course_id: int):
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM course_sources WHERE course_id=? ORDER BY created_at DESC",(course_id,))]

def get_source(source_id: int, course_id: int):
    """Return a source only when it belongs to the specified course."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM course_sources WHERE id=? AND course_id=?",
            (int(source_id), int(course_id)),
        ).fetchone()
        return dict(row) if row else None

def delete_source(source_id: int, course_id: int) -> bool:
    """Delete a course-source row scoped to one course."""
    with _conn() as c:
        cur = c.execute(
            "DELETE FROM course_sources WHERE id=? AND course_id=?",
            (int(source_id), int(course_id)),
        )
        c.commit()
        return cur.rowcount > 0

def create_conversation(
    user_id: int,
    course_id: int | None,
    title: str = "New chat",
    chat_mode: str = "socratic",
):
    if chat_mode not in ("socratic", "normal"):
        raise ValueError("Invalid chat mode.")
    now = time.time()
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO conversations
               (user_id, course_id, title, created_at, updated_at, chat_mode)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, course_id, title[:120], now, now, chat_mode),
        )
        c.commit()
        return int(cur.lastrowid)


def list_conversations(user_id: int, course_id: int | None):
    with _conn() as c:
        if course_id is None:
            rows = c.execute(
                """SELECT * FROM conversations
                   WHERE user_id=? AND course_id IS NULL
                   ORDER BY updated_at DESC""",
                (user_id,),
            )
        else:
            rows = c.execute(
                """SELECT * FROM conversations
                   WHERE user_id=? AND course_id=?
                   ORDER BY updated_at DESC""",
                (user_id, course_id),
            )
        return [dict(r) for r in rows]

def get_conversation(conversation_id:int,user_id:int):
    with _conn() as c:
        r=c.execute("SELECT * FROM conversations WHERE id=? AND user_id=?",(conversation_id,user_id)).fetchone()
        return dict(r) if r else None

def rename_conversation(conversation_id:int,user_id:int,title:str):
    with _conn() as c:
        c.execute("UPDATE conversations SET title=?,updated_at=? WHERE id=? AND user_id=?",
                  (title.strip()[:120] or "New chat",time.time(),conversation_id,user_id)); c.commit()

def delete_conversation(conversation_id:int,user_id:int):
    with _conn() as c:
        c.execute("DELETE FROM conversations WHERE id=? AND user_id=?",(conversation_id,user_id)); c.commit()

def add_message(conversation_id:int, role:str, content:str, mode="text", source_query="", context_json="[]"):
    with _conn() as c:
        c.execute("""INSERT INTO messages(conversation_id,role,content,mode,source_query,context_json,created_at)
                     VALUES(?,?,?,?,?,?,?)""",
                  (conversation_id,role,content,mode,source_query,context_json,time.time()))
        c.execute("UPDATE conversations SET updated_at=? WHERE id=?",(time.time(),conversation_id)); c.commit()

def list_messages(conversation_id:int):
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM messages WHERE conversation_id=? ORDER BY id",(conversation_id,))]


def get_tutoring_state(conversation_id: int):
    """Read saved Socratic tutoring state for one conversation."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM tutoring_states WHERE conversation_id=?",
            (conversation_id,),
        ).fetchone()
        return dict(row) if row else None


def save_tutoring_state(
    conversation_id: int,
    *,
    topic: str = "",
    stage: str,
    attempts: int = 0,
    turn_count: int = 0,
):
    """Insert or update tutoring progress without changing chat messages."""
    allowed_stages = {
        "explore", "guide", "hint", "explain", "check", "complete"
    }
    if stage not in allowed_stages:
        raise ValueError(f"Invalid tutoring stage: {stage}")
    if attempts < 0 or turn_count < 0:
        raise ValueError("Tutoring counters cannot be negative.")

    with _conn() as c:
        c.execute(
            """
            INSERT INTO tutoring_states
                (conversation_id, topic, stage, attempts, turn_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                topic=excluded.topic,
                stage=excluded.stage,
                attempts=excluded.attempts,
                turn_count=excluded.turn_count,
                updated_at=excluded.updated_at
            """,
            (
                conversation_id,
                topic[:300],
                stage,
                attempts,
                turn_count,
                time.time(),
            ),
        )
        c.commit()


def save_visualization(user_id:int, course_id:int, conversation_id:int|None, kind:str, title:str,
                       query:str, file_bytes:bytes|None=None, extension="png", source_text:str|None=None):
    stamp=f"{int(time.time()*1000)}_{secrets.token_hex(4)}"
    file_path=None
    if file_bytes is not None:
        path=SAVED_DIR/f"{stamp}.{extension}"
        path.write_bytes(file_bytes); file_path=str(path)
    elif source_text is not None:
        path=SAVED_DIR/f"{stamp}.{extension}"
        path.write_text(source_text,encoding="utf-8"); file_path=str(path)
    with _conn() as c:
        cur=c.execute("""INSERT INTO visualizations(user_id,course_id,conversation_id,kind,title,query,file_path,source_text,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?)""",
                      (user_id,course_id,conversation_id,kind,title,query,file_path,source_text,time.time()))
        c.commit()
        return int(cur.lastrowid)

def list_visualizations(user_id:int,course_id:int):
    with _conn() as c:
        return [dict(r) for r in c.execute("""SELECT * FROM visualizations
          WHERE user_id=? AND course_id=? ORDER BY created_at DESC""",(user_id,course_id))]

def delete_visualization(viz_id:int,user_id:int):
    with _conn() as c:
        row=c.execute("SELECT file_path FROM visualizations WHERE id=? AND user_id=?",(viz_id,user_id)).fetchone()
        if row and row["file_path"]:
            try: Path(row["file_path"]).unlink(missing_ok=True)
            except OSError: pass
        c.execute("DELETE FROM visualizations WHERE id=? AND user_id=?",(viz_id,user_id)); c.commit()

def log_activity(user_id:int,course_id:int,event_type:str,detail:str=""):
    with _conn() as c:
        c.execute("INSERT INTO activity(user_id,course_id,event_type,detail,created_at) VALUES(?,?,?,?,?)",
                  (user_id,course_id,event_type,detail,time.time())); c.commit()


def save_study_plan(
    user_id: int,
    course_id: int,
    week_start: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Save or update one study plan for a user, course, and week."""
    if not isinstance(plan, dict):
        raise ValueError("Study plan must be a dictionary.")

    plan_json = json.dumps(plan, ensure_ascii=False)
    now = time.time()

    with _conn() as c:
        c.execute(
            """
            INSERT INTO study_plans
                (user_id, course_id, week_start, plan_json,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, course_id, week_start)
            DO UPDATE SET
                plan_json = excluded.plan_json,
                updated_at = excluded.updated_at
            """,
            (user_id, course_id, week_start, plan_json, now, now),
        )
        row = c.execute(
            """
            SELECT id, user_id, course_id, week_start, plan_json,
                   created_at, updated_at
            FROM study_plans
            WHERE user_id = ? AND course_id = ? AND week_start = ?
            """,
            (user_id, course_id, week_start),
        ).fetchone()

    if row is None:
        raise RuntimeError("Saved study plan could not be retrieved.")

    result = dict(row)
    result["plan"] = json.loads(result.pop("plan_json"))
    return result


def get_study_plan(
    user_id: int,
    course_id: int,
    week_start: str,
) -> dict[str, Any] | None:
    """Retrieve a saved study plan, or None if it does not exist."""
    with _conn() as c:
        row = c.execute(
            """
            SELECT id, user_id, course_id, week_start, plan_json,
                   created_at, updated_at
            FROM study_plans
            WHERE user_id = ? AND course_id = ? AND week_start = ?
            """,
            (user_id, course_id, week_start),
        ).fetchone()

    if row is None:
        return None

    result = dict(row)
    result["plan"] = json.loads(result.pop("plan_json"))
    return result



def get_study_session_progress(
    user_id: int,
    course_id: int,
    week_start: str,
) -> dict[str, bool]:
    """Return {session_date: completed} for one user's course week."""
    with _conn() as c:
        rows = c.execute(
            """
            SELECT session_date, completed
            FROM study_session_progress
            WHERE user_id=? AND course_id=? AND week_start=?
            """,
            (user_id, course_id, week_start),
        ).fetchall()

    return {
        str(row["session_date"]): bool(row["completed"])
        for row in rows
    }


def set_study_session_completion(
    user_id: int,
    course_id: int,
    week_start: str,
    session_date: str,
    completed: bool,
) -> dict[str, Any]:
    """Create or update a session's completion status."""
    now = time.time()

    with _conn() as c:
        c.execute(
            """
            INSERT INTO study_session_progress
                (user_id, course_id, week_start, session_date,
                 completed, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, course_id, week_start, session_date)
            DO UPDATE SET
                completed=excluded.completed,
                updated_at=excluded.updated_at
            """,
            (
                user_id, course_id, week_start, session_date,
                int(bool(completed)), now,
            ),
        )
        row = c.execute(
            """
            SELECT user_id, course_id, week_start, session_date,
                   completed, updated_at
            FROM study_session_progress
            WHERE user_id=? AND course_id=?
              AND week_start=? AND session_date=?
            """,
            (user_id, course_id, week_start, session_date),
        ).fetchone()

    if row is None:
        raise RuntimeError("Could not retrieve saved session progress.")

    result = dict(row)
    result["completed"] = bool(result["completed"])
    return result


def dashboard(user_id:int,course_id:int):
    with _conn() as c:
        chats=c.execute("SELECT COUNT(*) n FROM conversations WHERE user_id=? AND course_id=?",(user_id,course_id)).fetchone()["n"]
        questions=c.execute("""SELECT COUNT(*) n FROM messages m JOIN conversations c ON c.id=m.conversation_id
                              WHERE c.user_id=? AND c.course_id=? AND m.role='user'""",(user_id,course_id)).fetchone()["n"]
        visuals=c.execute("SELECT COUNT(*) n FROM visualizations WHERE user_id=? AND course_id=?",(user_id,course_id)).fetchone()["n"]
        activities=c.execute("SELECT COUNT(*) n FROM activity WHERE user_id=? AND course_id=?",(user_id,course_id)).fetchone()["n"]
        sources=c.execute("SELECT COUNT(*) n FROM course_sources WHERE course_id=?",(course_id,)).fetchone()["n"]
        recent=[dict(r) for r in c.execute("""SELECT event_type,detail,created_at FROM activity
          WHERE user_id=? AND course_id=? ORDER BY created_at DESC LIMIT 50""",(user_id,course_id))]
        activity_7d=[dict(r) for r in c.execute("""SELECT event_type,detail,created_at FROM activity
          WHERE user_id=? AND course_id=? AND created_at>=? ORDER BY created_at DESC""",
          (user_id,course_id,time.time()-8*24*60*60))]
        modes=[dict(r) for r in c.execute("""SELECT m.mode, COUNT(*) n FROM messages m
          JOIN conversations c ON c.id=m.conversation_id WHERE c.user_id=? AND c.course_id=? AND m.role='assistant'
          GROUP BY m.mode""",(user_id,course_id))]
    return {"chats":chats,"questions":questions,"visuals":visuals,"activities":activities,
            "sources":sources,"recent":recent,"activity_7d":activity_7d,"modes":modes}


def save_pending_quiz_question(
    question_id: str,
    user_id: int,
    course_id: int,
    topic: str,
    difficulty: str,
    question: str,
    options: list[str],
    correct_index: int,
    explanation: str,
):
    """Keep answer keys server-side until the learner submits the question."""
    import json
    now = time.time()
    with _conn() as c:
        c.execute(
            "DELETE FROM pending_quiz_questions WHERE created_at<? OR answered_at IS NOT NULL",
            (now - 86400,),
        )
        c.execute(
            """INSERT INTO pending_quiz_questions(
                question_id,user_id,course_id,topic,difficulty,question,options_json,
                correct_index,explanation,created_at,answered_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,NULL)""",
            (
                question_id, user_id, course_id, topic, difficulty, question,
                json.dumps(options), int(correct_index), explanation, now,
            ),
        )
        c.commit()


def take_pending_quiz_question(question_id: str, user_id: int, course_id: int):
    """Atomically mark a quiz question as answered and return its private key."""
    import json
    now = time.time()
    with _conn() as c:
        cur = c.execute(
            """UPDATE pending_quiz_questions SET answered_at=?
               WHERE question_id=? AND user_id=? AND course_id=?
                 AND answered_at IS NULL AND created_at>=?""",
            (now, question_id, user_id, course_id, now - 14400),
        )
        if cur.rowcount != 1:
            c.commit()
            return None
        row = c.execute(
            "SELECT * FROM pending_quiz_questions WHERE question_id=?",
            (question_id,),
        ).fetchone()
        c.commit()
    if row is None:
        return None
    result = dict(row)
    result["options"] = json.loads(result.pop("options_json"))
    return result


def _new_attempt_quality_status(
    question: str,
    options: list[str],
    correct_index: int,
    selected_index: int | None,
    explanation: str,
) -> str:
    """Check structure before allowing a new attempt into learning statistics."""
    if not isinstance(question, str) or not 12 <= len(question.strip()) <= 300:
        return "unverified"
    if not isinstance(options, list) or len(options) != 4:
        return "unverified"
    if any(
        not isinstance(option, str)
        or not option.strip()
        or len(option.strip()) > 160
        for option in options
    ):
        return "unverified"
    if type(correct_index) is not int or correct_index not in range(4):
        return "unverified"
    if type(selected_index) is not int or selected_index not in range(4):
        return "unverified"
    if not isinstance(explanation, str) or len(explanation.strip()) < 10:
        return "unverified"

    keys = [
        "".join(ch for ch in option.casefold() if ch.isalnum())
        for option in options
    ]
    if any(not key for key in keys) or len(set(keys)) != 4:
        return "unverified"

    combined = (question + " " + " ".join(options)).casefold()
    bad_markers = (
        "which statement is directly supported by the course material about",
        "a statement not supported by the supplied course material",
        "a statement that changes the main relationship described in the material",
        "a statement about an unrelated topic",
        "all of the above",
        "none of the above",
    )
    if any(marker in combined for marker in bad_markers):
        return "unverified"
    return "validated"


def record_quiz_attempt(
    user_id: int,
    course_id: int,
    topic: str,
    difficulty: str,
    question: str,
    options: list[str],
    correct_index: int,
    selected_index: int | None,
    is_correct: bool,
    explanation: str,
    hints_used: int = 0,
):
    import json

    actual_correct = int(
        type(correct_index) is int
        and type(selected_index) is int
        and correct_index in range(4)
        and selected_index in range(4)
        and selected_index == correct_index
    )
    quality_status = _new_attempt_quality_status(
        question, options, correct_index, selected_index, explanation
    )

    with _conn() as c:
        cur = c.execute(
            """INSERT INTO quiz_attempts(
                user_id,course_id,topic,difficulty,question,options_json,
                correct_index,selected_index,is_correct,explanation,
                hints_used,created_at,quality_status
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                user_id, course_id, topic.strip() or "Course Review", difficulty,
                question, json.dumps(options), correct_index, selected_index,
                actual_correct, explanation, int(hints_used), time.time(),
                quality_status,
            ),
        )
        c.commit()
        return int(cur.lastrowid)


def _usable_quiz_attempt(attempt):
    """Only validated, structurally sound attempts contribute to progress."""
    if str(attempt.get("quality_status") or "") != "validated":
        return False

    question = str(attempt.get("question") or "").strip()
    if not 12 <= len(question) <= 300:
        return False

    try:
        options = json.loads(attempt.get("options_json") or "null")
    except (TypeError, ValueError):
        return False

    if not isinstance(options, list) or len(options) != 4:
        return False
    if any(
        not isinstance(option, str)
        or not option.strip()
        or len(option.strip()) > 160
        for option in options
    ):
        return False

    keys = [
        "".join(ch for ch in option.casefold() if ch.isalnum())
        for option in options
    ]
    if any(not key for key in keys) or len(set(keys)) != 4:
        return False

    try:
        correct_index = int(attempt.get("correct_index"))
        selected_index = int(attempt.get("selected_index"))
        recorded_correct = int(attempt.get("is_correct"))
    except (TypeError, ValueError):
        return False

    if correct_index not in range(4) or selected_index not in range(4):
        return False
    if recorded_correct not in (0, 1):
        return False
    if recorded_correct != int(selected_index == correct_index):
        return False
    if len(str(attempt.get("explanation") or "").strip()) < 10:
        return False

    combined = (question + " " + " ".join(options)).casefold()
    bad_markers = (
        "which statement is directly supported by the course material about",
        "a statement not supported by the supplied course material",
        "a statement that changes the main relationship described in the material",
        "a statement about an unrelated topic",
        "all of the above",
        "none of the above",
    )
    return not any(marker in combined for marker in bad_markers)


def recent_quiz_attempts(user_id: int, course_id: int, limit: int = 20):
    with _conn() as c:
        rows = c.execute(
            """SELECT * FROM quiz_attempts
               WHERE user_id=? AND course_id=?
               ORDER BY created_at DESC""",
            (user_id, course_id),
        ).fetchall()

    usable = [
        dict(row) for row in rows if _usable_quiz_attempt(dict(row))
    ]
    return usable[:max(0, int(limit))]


def quiz_stats(user_id: int, course_id: int):
    attempts = recent_quiz_attempts(user_id, course_id, limit=1_000_000)
    with _conn() as c:
        raw_total = int(c.execute(
            "SELECT COUNT(*) FROM quiz_attempts WHERE user_id=? AND course_id=?",
            (user_id, course_id),
        ).fetchone()[0])

    correct = sum(int(a.get("is_correct") or 0) for a in attempts)
    total = len(attempts)
    return {
        "attempts": total,
        "correct": correct,
        "incorrect": total - correct,
        "accuracy": correct / total if total else 0.0,
        "unverified_attempts": max(0, raw_total - total),
    }


def adaptive_difficulty(user_id: int, course_id: int, topic: str | None = None) -> str:
    """Choose the next difficulty from the student's recent performance.

    With fewer than three attempts we start at medium. Thereafter the most
    recent ten attempts determine the level: >=80% hard, >=60% medium, else easy.
    """
    attempts = recent_quiz_attempts(user_id, course_id, limit=10)
    if topic:
        topic_l = topic.strip().lower()
        topic_attempts = [a for a in attempts if str(a["topic"]).strip().lower() == topic_l]
        if len(topic_attempts) >= 3:
            attempts = topic_attempts
    if len(attempts) < 3:
        return "medium"
    accuracy = sum(int(a["is_correct"]) for a in attempts) / len(attempts)
    if accuracy >= 0.80:
        return "hard"
    if accuracy >= 0.60:
        return "medium"
    return "easy"




def weak_topics(user_id: int, course_id: int, limit: int = 10):
    """Aggregate validated quiz attempts under meaningful concept groups.

    Historical attempts are classified at read time; stored questions, scores,
    and topic labels are never rewritten by this function.
    """
    import re

    attempts = recent_quiz_attempts(
        user_id, course_id, limit=1_000_000
    )
    grouped = {}

    def classify(attempt):
        saved_topic = str(attempt.get("topic") or "").strip()
        question = str(attempt.get("question") or "")
        explanation = str(attempt.get("explanation") or "")
        raw = saved_topic.casefold()

        is_prompt = bool(re.search(r"\bgenerate\b.*\bquiz\b", raw))
        focus = saved_topic

        if is_prompt:
            match = re.search(
                r"\bquiz\s+on\s+(.+?)(?=\s+using\b|\s+from\b|[.!?]|$)",
                saved_topic,
                flags=re.IGNORECASE,
            )
            focus = match.group(1).strip() if match else ""

        searchable = " ".join((focus, question, explanation)).casefold()

        categories = (
            ("Machine Learning Fundamentals", r"\bmachine[-\s]learning task\b|\bunderstanding the data\b|\bdesired outcome\b"),
            ("Decision Trees", r"\bdecision[-\s]trees?\b|\btree regressor\b|\btree classifier\b"),
            ("Topic Modeling", r"\btopic[-\s]model(?:s|ing|ling)?\b|\blearned topic\b|\bmovie reviews?\b|\bmusician biographies\b|\bmusic.centered films\b"),
            ("Dimensionality Reduction", r"\bdimensionality reduction\b|\bpca\b"),
            ("Model Evaluation", r"\bcross.validation\b|\btest set\b|\bconfusion matrix\b|\bprecision\b|\brecall\b|\bf1 score\b|\bmodel evaluation\b"),
            ("Supervised Learning", r"\bsupervised learning\b"),
            ("Unsupervised Learning", r"\bunsupervised learning\b"),
            ("Clustering", r"\bclustering\b|\bk.means\b"),
            ("Neural Networks", r"\bneural networks?\b|\bdeep learning\b"),
            ("Embeddings", r"\bword2vec\b|\bword embeddings?\b|\bembeddings?\b"),
            ("Regression", r"\blinear regression\b|\blogistic regression\b"),
            ("Data Preprocessing", r"\bdata preprocessing\b|\bfeature scaling\b|\bnormalization\b|\bmissing values\b"),
        )

        for label, pattern in categories:
            if re.search(pattern, searchable):
                return label

        if is_prompt:
            if re.search(r"\bworkflow\b|\bsimple cases\b|\bcomplicated cases\b", question, re.I):
                return "Workflow Selection"
            # Do not display an unclassified generic request as though it
            # were a meaningful academic topic.
            return None

        if not saved_topic or raw in {
            "course overview", "course review", "the current course"
        }:
            return None

        return saved_topic[:80]

    def subtopic_for(parent, attempt):
        text = " ".join((
            str(attempt.get("topic") or ""),
            str(attempt.get("question") or ""),
        )).casefold()

        if parent == "Decision Trees":
            if "edge" in text:
                return "Tree edges"
            if "leaf" in text:
                return "Leaf predictions"
            if "regress" in text:
                return "Tree regression"
            if any(word in text for word in ("overfit", "pure leaf", "training accuracy", "complexity")):
                return "Overfitting and tree complexity"
            if "test" in text:
                return "Tree tests versus test sets"
            if "if/else" in text or "questions as possible" in text:
                return "Decision-tree question selection"
            return "Decision-tree fundamentals"

        if parent == "Topic Modeling":
            if "weight" in text:
                return "Topic weights"
            if "number of topics" in text or "increasing the number" in text:
                return "Choosing the number of topics"
            if any(word in text for word in ("movie", "musical", "musician", "music-centered")):
                return "Interpreting learned topics"
            return "Topic-model interpretation"

        return str(attempt.get("topic") or parent)[:80]

    for attempt in attempts:
        label = classify(attempt)
        if not label:
            continue

        if label not in grouped:
            grouped[label] = {
                "topic": label,
                "attempts": 0,
                "correct": 0,
                "incorrect": 0,
                "_subtopics": set(),
            }

        item = grouped[label]
        item["attempts"] += 1

        if int(attempt.get("is_correct") or 0):
            item["correct"] += 1
        else:
            item["incorrect"] += 1
            item["_subtopics"].add(subtopic_for(label, attempt))

    result = []
    for item in grouped.values():
        total = item["attempts"]
        item["accuracy"] = item["correct"] / total if total else 0.0
        item["subtopics"] = sorted(item.pop("_subtopics"))
        if item["incorrect"] >= 1 and item["accuracy"] < 0.80:
            result.append(item)
        else:
            item.pop("_subtopics", None)

    result.sort(key=lambda item: (item["accuracy"], -item["attempts"]))
    return result[:max(0, int(limit))]


# Authentication sessions are stored in SQLite so service restarts do not
# silently invalidate a student's login. Only a SHA-256 token digest is stored.
def _session_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(token: str, user_id: int, ttl_seconds: int = 60 * 60 * 24 * 14) -> None:
    now = time.time()
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        c.execute(
            "INSERT OR REPLACE INTO sessions(token_hash,user_id,created_at,expires_at) VALUES(?,?,?,?)",
            (_session_digest(token), int(user_id), now, now + ttl_seconds),
        )
        c.commit()


def get_session(token: str) -> dict[str, Any] | None:
    if not token:
        return None
    now = time.time()
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        row = c.execute(
            "SELECT u.id, u.username FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token_hash=? AND s.expires_at>?",
            (_session_digest(token), now),
        ).fetchone()
        c.commit()
    return dict(row) if row else None


def delete_session(token: str) -> None:
    if not token:
        return
    with _conn() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (_session_digest(token),))
        c.commit()



def save_revision_sheet(
    user_id: int,
    course_id: int,
    request_topic: str,
    content: str,
    sources: list,
    topics: list,
) -> int:
    """Save a revision sheet while preserving earlier sheets."""
    with _conn() as c:
        cur = c.execute(
            """INSERT INTO revision_sheets(
                user_id, course_id, request_topic, content,
                sources_json, topics_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                course_id,
                str(request_topic or ""),
                str(content or ""),
                json.dumps(sources if isinstance(sources, list) else [],
                           ensure_ascii=False),
                json.dumps(topics if isinstance(topics, list) else [],
                           ensure_ascii=False),
                time.time(),
            ),
        )
        c.commit()
        return int(cur.lastrowid)


def latest_revision_sheet(user_id: int, course_id: int):
    """Retrieve the latest sheet for the specified user and course."""
    with _conn() as c:
        row = c.execute(
            """SELECT request_topic, content, sources_json,
                      topics_json, created_at
               FROM revision_sheets
               WHERE user_id=? AND course_id=?
               ORDER BY created_at DESC, id DESC
               LIMIT 1""",
            (user_id, course_id),
        ).fetchone()

    if row is None:
        return None

    def decode_list(value):
        try:
            result = json.loads(value or "[]")
            return result if isinstance(result, list) else []
        except (TypeError, ValueError):
            return []

    return {
        "request_topic": row["request_topic"],
        "content": row["content"],
        "sources": decode_list(row["sources_json"]),
        "topics": decode_list(row["topics_json"]),
        "created_at": float(row["created_at"] or 0),
    }


def get_whatsapp_reminder_preferences(user_id: int):
    """Return reminder preferences for one user, if configured."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM whatsapp_reminder_preferences WHERE user_id=?",
            (int(user_id),),
        ).fetchone()

    if row is None:
        return None

    result = dict(row)
    result["enabled"] = bool(result["enabled"])
    result["consent"] = result["consent_at"] is not None
    return result


def save_whatsapp_reminder_preferences(
    user_id: int,
    phone_number: str,
    enabled: bool,
    timezone_name: str,
    reminder_time: str,
    consent: bool,
):
    """Save a user's explicit opt-in and reminder preferences."""
    now = time.time()
    phone_number = str(phone_number or "").strip()

    if enabled and not consent:
        raise ValueError("Explicit consent is required to enable reminders.")
    if enabled and not phone_number:
        raise ValueError("A WhatsApp number is required to enable reminders.")

    with _conn() as c:
        c.execute(
            """INSERT INTO whatsapp_reminder_preferences(
                   user_id, phone_number, enabled, timezone,
                   reminder_time, consent_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   phone_number=excluded.phone_number,
                   enabled=excluded.enabled,
                   timezone=excluded.timezone,
                   reminder_time=excluded.reminder_time,
                   consent_at=CASE
                       WHEN excluded.consent_at IS NULL THEN NULL
                       WHEN whatsapp_reminder_preferences.consent_at IS NULL
                           THEN excluded.consent_at
                       ELSE whatsapp_reminder_preferences.consent_at
                   END,
                   updated_at=excluded.updated_at""",
            (
                int(user_id),
                phone_number,
                int(bool(enabled and consent)),
                str(timezone_name),
                str(reminder_time),
                now if consent else None,
                now,
            ),
        )
        c.commit()

    return get_whatsapp_reminder_preferences(user_id)


def reset_stale_whatsapp_reminder_deliveries(
    stale_seconds: int = 900,
) -> int:
    """Release processing records left stale after a worker interruption."""
    cutoff = time.time() - max(60, int(stale_seconds))
    with _conn() as c:
        cur = c.execute(
            """UPDATE whatsapp_reminder_deliveries
               SET status='failed',
                   last_error='Recovered stale processing record',
                   updated_at=?
               WHERE status='processing' AND updated_at < ?""",
            (time.time(), cutoff),
        )
        c.commit()
        return int(cur.rowcount)


def claim_whatsapp_reminder_delivery(
    user_id: int,
    course_id: int,
    week_start: str,
    session_date: str,
) -> bool:
    """Claim a reminder; retries of failed records require explicit authorization."""
    now = time.time()

    with _conn() as c:
        c.execute("BEGIN IMMEDIATE")
        cur = c.execute(
            """INSERT INTO whatsapp_reminder_deliveries(
                   user_id, course_id, week_start, session_date,
                   status, attempt_count, last_error, created_at, updated_at
               ) VALUES (?, ?, ?, ?, 'processing', 1, '', ?, ?)
               ON CONFLICT(user_id, course_id, week_start, session_date)
               DO UPDATE SET
                   status='processing',
                   attempt_count=
                       whatsapp_reminder_deliveries.attempt_count + 1,
                   last_error='',
                   updated_at=excluded.updated_at
               WHERE whatsapp_reminder_deliveries.status='failed'
                   AND whatsapp_reminder_deliveries.last_error
                       LIKE 'MANUAL_RETRY:%'""",
            (
                int(user_id), int(course_id), str(week_start),
                str(session_date), now, now,
            ),
        )
        c.commit()
        return cur.rowcount == 1


def finish_whatsapp_reminder_delivery(
    user_id: int,
    course_id: int,
    week_start: str,
    session_date: str,
    sent: bool,
    error: str = "",
) -> bool:
    """Record a provider response for a claimed reminder."""
    now = time.time()
    status = "sent" if sent else "failed"
    with _conn() as c:
        cur = c.execute(
            """UPDATE whatsapp_reminder_deliveries
               SET status=?, last_error=?, updated_at=?, sent_at=?
               WHERE user_id=? AND course_id=? AND week_start=?
                 AND session_date=? AND status='processing'""",
            (
                status,
                "" if sent else str(error or "Delivery failed")[:1000],
                now,
                now if sent else None,
                int(user_id),
                int(course_id),
                str(week_start),
                str(session_date),
            ),
        )
        c.commit()
        return cur.rowcount == 1



def finish_whatsapp_reminder_delivery_meta(
    user_id: int,
    course_id: int,
    week_start: str,
    session_date: str,
    sent: bool,
    error: str = "",
    provider_message_id: str | None = None,
    provider_status: str = "",
    provider_error_code: str = "",
) -> bool:
    """Record Meta API acceptance or request failure."""
    now = time.time()
    status_value = provider_status or ("accepted" if sent else "failed")
    local_status = "sent" if sent else "failed"

    with _conn() as c:
        cur = c.execute(
            """UPDATE whatsapp_reminder_deliveries
               SET status=?, last_error=?, updated_at=?, sent_at=?,
                   provider_message_id=?, provider_status=?,
                   provider_error_code=?, provider_status_at=?
               WHERE user_id=? AND course_id=? AND week_start=?
                 AND session_date=? AND status='processing'""",
            (
                local_status,
                "" if sent else str(error or "WhatsApp request failed")[:1000],
                now,
                now if sent else None,
                provider_message_id,
                status_value,
                str(provider_error_code or "")[:100],
                now,
                int(user_id),
                int(course_id),
                str(week_start),
                str(session_date),
            ),
        )
        c.commit()
        return cur.rowcount == 1


def update_whatsapp_delivery_status(
    provider_message_id: str,
    provider_status: str,
    error_code: str = "",
    error_message: str = "",
    provider_timestamp: float | None = None,
) -> bool:
    """Apply Meta status events without allowing stale status regressions."""
    message_id = str(provider_message_id or "").strip()
    status_value = str(provider_status or "").strip().lower()

    if not message_id or status_value not in {
        "sent", "delivered", "read", "failed"
    }:
        return False

    now = time.time()
    status_time = (
        float(provider_timestamp)
        if provider_timestamp is not None
        else now
    )
    error_text = str(error_message or "")[:1000]
    error_code_text = str(error_code or "")[:100]
    rank = {"": 0, "accepted": 0, "sent": 1, "delivered": 2, "read": 3}

    with _conn() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute(
            """SELECT provider_status FROM whatsapp_reminder_deliveries
               WHERE provider_message_id=?""",
            (message_id,),
        ).fetchone()

        if row is None:
            c.commit()
            return False

        current = str(row["provider_status"] or "").lower()

        # Read and failed are terminal. Delivered may advance to read.
        if current in {"read", "failed"}:
            c.commit()
            return True

        # Once delivered, ignore all statuses except a read confirmation.
        if current == "delivered" and status_value != "read":
            c.commit()
            return True

        # Ignore an older or duplicate success status.
        if status_value != "failed" and rank.get(status_value, 0) <= rank.get(current, 0):
            c.commit()
            return True

        local_status = "failed" if status_value == "failed" else "sent"
        c.execute(
            """UPDATE whatsapp_reminder_deliveries
               SET provider_status=?,
                   provider_error_code=?,
                   provider_status_at=?,
                   status=?,
                   last_error=CASE WHEN ?='failed' THEN ?
                                   ELSE last_error END,
                   updated_at=?
               WHERE provider_message_id=?""",
            (
                status_value,
                error_code_text,
                status_time,
                local_status,
                status_value,
                error_text or "Meta reported message delivery failure",
                now,
                message_id,
            ),
        )
        c.commit()
        return True


def authorize_whatsapp_reminder_retry(
    user_id: int,
    course_id: int,
    week_start: str,
    session_date: str,
    reason: str,
) -> bool:
    """Explicitly authorize a retry after reviewing a failed attempt."""
    now = time.time()
    with _conn() as c:
        cur = c.execute(
            """UPDATE whatsapp_reminder_deliveries
               SET last_error=?, updated_at=?
               WHERE user_id=? AND course_id=? AND week_start=?
                 AND session_date=? AND status='failed'""",
            (
                "MANUAL_RETRY: " + str(reason or "Manually approved")[:900],
                now,
                int(user_id),
                int(course_id),
                str(week_start),
                str(session_date),
            ),
        )
        c.commit()
        return cur.rowcount == 1
