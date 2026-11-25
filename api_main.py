"""FastAPI bridge from the React UI to the existing CogniGraph modules."""
from __future__ import annotations
from fastapi.responses import FileResponse
import os
import base64, io, json, secrets, time, logging, os
from pathlib import Path
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re
from typing import Optional
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, Header, UploadFile, File, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import PlainTextResponse

import storage
from config import DATA_DIR, UPLOAD_DIR
from ingestion.pdf_processor import process_pdf
from llm.socratic_engine import SocraticEngine, ConversationState, TutorTurn
from llm.base import ChatMessage
from rag.retriever import retrieve, sample_course_context
from rag.vectorstore import get_vectorstore
from router.multimodal_router import classify, explain_classification, OutputMode
from orchestration.visualization_chain import run_visualization
from learning import generate_quiz_question, generate_revision, generate_explanation
from study_schedule import build_weekly_plan

app = FastAPI(title="CogniGraph API", version="1.0.0", description="React API for the CogniGraph Socratic tutor")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger = logging.getLogger("cognigraph.api")
_engine: SocraticEngine | None = None

def engine():
    global _engine
    if _engine is None:
        _engine = SocraticEngine()
    return _engine

def current_user(authorization: str | None = Header(default=None)):
    token = authorization.removeprefix("Bearer ") if authorization else ""
    user = storage.get_session(token)
    if not user: raise HTTPException(401, "Please sign in again.")
    return user

def check_course(course_id: int, user: dict):
    course = storage.get_course(course_id, int(user["id"]))
    if not course: raise HTTPException(404, "Course not found.")
    return course

def context_text(contexts):
    return "\n\n".join(f"[{x.source}, p.{x.page}]\n{x.text}" for x in contexts)


def recent_course_chat_context(
    user_id: int,
    course_id: int,
    max_conversations: int = 5,
    max_messages: int = 16,
    max_chars: int = 6000,
) -> str:
    """Return bounded recent messages from this user's selected course only."""
    conversations = storage.list_conversations(
        int(user_id), int(course_id)
    )[:max_conversations]

    collected = []
    for conversation in conversations:
        title = str(conversation.get("title") or "Course discussion")[:120]
        messages = storage.list_messages(int(conversation["id"]))
        for message in messages[-6:]:
            role = str(message.get("role") or "").strip().lower()
            content = str(message.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                continue
            content = content[:1200]
            try:
                timestamp = float(message.get("created_at") or 0)
            except (TypeError, ValueError):
                timestamp = 0.0
            collected.append((timestamp, title, role, content))

    collected.sort(key=lambda item: item[0])
    collected = collected[-max_messages:]

    lines = []
    remaining = max_chars
    for _, title, role, content in collected:
        prefix = f"[Conversation: {title}] {role.upper()}: "
        available = remaining - len(prefix) - 1
        if available <= 0:
            break
        line = prefix + content[:available]
        lines.append(line)
        remaining -= len(line) + 1

    return "\n".join(lines)


def fig_png(fig):
    if fig is None: return None
    b=io.BytesIO(); fig.savefig(b,format="png",dpi=130,bbox_inches="tight"); return base64.b64encode(b.getvalue()).decode()

class Credentials(BaseModel): username: str; password: str
class CourseInput(BaseModel): name: str; description: str = ""
class ChatInput(BaseModel): course_id: int | None = None; conversation_id: int | None = None; message: str; chat_mode: str = 'socratic'
class ActionInput(BaseModel): course_id: int; conversation_id: int | None = None; query: str; original_response: str = ""
class QuizStart(BaseModel): course_id: int; topic: str = ""
class QuizAnswer(BaseModel): course_id: int; question_id: str; selected_index: int; hints_used: int = 0
class RevisionInput(BaseModel): course_id: int; topic: str = ""
class StudyPlanInput(BaseModel):
    week_start: str
    plan: dict


class StudySessionCompletionInput(BaseModel):
    week_start: str
    session_date: str
    completed: bool


class WhatsAppReminderPreferencesInput(BaseModel):
    phone_number: str = ""
    enabled: bool = False
    timezone: str = "Asia/Karachi"
    reminder_time: str = "19:00"
    consent: bool = False


class SaveVizInput(BaseModel): course_id: int; kind: str; title: str; query: str; source_text: str = ""; image_base64: str = ""

@app.on_event("startup")
def startup():
    storage.init_db()
    storage.fail_interrupted_ingestion_jobs()

@app.get("/api/health")
def health(): return {"status":"ok", "service":"CogniGraph API"}

@app.post("/api/auth/register")
def register(body: Credentials):
    uid, err = storage.create_user(body.username, body.password)
    if err: raise HTTPException(400, err)
    # New accounts start with an empty workspace; students create their own courses.
    user = {"id":uid,"username":body.username.strip()}
    token=secrets.token_urlsafe(32)
    storage.create_session(token, uid)
    return {"token":token,"user":user,"courses":storage.list_courses(uid)}

@app.post("/api/auth/login")
def login(body: Credentials):
    row=storage.authenticate(body.username,body.password)
    if not row: raise HTTPException(401,"Incorrect username or password.")
    user={"id":row["id"],"username":row["username"]}
    token=secrets.token_urlsafe(32)
    storage.create_session(token, user["id"])
    return {"token":token,"user":user,"courses":storage.list_courses(user["id"])}

@app.post("/api/auth/logout")
def logout(user=Depends(current_user), authorization: str | None=Header(default=None)):
    token=authorization.removeprefix("Bearer ") if authorization else ""
    storage.delete_session(token)
    return {"ok":True}

@app.get("/api/me")
def me(user=Depends(current_user)):
    courses=storage.list_courses(user["id"])
    return {"user":user,"courses":courses}

@app.get("/api/me/whatsapp-reminders")
def get_whatsapp_reminder_preferences(user=Depends(current_user)):
    preferences = storage.get_whatsapp_reminder_preferences(int(user["id"]))
    return {"preferences": preferences}


@app.put("/api/me/whatsapp-reminders")
def update_whatsapp_reminder_preferences(
    body: WhatsAppReminderPreferencesInput,
    user=Depends(current_user),
):
    # Normalize common formatting without guessing a country code.
    phone = re.sub(r"[\s().-]", "", body.phone_number or "")

    if body.enabled and not body.consent:
        raise HTTPException(
            status_code=400,
            detail="Explicit consent is required to enable reminders.",
        )

    existing = storage.get_whatsapp_reminder_preferences(int(user["id"]))
    if not phone and existing:
        phone = str(existing.get("phone_number") or "")

    if body.enabled and not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        raise HTTPException(
            status_code=400,
            detail="Enter a WhatsApp number in international format, e.g. +923001234567.",
        )

    if phone and not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        raise HTTPException(
            status_code=400,
            detail="The phone number must use international format, e.g. +923001234567.",
        )

    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", body.reminder_time):
        raise HTTPException(
            status_code=400,
            detail="reminder_time must use 24-hour HH:MM format, e.g. 19:00.",
        )

    try:
        ZoneInfo(body.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Unknown timezone. Use a valid IANA timezone such as Asia/Karachi.",
        )

    try:
        preferences = storage.save_whatsapp_reminder_preferences(
            user_id=int(user["id"]),
            phone_number=phone,
            enabled=body.enabled,
            timezone_name=body.timezone,
            reminder_time=body.reminder_time,
            consent=body.consent,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"preferences": preferences}



@app.get("/api/webhooks/whatsapp", include_in_schema=False)
def verify_whatsapp_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(
        default=None, alias="hub.verify_token"
    ),
    hub_challenge: str | None = Query(
        default=None, alias="hub.challenge"
    ),
):
    expected = os.getenv(
        "COGNIGRAPH_WHATSAPP_WEBHOOK_VERIFY_TOKEN", ""
    ).strip()

    if (
        hub_mode == "subscribe"
        and expected
        and secrets.compare_digest(hub_verify_token or "", expected)
        and hub_challenge is not None
    ):
        return PlainTextResponse(hub_challenge, status_code=200)

    raise HTTPException(status_code=403, detail="Webhook verification failed.")


@app.post("/api/webhooks/whatsapp", include_in_schema=False)
async def whatsapp_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
):
    from whatsapp_cloud import (
        parse_status_events,
        verify_webhook_signature,
    )

    raw_body = await request.body()
    if not verify_webhook_signature(raw_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload.")

    if payload.get("object") != "whatsapp_business_account":
        # Validly signed events for another Meta product are acknowledged
        # but are not interpreted as WhatsApp delivery updates.
        return {"ok": True, "status_events": 0, "updated": 0, "ignored": 0}

    expected_phone_id = os.getenv(
        "COGNIGRAPH_WHATSAPP_PHONE_NUMBER_ID", ""
    ).strip()
    expected_waba_id = os.getenv(
        "COGNIGRAPH_WHATSAPP_WABA_ID", ""
    ).strip()

    if not expected_phone_id:
        raise HTTPException(
            status_code=503,
            detail="WhatsApp Phone Number ID is not configured.",
        )

    events = parse_status_events(payload)
    updated_count = 0
    ignored_count = 0

    for event in events:
        # Ensure signed events are for the configured sender/account.
        if event["phone_number_id"] != expected_phone_id:
            ignored_count += 1
            continue

        if (
            expected_waba_id
            and event["waba_id"] != expected_waba_id
        ):
            ignored_count += 1
            continue

        if not event["message_id"]:
            ignored_count += 1
            continue

        matched = storage.update_whatsapp_delivery_status(
            provider_message_id=event["message_id"],
            provider_status=event["status"],
            error_code=event["error_code"],
            error_message=event["error_message"],
            provider_timestamp=event["timestamp"],
        )
        if matched:
            updated_count += 1
        else:
            ignored_count += 1

    logger.info(
        "WhatsApp status webhook: events=%d updated=%d ignored=%d",
        len(events), updated_count, ignored_count,
    )
    return {
        "ok": True,
        "status_events": len(events),
        "updated": updated_count,
        "ignored": ignored_count,
    }


@app.get("/api/courses")
def courses(user=Depends(current_user)): return storage.list_courses(user["id"])

@app.post("/api/courses")
def add_course(body: CourseInput, user=Depends(current_user)):
    course, err=storage.create_course(user["id"],body.name,body.description)
    if err: raise HTTPException(400,err)
    return course

@app.get("/api/courses/{course_id}/sources")
def sources(course_id:int,user=Depends(current_user)):
    check_course(course_id,user); return storage.list_sources(course_id)

@app.delete("/api/courses/{course_id}/sources/{source_id}")
def remove_course_source(course_id: int, source_id: int, user=Depends(current_user)):
    """Delete a PDF and its indexed chunks, restricted to the signed-in user's course."""
    check_course(course_id, user)
    source = storage.get_source(source_id, course_id)
    if not source:
        raise HTTPException(404, "PDF not found in this course.")

    filename = str(source["filename"])
    # Only simple basenames are valid; never permit a stored value to escape the course folder.
    if not filename or filename in {".", ".."} or Path(filename).name != filename or "/" in filename or "\\" in filename:
        logger.error("Refusing unsafe stored PDF filename for source_id=%s", source_id)
        raise HTTPException(500, "The stored PDF filename is invalid; no files were deleted.")

    # First remove the matching chunks. Leave the file and source row in place if this fails.
    try:
        vectorstore = get_vectorstore(course_id)
        matches = vectorstore.store._collection.get(where={"source": filename}, include=["metadatas"])
        chunk_ids = matches.get("ids") or []
        if chunk_ids:
            vectorstore.store.delete(ids=chunk_ids)
    except Exception as exc:
        logger.exception("Failed to remove indexed chunks for course_id=%s source_id=%s", course_id, source_id)
        raise HTTPException(500, "Could not remove this PDF's indexed chunks. The PDF was left in place.") from exc

    course_folder = (UPLOAD_DIR / str(course_id)).resolve()
    pdf_path = (course_folder / filename).resolve()
    if course_folder not in pdf_path.parents:
        raise HTTPException(500, "The stored PDF path is invalid.")
    try:
        pdf_path.unlink(missing_ok=True)
    except OSError as exc:
        logger.exception("Failed to remove uploaded PDF course_id=%s source_id=%s", course_id, source_id)
        raise HTTPException(500, "Indexed chunks were removed, but the PDF file could not be deleted. Please retry.") from exc

    if not storage.delete_source(source_id, course_id):
        raise HTTPException(404, "PDF record was not found; refresh the workspace.")
    storage.log_activity(user["id"], course_id, "material_deleted", filename)
    return {"ok": True, "source_id": source_id, "filename": filename, "chunks_deleted": len(chunk_ids)}

def _sha256_bytes(content: bytes) -> str:
    import hashlib
    return hashlib.sha256(content).hexdigest()

def _sha256_file(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def _process_pdf_ingestion_job(
    job_id: str, course_id: int, user_id: int, filename: str, file_path: str, content_sha256: str
) -> None:
    """Index one PDF off-request while preserving the configured BGE-M3 pipeline."""
    dest = Path(file_path)
    source_saved = False
    vectorstore = None
    preexisting_ids: set[str] = set()
    can_clean_failed_chunks = False
    try:
        vectorstore = get_vectorstore(course_id)
        try:
            existing = vectorstore.store._collection.get(
                where={"source": filename}, include=["metadatas"]
            )
            preexisting_ids = set(existing.get("ids") or [])
            can_clean_failed_chunks = True
        except Exception:
            # Never risk deleting data we could not inspect before the new job.
            logger.exception(
                "Could not inspect existing chunks before ingestion course_id=%s filename=%s",
                course_id, filename,
            )
        storage.update_ingestion_job(
            job_id, status="processing", stage="Extracting PDF text"
        )
        chunks = process_pdf(dest)
        if not chunks:
            raise ValueError("No readable text was extracted from this PDF.")
        pages = len({chunk.page for chunk in chunks})
        storage.update_ingestion_job(
            job_id, status="processing", stage=f"Embedding {len(chunks)} chunks with BGE-M3"
        )
        count = vectorstore.add_chunks(chunks)
        storage.add_source(course_id, filename, count, content_sha256=content_sha256)
        source_saved = True
        storage.log_activity(user_id, course_id, "material_uploaded", filename)
        storage.update_ingestion_job(
            job_id, status="succeeded", stage="Indexed successfully", chunks=count, pages=pages
        )
        logger.info(
            "PDF ingestion complete course_id=%s job_id=%s filename=%s chunks=%s pages=%s",
            course_id, job_id, filename, count, pages,
        )
    except Exception as exc:
        logger.exception(
            "PDF ingestion failed course_id=%s job_id=%s filename=%s", course_id, job_id, filename
        )
        # This filename is unique within this course for different PDF contents.
        # Remove any partially indexed chunks from this failed new ingestion only.
        try:
            if not can_clean_failed_chunks or vectorstore is None:
                logger.warning(
                    "Skipped failed-ingestion chunk cleanup because the pre-job state could not be verified "
                    "course_id=%s job_id=%s", course_id, job_id,
                )
            else:
                matches = vectorstore.store._collection.get(
                    where={"source": filename}, include=["metadatas"]
                )
                # Preserve every ID that existed before this job; only remove newly introduced IDs.
                ids = [
                    item_id for item_id in (matches.get("ids") or [])
                    if item_id not in preexisting_ids
                ]
                if ids:
                    vectorstore.store.delete(ids=ids)
        except Exception:
            logger.exception(
                "Failed to clean partial chunks course_id=%s job_id=%s", course_id, job_id
            )
        if source_saved:
            try:
                saved = storage.get_source_by_filename(course_id, filename)
                if saved and saved.get("content_sha256") == content_sha256:
                    storage.delete_source(saved["id"], course_id)
            except Exception:
                logger.exception("Failed to roll back source row for ingestion job_id=%s", job_id)
        storage.update_ingestion_job(
            job_id, status="failed", stage="Indexing failed",
            error="PDF indexing failed. Check the server log and upload the file again."
        )

@app.post("/api/courses/{course_id}/upload")
def upload_pdf(
    course_id: int, background_tasks: BackgroundTasks,
    file: UploadFile = File(...), user=Depends(current_user)
):
    check_course(course_id, user)
    incoming_name = Path(str(file.filename or "").replace("\\", "/")).name
    if not incoming_name or not incoming_name.lower().endswith(".pdf"):
        raise HTTPException(400, "Please upload a PDF file.")
    content = file.file.read()
    if len(content) > 35 * 1024 * 1024:
        raise HTTPException(413, "PDF must be smaller than 35 MB.")
    if not content:
        raise HTTPException(400, "The uploaded PDF is empty.")

    content_sha256 = _sha256_bytes(content)
    folder = UPLOAD_DIR / str(course_id)
    folder.mkdir(parents=True, exist_ok=True)

    # Backfill hashes for legacy source records from their existing PDF files.
    # This does not touch existing Chroma vectors or re-embed prior documents.
    duplicate = storage.get_source_by_hash(course_id, content_sha256)
    if duplicate is None:
        for source in storage.list_sources(course_id):
            if source.get("content_sha256"):
                continue
            old_name = str(source.get("filename") or "")
            if not old_name or Path(old_name).name != old_name or "\\" in old_name or "/" in old_name:
                continue
            old_path = folder / old_name
            if old_path.is_file():
                try:
                    old_hash = _sha256_file(old_path)
                    storage.set_source_content_hash(source["id"], course_id, old_hash)
                    if old_hash == content_sha256:
                        duplicate = source
                        duplicate["content_sha256"] = old_hash
                        break
                except OSError:
                    logger.warning(
                        "Could not hash legacy source file course_id=%s filename=%s",
                        course_id, old_name,
                    )

    if duplicate:
        return {
            "status": "already_indexed", "duplicate": True, "job_id": None,
            "filename": duplicate["filename"], "chunks": int(duplicate.get("chunks") or 0),
        }

    active_job = storage.get_active_ingestion_job(course_id, content_sha256)
    if active_job:
        return {
            "status": active_job["status"], "duplicate": True, "job_id": active_job["id"],
            "filename": active_job["filename"], "chunks": int(active_job.get("chunks") or 0),
        }

    used_names = {str(row.get("filename") or "") for row in storage.list_sources(course_id)}
    destination_name = incoming_name
    destination = folder / destination_name
    if destination_name in used_names:
        stem, suffix = Path(incoming_name).stem, Path(incoming_name).suffix
        destination_name = f"{stem}-{content_sha256[:10]}{suffix}"
        destination = folder / destination_name
    elif destination.exists():
        try:
            if _sha256_file(destination) != content_sha256:
                stem, suffix = Path(incoming_name).stem, Path(incoming_name).suffix
                destination_name = f"{stem}-{content_sha256[:10]}{suffix}"
                destination = folder / destination_name
        except OSError as exc:
            raise HTTPException(500, "Could not safely inspect the existing PDF file.") from exc

    # Avoid overwriting a file from another upload, even in an unusual collision.
    if destination.exists() and _sha256_file(destination) != content_sha256:
        raise HTTPException(409, "A filename collision was detected. Rename the PDF and retry.")
    destination.write_bytes(content)
    job_id = secrets.token_hex(16)
    job = storage.create_ingestion_job(job_id, course_id, destination_name, content_sha256)
    if not job or job.get("id") != job_id:
        active_job = storage.get_active_ingestion_job(course_id, content_sha256)
        if active_job:
            return {
                "status": active_job["status"], "duplicate": True, "job_id": active_job["id"],
                "filename": active_job["filename"], "chunks": int(active_job.get("chunks") or 0),
            }
        raise HTTPException(409, "This PDF is already being indexed. Refresh the course workspace and retry if needed.")

    background_tasks.add_task(
        _process_pdf_ingestion_job, job_id, course_id, int(user["id"]),
        destination_name, str(destination), content_sha256,
    )
    return {
        "status": "queued", "duplicate": False, "job_id": job_id,
        "filename": destination_name, "chunks": 0,
    }

@app.get("/api/courses/{course_id}/upload-jobs")
def course_upload_jobs(course_id: int, user=Depends(current_user)):
    check_course(course_id, user)
    return {"jobs": storage.list_ingestion_jobs(course_id)}

@app.get("/api/courses/{course_id}/upload-jobs/{job_id}")
def course_upload_job(course_id: int, job_id: str, user=Depends(current_user)):
    check_course(course_id, user)
    job = storage.get_ingestion_job(job_id, course_id)
    if not job:
        raise HTTPException(404, "Upload job not found in this course.")
    return job

@app.get("/api/chats")
def general_chats(user=Depends(current_user)):
    return storage.list_conversations(int(user["id"]), None)


@app.get("/api/courses/{course_id}/chats")
def chats(course_id:int,user=Depends(current_user)):
    check_course(course_id,user); return storage.list_conversations(user["id"],course_id)

@app.delete("/api/chats/{conversation_id}")
def remove_chat(conversation_id:int,user=Depends(current_user)):
    conversation = storage.get_conversation(conversation_id,user["id"])
    if not conversation:
        raise HTTPException(404,"Conversation not found.")
    storage.delete_conversation(conversation_id,user["id"])
    return {"ok": True, "conversation_id": conversation_id}

@app.post("/api/chat")
def chat(body: ChatInput, user=Depends(current_user)):
    text = body.message.strip()
    if not text:
        raise HTTPException(400, "Message cannot be empty.")
    if body.chat_mode not in ("socratic", "normal"):
        raise HTTPException(400, "Chat mode must be 'socratic' or 'normal'.")

    course_id = int(body.course_id) if body.course_id is not None else None
    if course_id is not None:
        check_course(course_id, user)

    cid = body.conversation_id
    if cid:
        conv = storage.get_conversation(cid, int(user["id"]))
        if not conv or conv["course_id"] != course_id:
            raise HTTPException(404, "Conversation not found.")
        saved_mode = conv.get("chat_mode") or "socratic"
        if saved_mode != body.chat_mode:
            raise HTTPException(
                409,
                "This conversation's mode is locked. Start a new chat to choose another mode.",
            )
    else:
        cid = storage.create_conversation(
            int(user["id"]), course_id, text[:60], chat_mode=body.chat_mode
        )

    previous = storage.list_messages(cid)
    state = ConversationState([
        TutorTurn(role=m["role"], content=m["content"])
        for m in previous
        if m["role"] in ("user", "assistant")
    ])
    started = time.perf_counter()

    # General chat and course-free Socratic chat never query the legacy vector store.
    if body.chat_mode == "normal" or course_id is None:
        if body.chat_mode == "normal":
            system_prompt = (
                "You are CogniGraph's helpful general AI assistant. Answer directly, "
                "accurately, and clearly. Use Markdown and examples when useful. "
                "Do not force the learner into a Socratic exercise or end every answer "
                "with a question. No course documents have been provided for this turn; "
                "never claim to have searched or read course files."
            )
        else:
            system_prompt = (
                "You are CogniGraph in Socratic learning mode. Be supportive and help "
                "the learner reason step by step. Ask one focused question at a time, "
                "offer hints before revealing a full solution when appropriate, and "
                "adapt to the learner's answers. No course documents have been provided, "
                "so use general knowledge and be transparent about uncertainty."
            )

        llm_messages = [ChatMessage(role="system", content=system_prompt)]
        for message in previous[-20:]:
            role = message.get("role")
            content = str(message.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                llm_messages.append(ChatMessage(role=role, content=content))
        llm_messages.append(ChatMessage(role="user", content=text))

        try:
            generated = engine().chat_model.brain.generate(llm_messages)
        except Exception as e:
            logger.exception("General chat generation failed; chat_mode=%s", body.chat_mode)
            raise HTTPException(
                500, f"Chat generation failed: {type(e).__name__}: {e}"
            )

        turn = TutorTurn(
            role="assistant",
            content=generated.text,
            context_used=[],
            source_query=text,
        )
        saved_tutoring = None
    else:
        # Existing course-aware Socratic engine remains the source of course context.
        saved_tutoring = storage.get_tutoring_state(cid)
        if saved_tutoring:
            state.stage = str(saved_tutoring.get("stage") or "explore")
            state.attempts = int(saved_tutoring.get("attempts") or 0)
            state.turn_count = int(saved_tutoring.get("turn_count") or 0)
            state.topic = str(saved_tutoring.get("topic") or "")
            state.tutoring_active = state.stage != "complete"

        try:
            turn = engine().ask(state, text, course_id=course_id)
        except Exception as e:
            logger.exception("Tutor generation failed for course_id=%s", course_id)
            raise HTTPException(
                500, f"Tutor generation failed: {type(e).__name__}: {e}"
            )

        if state.tutoring_active or saved_tutoring is not None:
            try:
                storage.save_tutoring_state(
                    cid,
                    topic=state.topic,
                    stage=state.stage,
                    attempts=state.attempts,
                    turn_count=state.turn_count,
                )
            except Exception:
                logger.exception(
                    "Failed to persist tutoring state for conversation_id=%s", cid
                )
                raise HTTPException(
                    500, "The tutor responded, but tutoring progress could not be saved."
                )

    query_lower = text.casefold()
    project_purpose_request = (
        "purpose" in query_lower
        and any(
            project_term in query_lower
            for project_term in (
                "cognigraph", "cognigrpah",
                "this project", "our project", "this system",
            )
        )
    )
    document_request = project_purpose_request or any(
        term in query_lower
        for term in (
            "summarize", "summary", "main objectives", "main components",
            "technologies", "technology stack", "important things",
            "important points", "uploaded proposal", "uploaded pdf",
            "from this pdf", "according to my", "what problem does",
        )
    )
    explicit_visual_request = any(
        term in query_lower
        for term in (
            "make a chart", "plot a chart", "draw a graph",
            "create a graph", "make a graph", "create a diagram",
            "draw a diagram", "visualize", "visualise",
        )
    )
    mode = (
        "text" if body.chat_mode == "normal"
        or (document_request and not explicit_visual_request)
        else classify(text).value
    )
    ctx=[{"source":x.source,"page":x.page,"similarity":x.similarity,"text":x.text} for x in turn.context_used]
    storage.add_message(cid,"user",text,mode=mode,source_query=text)
    storage.add_message(cid,"assistant",turn.content,mode=mode,source_query=text,context_json=json.dumps(ctx))
    if course_id is not None and body.chat_mode == "socratic":
        storage.log_activity(user["id"], course_id, "question_asked", text[:180])
    visual=None
    if body.chat_mode == "socratic" and course_id is not None and mode in ("graph","diagram","concept_map","image"):
        try:
            result=run_visualization(OutputMode(mode),text,context_text(turn.context_used),get_vectorstore(body.course_id).get_all_documents)
            visual={"kind":result.kind,"mermaid":result.mermaid_source,"image":fig_png(result.figure),"message":result.image_message,"placeholder":result.is_placeholder}
        except Exception: visual=None
    return {
        "conversation_id": cid,
        "answer": turn.content,
        "mode": mode,
        "sources": ctx,
        "visualization": visual,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "tutoring": (
            {
                "stage": state.stage,
                "attempts": state.attempts,
                "turn_count": state.turn_count,
                "topic": state.topic,
            }
            if state.tutoring_active or saved_tutoring is not None
            else None
        ),
    }

@app.get("/api/chats/{conversation_id}/messages")
def messages(conversation_id:int,user=Depends(current_user)):
    conv=storage.get_conversation(conversation_id,user["id"])
    if not conv: raise HTTPException(404,"Conversation not found.")
    return storage.list_messages(conversation_id)

@app.post("/api/actions/explain")
def explain(body:ActionInput,user=Depends(current_user)):
    check_course(body.course_id,user); contexts=retrieve(body.query,course_id=body.course_id)
    if not contexts: raise HTTPException(400,"No relevant course material found. Upload a course PDF or change the topic.")
    result=generate_explanation(engine().chat_model.brain,body.original_response,context_text(contexts))
    return {"answer":result,"sources":[{"source":x.source,"page":x.page,"similarity":x.similarity} for x in contexts]}

@app.post("/api/actions/visualize")
def visualize(body:ActionInput,user=Depends(current_user)):
    check_course(body.course_id,user); mode=classify(body.query)
    if mode==OutputMode.TEXT: mode=OutputMode.DIAGRAM
    contexts=retrieve(body.query,course_id=body.course_id)
    diagram_context=context_text(contexts)
    tutor_explanation=(body.original_response or "").strip()

    # Use the saved assistant explanation as a fallback.
    saved_explanation = ""
    if body.conversation_id:
        conversation = storage.get_conversation(
            body.conversation_id, user["id"]
        )
        if conversation and int(conversation["course_id"]) == int(body.course_id):
            for saved_message in reversed(
                storage.list_messages(body.conversation_id)
            ):
                if saved_message.get("role") == "assistant":
                    saved_explanation = str(
                        saved_message.get("content") or ""
                    ).strip()
                    if saved_explanation:
                        break

    explanations = list(dict.fromkeys(
        item for item in (tutor_explanation, saved_explanation) if item
    ))
    if explanations:
        diagram_context += "\n\nTUTOR EXPLANATION:\n" + "\n\n".join(explanations)
    result=run_visualization(mode,body.query,diagram_context,get_vectorstore(body.course_id).get_all_documents)
    return {"kind":result.kind,"mermaid":result.mermaid_source,"image":fig_png(result.figure),"message":result.image_message,"placeholder":result.is_placeholder}

@app.post("/api/quiz/question")
def quiz_question(body:QuizStart,user=Depends(current_user)):
    check_course(body.course_id,user)
    topic=body.topic.strip()
    if topic:
        # Explicit topics remain PDF-only and use topic-specific retrieval.
        contexts=retrieve(topic,course_id=body.course_id)
        quiz_context=context_text(contexts)
    else:
        # An empty topic requests a hybrid course quiz.
        topic="course overview"
        contexts=sample_course_context(body.course_id, limit=5)
        pdf_context=context_text(contexts)
        chat_context=recent_course_chat_context(
            user["id"],
            body.course_id,
            max_conversations=3,
            max_messages=6,
            max_chars=1800,
        )
        quiz_context=(
            "COURSE PDF MATERIAL (primary reference):\n"
            + pdf_context
        )
        if chat_context:
            quiz_context += (
                "\n\nRECENT SOCRATIC TUTOR CHAT HISTORY "
                "(supplemental learning context):\n"
                + chat_context
            )
        else:
            quiz_context += (
                "\n\nNo recent tutor chat history is available. "
                "Use the PDF material only."
            )

    if not contexts:
        raise HTTPException(400,"No indexed course material is available for this course. Open Course Workspace and verify the PDF is listed under the active course.")

    difficulty=storage.adaptive_difficulty(user["id"],body.course_id,topic)
    previous=[x["question"] for x in storage.recent_quiz_attempts(user["id"],body.course_id,10)]
    try:
        q = generate_quiz_question(
            engine().chat_model.brain,
            topic,
            quiz_context,
            difficulty,
            previous,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "CogniGraph could not generate a valid quiz question. "
                "Please try again; no new quiz attempt was recorded."
            ),
        ) from exc
    data=q.to_dict()
    question_id=secrets.token_urlsafe(24)
    generated_topic = str(data.get("topic") or "").strip()
    generic_topics = {"course overview", "course review", "the current course"}
    if not generated_topic or generated_topic.casefold() in generic_topics:
        generated_topic = str(topic or "Course Review").strip() or "Course Review"

    storage.save_pending_quiz_question(
        question_id=question_id,
        user_id=int(user["id"]),
        course_id=body.course_id,
        topic=generated_topic,
        difficulty=difficulty,
        question=str(data.get("question", "")),
        options=list(data.get("options") or []),
        correct_index=int(q.correct_index),
        explanation=str(q.explanation or ""),
    )
    # Never send the answer key or explanation until an answer is submitted.
    data.pop("correct_index",None)
    data.pop("explanation",None)
    return {
        "question":data,
        "question_id":question_id,
        "stats":storage.quiz_stats(user["id"],body.course_id),
        "next_difficulty":difficulty,
    }


@app.post("/api/quiz/answer")
def quiz_answer(body:QuizAnswer,user=Depends(current_user)):
    check_course(body.course_id,user)
    saved=storage.take_pending_quiz_question(
        body.question_id,int(user["id"]),body.course_id
    )
    if not saved:
        raise HTTPException(400,"This quiz question expired or was already submitted. Generate a new question.")
    options=saved["options"]
    if body.selected_index < 0 or body.selected_index >= len(options):
        raise HTTPException(422,"Selected option is out of range. Generate a new question.")

    correct=(body.selected_index == int(saved["correct_index"]))
    storage.record_quiz_attempt(
        user["id"],body.course_id,saved["topic"],saved["difficulty"],
        saved["question"],options,int(saved["correct_index"]),
        body.selected_index,correct,saved["explanation"],body.hints_used
    )
    storage.log_activity(
        user["id"],body.course_id,"quiz_answered",
        f"{saved['topic']} | {saved['difficulty']} | {'correct' if correct else 'incorrect'}"
    )
    return {
        "correct":correct,
        "correct_index":int(saved["correct_index"]),
        "correct_answer":options[int(saved["correct_index"])],
        "explanation":saved["explanation"],
        "stats":storage.quiz_stats(user["id"],body.course_id),
        "next_difficulty":storage.adaptive_difficulty(user["id"],body.course_id,saved["topic"]),
    }


@app.post("/api/revision")
def revision(body:RevisionInput,user=Depends(current_user)):
    check_course(body.course_id,user)
    requested_topic=body.topic.strip()
    selected_topics=[]
    contexts=[]
    weak_topic_stats=[]

    if requested_topic == "__weak_topics__":
        weak=storage.weak_topics(user["id"],body.course_id,limit=3)
        if not weak:
            raise HTTPException(400,"Complete at least two quiz attempts on a topic before generating weak-topic revision.")
        weak_topic_stats = weak
        selected_topics=[str(item["topic"]) for item in weak]
        seen=set()
        for weak_topic in selected_topics:
            for item in retrieve(weak_topic,course_id=body.course_id):
                key=(item.source,item.page,item.text)
                if key not in seen:
                    seen.add(key)
                    contexts.append(item)
        topic="Personalized revision for weak topics: " + ", ".join(selected_topics)
    else:
        contexts=retrieve(requested_topic,course_id=body.course_id) if requested_topic else sample_course_context(body.course_id, limit=5)
        topic=requested_topic or "course overview"

    if not contexts:
        raise HTTPException(400,"No indexed course material is available for these topics. Upload a course PDF or verify the active course.")

    import re

    all_attempts = storage.recent_quiz_attempts(
        user["id"], body.course_id, limit=100
    )
    incorrect_attempts = [
        a for a in all_attempts if not bool(a.get("is_correct"))
    ]

    stop_words = {
        "the", "and", "for", "from", "with", "using", "use", "only",
        "pdf", "uploaded", "document", "file", "book", "please",
        "help", "me", "my", "i", "to", "of", "in", "on", "about",
        "explain", "revise", "revision", "focus", "concept", "concepts",
        "answered", "incorrectly", "latest", "quiz", "cite", "relevant",
        "page", "pages", "what", "which", "that", "this", "these",
        "those", "from", "based", "according", "course", "material",
    }

    def topic_tokens(value):
        words = re.findall(r"[a-z0-9]+", str(value or "").casefold())
        normalized = set()
        for word in words:
            if len(word) > 4 and word.endswith("ies"):
                word = word[:-3] + "y"
            elif len(word) > 3 and word.endswith("s"):
                word = word[:-1]
            if len(word) > 2 and word not in stop_words:
                normalized.add(word)
        return normalized

    target_topics = selected_topics or (
        [requested_topic]
        if requested_topic and requested_topic != "__weak_topics__"
        else []
    )
    target_sets = [topic_tokens(t) for t in target_topics]
    target_sets = [terms for terms in target_sets if terms]

    def topic_match_score(attempt):
        saved_topic = str(attempt.get("topic") or "")
        saved_terms = topic_tokens(saved_topic)
        if not saved_terms:
            return 0
        for target in target_sets:
            if saved_terms == target:
                return 100
        return max(
            (len(saved_terms & target) for target in target_sets),
            default=0,
        )

    ranked = [
        (topic_match_score(attempt), index, attempt)
        for index, attempt in enumerate(incorrect_attempts)
    ]
    matching = [item for item in ranked if item[0] > 0]

    if matching:
        candidates = [
            attempt for _, _, attempt in
            sorted(matching, key=lambda item: (-item[0], item[1]))
        ]
        history_match_mode = "topic_match"
    else:
        # Preserve personalization when the user's wording differs from the
        # stored topic label. Attempts remain scoped to this user and course.
        candidates = incorrect_attempts
        history_match_mode = "recent_course_mistakes_fallback"

    learner_history = []
    per_topic_counts = {}

    for attempt in candidates:
        topic_name = str(attempt.get("topic", "")).strip() or "Course Review"
        topic_key = topic_name.casefold()
        if per_topic_counts.get(topic_key, 0) >= 3:
            continue

        try:
            options = json.loads(attempt.get("options_json") or "[]")
        except (TypeError, ValueError):
            options = []

        def answer_at(index, fallback):
            try:
                index = int(index)
                return str(options[index]) if 0 <= index < len(options) else fallback
            except (TypeError, ValueError):
                return fallback

        learner_history.append({
            "topic": topic_name,
            "question": str(attempt.get("question", ""))[:400],
            "student_answer": answer_at(
                attempt.get("selected_index"), "No answer recorded"
            ),
            "correct_answer": answer_at(
                attempt.get("correct_index"), "Correct answer unavailable"
            ),
            "saved_explanation": str(attempt.get("explanation", ""))[:600],
            "hints_used": int(attempt.get("hints_used") or 0),
        })
        per_topic_counts[topic_key] = per_topic_counts.get(topic_key, 0) + 1
        if len(learner_history) >= 9:
            break

    print(
        "REVISION_HISTORY "
        f"attempts_seen={len(all_attempts)} "
        f"incorrect={len(incorrect_attempts)} "
        f"selected={len(learner_history)} "
        f"mode={history_match_mode}",
        flush=True,
    )

    quiz_summary = storage.quiz_stats(user["id"], body.course_id)
    quiz_summary["accuracy_percent"] = round(
        float(quiz_summary["accuracy"]) * 100, 1
    )

    topic_stats = [
        {
            "topic": item["topic"],
            "attempts": item["attempts"],
            "correct": item["correct"],
            "incorrect": item["incorrect"],
            "accuracy_percent": round(float(item["accuracy"]) * 100, 1),
        }
        for item in weak_topic_stats
    ]

    result = generate_revision(
        engine().chat_model.brain,
        topic,
        context_text(contexts),
        learner_history=learner_history,
        quiz_stats=quiz_summary,
        topic_stats=topic_stats,
    )
    revision_sources = [
        {"source": item.source, "page": item.page}
        for item in contexts
    ]
    storage.save_revision_sheet(
        user_id=int(user["id"]),
        course_id=body.course_id,
        request_topic=(
            "Weak topics"
            if requested_topic == "__weak_topics__"
            else requested_topic or "Course overview"
        ),
        content=result,
        sources=revision_sources,
        topics=selected_topics,
    )
    storage.log_activity(
        user["id"], body.course_id, "revision_generated", topic
    )
    return {
        "content": result,
        "sources": revision_sources,
        "topics": selected_topics,
    }


@app.get("/api/courses/{course_id}/revision/latest")
def latest_revision(course_id: int, user=Depends(current_user)):
    check_course(course_id, user)
    return {
        "revision": storage.latest_revision_sheet(
            int(user["id"]), course_id
        )
    }


@app.get("/api/courses/{course_id}/weak-topics")
def weak_topics(course_id:int,user=Depends(current_user)):
    check_course(course_id,user)
    return {
        "stats":storage.quiz_stats(user["id"],course_id),
        "difficulty":storage.adaptive_difficulty(user["id"],course_id),
        "topics":storage.weak_topics(user["id"],course_id),
    }



def validate_study_week_start(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="week_start must be a valid date in YYYY-MM-DD format.",
        )

    if parsed.isoformat() != value:
        raise HTTPException(
            status_code=400,
            detail="week_start must be a valid date in YYYY-MM-DD format.",
        )

    return value




def _attach_study_session_progress(saved, user_id: int, course_id: int):
    """Attach persisted completion states to returned plan sessions."""
    if not saved:
        return None

    plan = saved.get("plan")
    if not isinstance(plan, dict):
        return saved

    sessions = plan.get("sessions", [])
    if not isinstance(sessions, list):
        sessions = []
        plan["sessions"] = sessions

    progress = storage.get_study_session_progress(
        user_id, course_id, str(saved["week_start"])
    )

    for session in sessions:
        session["completed"] = bool(
            progress.get(str(session.get("date", "")), False)
        )

    saved["completed_count"] = sum(
        1 for session in sessions if session.get("completed")
    )
    saved["total_sessions"] = len(sessions)
    return saved


@app.post("/api/courses/{course_id}/study-plan/generate")
def generate_course_study_plan(
    course_id: int,
    week_start: str,
    minutes_per_day: int = 30,
    user=Depends(current_user),
):
    check_course(course_id, user)
    week_start = validate_study_week_start(week_start)

    if not 15 <= minutes_per_day <= 120:
        raise HTTPException(
            status_code=400,
            detail="minutes_per_day must be between 15 and 120.",
        )

    user_id = int(user["id"])
    stats = storage.quiz_stats(user_id, course_id)
    weak = storage.weak_topics(user_id, course_id, limit=3)
    recent = storage.recent_quiz_attempts(
        user_id, course_id, limit=100
    )

    try:
        plan = build_weekly_plan(
            week_start=week_start,
            quiz_stats=stats,
            weak_topics=weak,
            recent_attempts=recent,
            minutes_per_day=minutes_per_day,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Keep completed tasks unchanged when regenerating this same period.
    existing = storage.get_study_plan(user_id, course_id, week_start)
    progress = storage.get_study_session_progress(
        user_id, course_id, week_start
    )
    if existing:
        old_sessions = (existing.get("plan") or {}).get("sessions", [])
        old_by_date = {
            str(item.get("date")): item
            for item in old_sessions
            if isinstance(item, dict) and item.get("date")
        }
        merged_sessions = []
        for session in plan.get("sessions", []):
            session_date = str(session.get("date", ""))
            if progress.get(session_date) and session_date in old_by_date:
                preserved = dict(old_by_date[session_date])
                preserved["completed"] = True
                merged_sessions.append(preserved)
            else:
                merged_sessions.append(session)
        plan["sessions"] = merged_sessions

    saved = storage.save_study_plan(
        user_id, course_id, week_start, plan
    )
    storage.log_activity(
        user_id, course_id, "study_plan_generated",
        f"{week_start} | {plan['mode']}",
    )
    return {"study_plan": _attach_study_session_progress(saved, int(user["id"]), course_id)}


@app.get("/api/courses/{course_id}/study-plan")
def get_course_study_plan(
    course_id: int,
    week_start: str,
    user=Depends(current_user),
):
    check_course(course_id, user)
    week_start = validate_study_week_start(week_start)

    saved = storage.get_study_plan(
        int(user["id"]), course_id, week_start
    )
    return {"study_plan": _attach_study_session_progress(saved, int(user["id"]), course_id)}


@app.post("/api/courses/{course_id}/study-plan")
def save_course_study_plan(
    course_id: int,
    body: StudyPlanInput,
    user=Depends(current_user),
):
    check_course(course_id, user)
    week_start = validate_study_week_start(body.week_start)

    saved = storage.save_study_plan(
        int(user["id"]),
        course_id,
        week_start,
        body.plan,
    )
    return {"study_plan": _attach_study_session_progress(saved, int(user["id"]), course_id)}



@app.post("/api/courses/{course_id}/study-plan/session")
def update_study_session(
    course_id: int,
    body: StudySessionCompletionInput,
    user=Depends(current_user),
):
    check_course(course_id, user)
    week_start = validate_study_week_start(body.week_start)

    try:
        session_day = date.fromisoformat(body.session_date)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="session_date must be a valid YYYY-MM-DD date.",
        ) from exc

    if session_day.isoformat() != body.session_date:
        raise HTTPException(
            status_code=400,
            detail="session_date must use YYYY-MM-DD format.",
        )

    offset = (session_day - date.fromisoformat(week_start)).days
    if offset < 0 or offset > 6:
        raise HTTPException(
            status_code=400,
            detail="The session date must fall inside the selected week.",
        )

    user_id = int(user["id"])
    saved = storage.get_study_plan(user_id, course_id, week_start)
    if not saved:
        raise HTTPException(
            status_code=404,
            detail="Generate a study plan for this week first.",
        )

    sessions = (saved.get("plan") or {}).get("sessions", [])
    if not any(
        str(session.get("date", "")) == body.session_date
        for session in sessions
    ):
        raise HTTPException(
            status_code=400,
            detail="This date is not a session in the saved study plan.",
        )

    storage.set_study_session_completion(
        user_id,
        course_id,
        week_start,
        body.session_date,
        body.completed,
    )

    progress = storage.get_study_session_progress(
        user_id, course_id, week_start
    )
    completed_count = sum(
        1 for session in sessions
        if progress.get(str(session.get("date", "")), False)
    )

    storage.log_activity(
        user_id,
        course_id,
        "study_session_completed" if body.completed else "study_session_reopened",
        body.session_date,
    )

    return {
        "session_date": body.session_date,
        "completed": bool(body.completed),
        "completed_count": completed_count,
        "total_sessions": len(sessions),
    }


@app.get("/api/courses/{course_id}/dashboard")
def dashboard(course_id:int,user=Depends(current_user)):
    check_course(course_id,user); return {**storage.dashboard(user["id"],course_id),"quiz":storage.quiz_stats(user["id"],course_id),"weak_topics":storage.weak_topics(user["id"],course_id)}

@app.get("/api/courses/{course_id}/visualizations")
def visualizations(course_id:int,user=Depends(current_user)):
    check_course(course_id,user); return storage.list_visualizations(user["id"],course_id)

@app.get("/api/courses/{course_id}/visualizations/{viz_id}/content")
def visualization_content(course_id: int, viz_id: int, download: bool = False, user=Depends(current_user)):
    """Return a saved image owned by the authenticated user and selected course."""
    check_course(course_id, user)
    rows = storage.list_visualizations(user["id"], course_id)
    row = next((item for item in rows if int(item["id"]) == viz_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Visualization not found")
    file_path = row.get("file_path")
    if not file_path or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Saved image file not found")
    ext = os.path.splitext(file_path)[1].lower()
    media_type = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "application/octet-stream"
    filename = os.path.basename(file_path) if download else None
    return FileResponse(file_path, media_type=media_type, filename=filename)


@app.delete("/api/visualizations/{viz_id}")
def remove_visualization(viz_id:int,user=Depends(current_user)):
    storage.delete_visualization(viz_id,user["id"]); return {"ok":True}

@app.post("/api/visualizations")
def save_viz(body:SaveVizInput,user=Depends(current_user)):
    check_course(body.course_id,user)
    image_bytes=base64.b64decode(body.image_base64) if body.image_base64 else None
    extension="png" if image_bytes else ("mmd" if body.kind=="diagram" else "txt")
    vid=storage.save_visualization(user["id"],body.course_id,None,body.kind,body.title,body.query,file_bytes=image_bytes,extension=extension,source_text=(body.source_text or None) if image_bytes is None else None)
    return {"id":vid}
