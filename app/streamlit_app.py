
"""
CogniGraph — Phase 5 Workspace UI.

Adds persistent local:
- Login / registration
- Course workspaces
- Chat history
- Saved visualizations
- Progress dashboard

The existing Socratic/RAG/router/visualization pipeline remains intact.
"""
from __future__ import annotations

import io, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import streamlit.components.v1 as components

from auth import ensure_auth_state, login_screen
from config import CONFIG, UPLOAD_DIR, DATA_DIR
from ingestion.pdf_processor import process_pdf
from llm.socratic_engine import ConversationState, SocraticEngine, TutorTurn
from orchestration.visualization_chain import VisualizationResult, run_visualization
from rag.vectorstore import get_vectorstore
from rag.retriever import RetrievedContext, retrieve
from router.multimodal_router import OutputMode, classify, explain_classification
from learning import generate_explanation, generate_quiz_question, generate_revision
from storage import (
    add_message, add_source, create_conversation, create_course, dashboard,
    delete_conversation, delete_visualization, get_course, list_conversations,
    list_courses, list_messages, list_sources as db_list_sources, list_visualizations,
    adaptive_difficulty, log_activity, quiz_stats, record_quiz_attempt, rename_conversation, save_visualization, weak_topics,
)

st.set_page_config(page_title="CogniGraph — Socratic AI Tutor", page_icon="🧠", layout="wide")

MERMAID_TEMPLATE = """
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<div class="mermaid">{diagram}</div>
<script>mermaid.initialize({{ startOnLoad: true }});</script>
"""

def _user_id(): return st.session_state.user["id"]
def _course_id(): return st.session_state.course_id

def _init_app_state():
    ensure_auth_state()
    if not st.session_state.authenticated:
        return
    if not st.session_state.get("engine"):
        st.session_state.engine = SocraticEngine()
    st.session_state.setdefault("conversation", ConversationState())
    st.session_state.setdefault("conversation_id", None)
    st.session_state.setdefault("page", "Tutor")
    st.session_state.setdefault("turn_explanations", {})
    st.session_state.setdefault("turn_visuals", {})
    st.session_state.setdefault("quiz_active", False)
    st.session_state.setdefault("quiz_question", None)
    st.session_state.setdefault("quiz_answered", False)
    st.session_state.setdefault("quiz_selected", None)
    st.session_state.setdefault("quiz_hint_level", 0)
    st.session_state.setdefault("quiz_score", 0)
    st.session_state.setdefault("quiz_total", 0)
    st.session_state.setdefault("quiz_topic", "")
    st.session_state.setdefault("quiz_history", [])
    st.session_state.setdefault("revision_content", "")
    _ensure_course()

def _ensure_course():
    courses = list_courses(_user_id())
    if not courses:
        # Should normally be created by login_screen, but keeps direct recovery safe.
        from storage import get_or_create_demo_course
        course = get_or_create_demo_course(_user_id())
        courses = [course]
    valid = {c["id"] for c in courses}
    if st.session_state.course_id not in valid:
        st.session_state.course_id = courses[0]["id"]
        st.session_state.conversation_id = None

def _reset_learning_state():
    st.session_state.quiz_active = False
    st.session_state.quiz_question = None
    st.session_state.quiz_answered = False
    st.session_state.quiz_selected = None
    st.session_state.quiz_hint_level = 0
    st.session_state.quiz_score = 0
    st.session_state.quiz_total = 0
    st.session_state.quiz_topic = ""
    st.session_state.quiz_history = []
    st.session_state.quiz_error = ""
    st.session_state.revision_content = ""

def _new_conversation():
    cid = create_conversation(_user_id(), _course_id(), "New chat")
    st.session_state.conversation_id = cid
    st.session_state.conversation = ConversationState()
    st.session_state.turn_explanations = {}
    st.session_state.turn_visuals = {}
    st.session_state.page = "Tutor"

def _load_conversation(cid: int):
    rows = list_messages(cid)
    state = ConversationState()
    for row in rows:
        contexts = []
        try:
            raw = json.loads(row.get("context_json") or "[]")
            contexts = [RetrievedContext(**x) for x in raw]
        except Exception:
            contexts = []
        state.add(TutorTurn(
            role=row["role"], content=row["content"], context_used=contexts,
            mode=row.get("mode") or "text", source_query=row.get("source_query") or ""
        ))
    st.session_state.conversation_id = cid
    st.session_state.conversation = state
    st.session_state.turn_explanations = {}
    st.session_state.turn_visuals = {}

def _ensure_active_conversation():
    cid = st.session_state.get("conversation_id")
    from storage import get_conversation
    if cid and get_conversation(cid, _user_id()) is None:
        st.session_state.conversation_id = None
    if not st.session_state.get("conversation_id"):
        _new_conversation()

def _context_json(turn: TutorTurn) -> str:
    return json.dumps([{
        "text": c.text, "source": c.source, "page": c.page, "similarity": c.similarity
    } for c in turn.context_used])

def _figure_to_png_bytes(figure) -> bytes | None:
    if figure is None: return None
    buf = io.BytesIO()
    try:
        figure.savefig(buf, format="png", dpi=180, bbox_inches="tight")
        buf.seek(0); return buf.read()
    except Exception:
        return None

def _result_title(result: VisualizationResult) -> str:
    return {"chart":"📊 Visualization","diagram":"🧩 Visualization",
            "concept_map":"🕸️ Visualization","image":"🖼️ Visualization"}.get(result.kind, "🔎 Visualization")

def _save_visualization(result, query, conversation_id):
    if result.kind == "chart":
        data = _figure_to_png_bytes(result.figure)
        if not data: return False
        save_visualization(_user_id(), _course_id(), conversation_id, "chart",
                           f"Chart — {query[:70]}", query, file_bytes=data)
    elif result.kind == "concept_map":
        data = _figure_to_png_bytes(result.figure)
        if not data: return False
        save_visualization(_user_id(), _course_id(), conversation_id, "concept_map",
                           f"Concept Map — {query[:70]}", query, file_bytes=data)
    elif result.kind == "diagram" and result.mermaid_source:
        save_visualization(_user_id(), _course_id(), conversation_id, "diagram",
                           f"Diagram — {query[:70]}", query,
                           source_text=result.mermaid_source, extension="mmd")
    elif result.kind == "image" and result.image_bytes:
        save_visualization(_user_id(), _course_id(), conversation_id, "image",
                           f"Image — {query[:70]}", query, file_bytes=result.image_bytes)
    else:
        return False
    log_activity(_user_id(), _course_id(), "visualization_saved", result.kind)
    return True

def _visualization_dialog(result):
    st.markdown(f"### {_result_title(result)}")
    if result.kind == "chart":
        if result.is_placeholder: st.warning("Illustrative example — no matching numeric data was found.")
        st.pyplot(result.figure, clear_figure=False, use_container_width=True)
        data=_figure_to_png_bytes(result.figure)
        if data: st.download_button("⬇️ Download PNG",data=data,file_name="cognigraph_chart.png",mime="image/png",use_container_width=True)
    elif result.kind == "diagram":
        components.html(MERMAID_TEMPLATE.format(diagram=result.mermaid_source),height=600,scrolling=True)
        st.download_button("⬇️ Download Mermaid Source",data=result.mermaid_source,file_name="cognigraph_diagram.mmd",mime="text/plain",use_container_width=True)
    elif result.kind == "concept_map":
        if result.is_placeholder: st.warning("Upload course material to generate a real concept map.")
        st.pyplot(result.figure, clear_figure=False, use_container_width=True)
        data=_figure_to_png_bytes(result.figure)
        if data: st.download_button("⬇️ Download PNG",data=data,file_name="cognigraph_concept_map.png",mime="image/png",use_container_width=True)
    elif result.kind == "image":
        if result.image_bytes:
            st.image(result.image_bytes,use_container_width=True)
        else: st.info(result.image_message)

@st.dialog("Visualization", width="large")
def _dialog(result): _visualization_dialog(result)

def _render_visualization(result, turn_index=None, query="", conversation_id=None):
    if not result: return
    cols=st.columns([2,2,6])
    if turn_index is not None and cols[0].button(f"🔎 Open {_result_title(result)}",key=f"open_viz_{turn_index}_{result.kind}",use_container_width=True):
        _dialog(result)
    if cols[1].button("💾 Save",key=f"save_viz_{turn_index}_{result.kind}",use_container_width=True):
        if _save_visualization(result,query,conversation_id):
            st.toast("Visualization saved to this course.")
        else: st.warning("This visualization cannot be saved because it has no renderable output.")
    if result.kind=="chart":
        if result.is_placeholder: st.warning("Illustrative example — no matching numeric data was found in retrieved context.")
        st.pyplot(result.figure,clear_figure=False,use_container_width=True)
    elif result.kind=="diagram":
        components.html(MERMAID_TEMPLATE.format(diagram=result.mermaid_source),height=460,scrolling=True)
        with st.expander("Mermaid source"): st.code(result.mermaid_source,language="text")
    elif result.kind=="concept_map":
        if result.is_placeholder: st.warning("Upload course material to generate a real concept map.")
        st.pyplot(result.figure,clear_figure=False,use_container_width=True)
    elif result.kind=="image":
        if result.image_bytes: st.image(result.image_bytes,use_container_width=True)
        else: st.info(result.image_message)

def _clean_visualization_response(content, mode, has_context):
    if not has_context or not content: return content
    lowered=content.lower()
    phrases=("i can't access external files","i cannot access external files","please provide the scores",
             "please provide the data","i don't see any uploaded material","i do not see any uploaded material",
             "i don't see any course material","i do not see any course material")
    if not any(p in lowered for p in phrases): return content
    return {
        OutputMode.GRAPH:"I found the relevant numerical information in the uploaded course material and generated the requested chart below.",
        OutputMode.DIAGRAM:"I found the relevant workflow information in the uploaded course material and generated the requested diagram below.",
        OutputMode.CONCEPT_MAP:"I found the relevant concepts in the uploaded course material and generated the requested concept map below."
    }.get(mode,content)

def _feedback_widget(turn_index):
    a,b,_=st.columns([1,1,8])
    if a.button("👍",key=f"fb_{turn_index}_up"):
        _log_feedback(turn_index,"up"); st.toast("Thanks for the feedback!")
    if b.button("👎",key=f"fb_{turn_index}_down"):
        _log_feedback(turn_index,"down"); st.toast("Thanks — noted.")

def _log_feedback(turn_index,rating):
    turn=st.session_state.conversation.turns[turn_index]
    log_activity(_user_id(),_course_id(),"feedback",rating)
    path=DATA_DIR/"feedback.jsonl"
    record={"timestamp":time.time(),"rating":rating,"mode":turn.mode,"query":turn.source_query,"response":turn.content}
    with open(path,"a",encoding="utf-8") as f: f.write(json.dumps(record)+"\n")


def _course_context(query: str) -> list[RetrievedContext]:
    return retrieve(query or "course material", top_k=5, course_id=_course_id())


def _context_text(contexts: list[RetrievedContext]) -> str:
    return "\n\n".join(f"[{c.source}, p.{c.page}]\n{c.text}" for c in contexts)


def _prepare_quiz_question():
    topic = st.session_state.quiz_topic.strip() or "course material"
    contexts = _course_context(topic)
    if not contexts:
        st.session_state.quiz_question = None
        st.session_state.quiz_error = "No relevant course material was found. Upload a course PDF or choose a topic covered by your material."
        return False
    difficulty = adaptive_difficulty(_user_id(), _course_id(), topic)
    previous = [q for q in st.session_state.quiz_history[-5:]]
    question = generate_quiz_question(
        st.session_state.engine.chat_model.brain,
        topic,
        _context_text(contexts),
        difficulty,
        previous_questions=previous,
    )
    st.session_state.quiz_question = question
    st.session_state.quiz_question_context = contexts
    st.session_state.quiz_question_difficulty = difficulty
    st.session_state.quiz_answered = False
    st.session_state.quiz_selected = None
    st.session_state.quiz_hint_level = 0
    st.session_state.quiz_error = ""
    st.session_state.quiz_history.append(question.question)
    return True


def _quiz_mode():
    st.title("📝 Quiz Mode")
    st.caption("Practice from your uploaded course material. Difficulty adapts from your recent quiz performance.")
    stats = quiz_stats(_user_id(), _course_id())
    cols = st.columns(4)
    cols[0].metric("Quiz attempts", stats["attempts"])
    cols[1].metric("Correct", stats["correct"])
    cols[2].metric("Accuracy", f"{stats['accuracy']*100:.0f}%")
    cols[3].metric("Next difficulty", adaptive_difficulty(_user_id(), _course_id(), st.session_state.quiz_topic or None).title())

    topic = st.text_input("Topic (optional)", value=st.session_state.quiz_topic, placeholder="e.g. Logistic Regression")
    st.session_state.quiz_topic = topic
    start = st.button("🚀 Start / Restart 5-question quiz", type="primary", use_container_width=True)
    if start:
        st.session_state.quiz_active = True
        st.session_state.quiz_score = 0
        st.session_state.quiz_total = 0
        st.session_state.quiz_history = []
        st.session_state.quiz_topic = topic.strip() or "course material"
        _prepare_quiz_question()
        st.rerun()

    if st.session_state.get("quiz_error"):
        st.warning(st.session_state.quiz_error)
    if not st.session_state.quiz_active:
        st.info("Start a quiz to practice the current course material.")
        return

    question = st.session_state.quiz_question
    if question is None:
        st.warning("A quiz question could not be prepared yet. Try starting the quiz again.")
        return

    display_number = st.session_state.quiz_total if st.session_state.quiz_answered else st.session_state.quiz_total + 1
    st.markdown(f"### Question {display_number} of 5")
    st.caption(f"Topic: **{question.topic}** · Adaptive difficulty: **{question.difficulty.title()}**")
    st.write(question.question)
    answer = st.radio("Choose one answer", question.options, key=f"quiz_answer_{st.session_state.quiz_total}_{hash(question.question)}")

    if not st.session_state.quiz_answered:
        b1, b2 = st.columns([1, 1])
        if b1.button("💡 I'm Stuck", use_container_width=True):
            st.session_state.quiz_hint_level = min(3, st.session_state.quiz_hint_level + 1)
            st.rerun()
        if b2.button("✅ Submit answer", type="primary", use_container_width=True):
            selected_index = question.options.index(answer)
            correct = selected_index == question.correct_index
            hints_used = st.session_state.quiz_hint_level
            record_quiz_attempt(
                _user_id(), _course_id(), question.topic, question.difficulty,
                question.question, question.options, question.correct_index,
                selected_index, correct, question.explanation, hints_used,
            )
            st.session_state.quiz_selected = selected_index
            st.session_state.quiz_answered = True
            st.session_state.quiz_total += 1
            if correct:
                st.session_state.quiz_score += 1
            log_activity(_user_id(), _course_id(), "quiz_answered", f"{question.topic} | {question.difficulty} | {'correct' if correct else 'incorrect'}")
            st.rerun()

    if st.session_state.quiz_hint_level:
        st.info("**Hint {}:** {}".format(
            st.session_state.quiz_hint_level,
            question.hints[st.session_state.quiz_hint_level - 1],
        ))

    if st.session_state.quiz_answered:
        selected_index = st.session_state.quiz_selected
        correct = selected_index == question.correct_index
        if correct:
            st.success("✅ Correct")
        else:
            st.error(f"❌ Not quite. The correct answer is: **{question.options[question.correct_index]}**")
        st.markdown("**Why:** " + question.explanation)

        if st.session_state.quiz_total >= 5:
            accuracy = st.session_state.quiz_score / max(1, st.session_state.quiz_total)
            st.success(f"Quiz complete — {st.session_state.quiz_score}/5 ({accuracy*100:.0f}%).")
            st.caption(f"Your next adaptive difficulty is **{adaptive_difficulty(_user_id(), _course_id(), st.session_state.quiz_topic).title()}**.")
            if st.button("🔄 Start another quiz", use_container_width=True):
                st.session_state.quiz_active = False
                st.session_state.quiz_question = None
                st.rerun()
        else:
            if st.button("➡️ Next question", type="primary", use_container_width=True):
                _prepare_quiz_question()
                st.rerun()


def _revision_mode():
    st.title("📖 Revision Mode")
    st.caption("Turn your course material into a focused revision sheet grounded in your uploaded sources.")
    weak = weak_topics(_user_id(), _course_id())
    default_topic = weak[0]["topic"] if weak else ""
    topic = st.text_input("What do you want to revise?", value=default_topic, placeholder="e.g. K-Means clustering")
    if weak:
        st.caption("Detected topics that may need more practice:")
        st.write(" · ".join(f"{x['topic']} ({x['accuracy']*100:.0f}% accuracy)" for x in weak[:5]))
    if st.button("📚 Generate revision sheet", type="primary", use_container_width=True):
        contexts = _course_context(topic or "course material")
        if not contexts:
            st.session_state.revision_content = ""
            st.warning("No relevant course material was found for this topic.")
        else:
            with st.spinner("Building your revision sheet..."):
                st.session_state.revision_content = generate_revision(
                    st.session_state.engine.chat_model.brain,
                    topic or "course material",
                    _context_text(contexts),
                )
            log_activity(_user_id(), _course_id(), "revision_generated", topic or "course material")
    if st.session_state.revision_content:
        st.markdown(st.session_state.revision_content)
        st.caption("Revision content is generated from the retrieved course material for this course.")


def _weak_topics_page():
    st.title("🎯 Weak-topic Detection")
    st.caption("Topics are flagged from your recorded quiz attempts. A topic appears here after at least two attempts.")
    stats = quiz_stats(_user_id(), _course_id())
    if stats["attempts"]:
        st.metric("Overall quiz accuracy", f"{stats['accuracy']*100:.0f}%")
    rows = weak_topics(_user_id(), _course_id())
    if not rows:
        st.info("Not enough quiz data yet. Complete at least two attempts on a topic to detect a learning gap.")
        return
    for row in rows:
        with st.container(border=True):
            st.markdown(f"### {row['topic']}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Attempts", row["attempts"])
            c2.metric("Accuracy", f"{row['accuracy']*100:.0f}%")
            c3.metric("Incorrect", row["incorrect"])
            st.progress(row["accuracy"], text=f"Accuracy: {row['accuracy']*100:.0f}%")
            st.caption("Use Revision Mode for a targeted review, then return to Quiz Mode to practice this topic again.")

def _sidebar():
    st.sidebar.title("🧠 CogniGraph")
    st.sidebar.caption('"Don\'t Give Answers. Teach Thinking."')
    user=st.session_state.user
    st.sidebar.write(f"👤 **{user['username']}**")
    if st.sidebar.button("🚪 Logout",use_container_width=True):
        for key in ("authenticated","user","course_id","conversation_id","conversation","engine","turn_explanations","turn_visuals","quiz_question","revision_content"):
            st.session_state.pop(key,None)
        st.rerun()

    courses=list_courses(_user_id())
    names=[c["name"] for c in courses]
    current=get_course(_course_id(),_user_id())
    idx=names.index(current["name"]) if current and current["name"] in names else 0
    selected=st.sidebar.selectbox("Course workspace",names,index=idx)
    selected_course=courses[names.index(selected)]
    if selected_course["id"] != _course_id():
        st.session_state.course_id=selected_course["id"]; st.session_state.conversation_id=None; st.session_state.conversation=ConversationState(); st.session_state.turn_explanations={}; st.session_state.turn_visuals={}; _reset_learning_state(); st.rerun()

    with st.sidebar.expander("➕ Create course"):
        name=st.text_input("Course name",key="new_course_name")
        desc=st.text_input("Description",key="new_course_desc")
        if st.button("Create",use_container_width=True):
            course,error=create_course(_user_id(),name,desc)
            if error: st.error(error)
            else:
                st.session_state.course_id=course["id"]; st.session_state.conversation_id=None
                st.session_state.conversation=ConversationState(); st.session_state.turn_explanations={}; st.session_state.turn_visuals={}; _reset_learning_state(); st.rerun()

    st.sidebar.markdown("### Course Materials")
    uploaded=st.sidebar.file_uploader("Upload a course PDF",type=["pdf"],key="course_pdf")
    if uploaded is not None:
        raw=uploaded.getvalue()
        signature=f"{_course_id()}:{uploaded.name}:{len(raw)}:{raw[:64]}"
        if st.session_state.get("last_upload_signature") != signature:
            course_upload_dir = UPLOAD_DIR / str(_course_id())
            course_upload_dir.mkdir(parents=True, exist_ok=True)
            dest = course_upload_dir / uploaded.name
            dest.write_bytes(raw)
            with st.status(f"Indexing {uploaded.name}...",expanded=True) as status:
                status.write("📄 Extracting PDF text...")
                chunks=process_pdf(dest)
                status.write(f"✂️ Created {len(chunks)} text chunks.")
                status.write("🧠 Generating embeddings and storing in this course workspace...")
                get_vectorstore(_course_id()).add_chunks(chunks)
                add_source(_course_id(),uploaded.name,len(chunks))
                log_activity(_user_id(),_course_id(),"material_uploaded",uploaded.name)
                st.session_state.last_upload_signature=signature
                status.update(label=f"✅ {uploaded.name} indexed",state="complete",expanded=False)
    sources=db_list_sources(_course_id())
    if sources:
        st.sidebar.caption("Sources in this course")
        for s in sources: st.sidebar.markdown(f"- {s['filename']} ({s['chunks']} chunks)")
    else: st.sidebar.info("No material in this course yet.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Chat history")
    chats=list_conversations(_user_id(),_course_id())
    if st.sidebar.button("➕ New chat",use_container_width=True):
        _new_conversation(); st.rerun()
    for chat in chats[:12]:
        label=chat["title"] or "New chat"
        if st.sidebar.button(label,key=f"chat_{chat['id']}",use_container_width=True):
            _load_conversation(chat["id"]); st.session_state.page="Tutor"; st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Navigate")
    for label in ("Tutor","Quiz Mode","Revision Mode","Weak Topics","Course Workspace","Saved Visualizations","Progress Dashboard","Debug / Demo"):
        if st.sidebar.button(label,key=f"nav_{label}",use_container_width=True):
            st.session_state.page=label; st.rerun()

def _chat_tab():
    _ensure_active_conversation()
    conversation=st.session_state.conversation
    engine=st.session_state.engine
    for i,turn in enumerate(conversation.turns):
        with st.chat_message(turn.role):
            st.markdown(turn.content)
            if turn.role=="assistant":
                action_cols=st.columns([1,1,6])
                if action_cols[0].button("✨ Explain", key=f"explain_{i}", use_container_width=True):
                    context_text="\n\n".join(c.text for c in turn.context_used)
                    with st.spinner("Preparing a simpler explanation..."):
                        st.session_state.turn_explanations[i]=generate_explanation(
                            engine.chat_model.brain, turn.content, context_text
                        )
                    log_activity(_user_id(), _course_id(), "explain_clicked", turn.source_query[:200])
                if action_cols[1].button("🧩 Visualize", key=f"visualize_{i}", use_container_width=True):
                    context_text="\n".join(c.text for c in turn.context_used)
                    requested=classify("visualize " + (turn.source_query or turn.content))
                    if requested == OutputMode.TEXT:
                        requested=OutputMode.DIAGRAM
                    with st.spinner("Creating a visualization..."):
                        st.session_state.turn_visuals[i]=run_visualization(
                            requested, turn.source_query or turn.content, context_text,
                            get_vectorstore(_course_id()).get_all_documents
                        )
                    log_activity(_user_id(), _course_id(), "visualize_clicked", turn.source_query[:200])
                if i in st.session_state.turn_explanations:
                    with st.expander("✨ Simpler explanation", expanded=True):
                        st.markdown(st.session_state.turn_explanations[i])
                if i in st.session_state.turn_visuals:
                    _render_visualization(st.session_state.turn_visuals[i], 10000+i, turn.source_query, st.session_state.conversation_id)
                if turn.mode!="text":
                    context_text="\n".join(c.text for c in turn.context_used)
                    result=run_visualization(OutputMode(turn.mode),turn.source_query,context_text,get_vectorstore(_course_id()).get_all_documents)
                    _render_visualization(result,i,turn.source_query,st.session_state.conversation_id)
                _feedback_widget(i)

    query=st.chat_input("Ask about your course material...")
    if not query: return
    with st.chat_message("user"): st.markdown(query)
    mode=classify(query)
    with st.chat_message("assistant"):
        with st.status("CogniGraph is working...",expanded=True) as status:
            status.write("🔎 Analyzing your question...")
            status.write(f"🧭 Router selected: {mode.value} mode")
            status.write("📚 Retrieving relevant course material...")
            status.write("🧠 Generating Socratic response...")
            turn=engine.ask(conversation,query,course_id=_course_id())
            turn.mode=mode.value
            turn.content=_clean_visualization_response(turn.content,mode,bool(turn.context_used))
            context_text="\n".join(c.text for c in turn.context_used)
            result=None
            if mode!=OutputMode.TEXT:
                status.write("🎨 Generating visualization...")
                result=run_visualization(mode,query,context_text,get_vectorstore(_course_id()).get_all_documents)
            status.update(label="✅ Response ready",state="complete",expanded=False)
        st.markdown(turn.content)
        current_index=len(conversation.turns)-1
        action_cols=st.columns([1,1,6])
        if action_cols[0].button("✨ Explain", key=f"explain_current_{current_index}", use_container_width=True):
            with st.spinner("Preparing a simpler explanation..."):
                st.session_state.turn_explanations[current_index]=generate_explanation(
                    engine.chat_model.brain, turn.content, context_text
                )
            log_activity(_user_id(), _course_id(), "explain_clicked", turn.source_query[:200])
        if action_cols[1].button("🧩 Visualize", key=f"visualize_current_{current_index}", use_container_width=True):
            requested=classify("visualize " + (turn.source_query or turn.content))
            if requested == OutputMode.TEXT:
                requested=OutputMode.DIAGRAM
            with st.spinner("Creating a visualization..."):
                st.session_state.turn_visuals[current_index]=run_visualization(
                    requested, turn.source_query or turn.content, context_text,
                    get_vectorstore(_course_id()).get_all_documents
                )
            log_activity(_user_id(), _course_id(), "visualize_clicked", turn.source_query[:200])
        if current_index in st.session_state.turn_explanations:
            with st.expander("✨ Simpler explanation", expanded=True):
                st.markdown(st.session_state.turn_explanations[current_index])
        if current_index in st.session_state.turn_visuals:
            _render_visualization(st.session_state.turn_visuals[current_index], 20000+current_index, turn.source_query, st.session_state.conversation_id)
        if mode!=OutputMode.TEXT:
            st.caption(f"Router selected: **{mode.value}** mode")
            _render_visualization(result,len(conversation.turns)-1,query,st.session_state.conversation_id)
        if turn.context_used:
            with st.expander(f"📚 Sources ({len(turn.context_used)})"):
                for c in turn.context_used:
                    st.markdown(f"**📄 {c.source}** — page {c.page}  \nSimilarity: `{c.similarity:.2f}`")
        # Persist both turns after successful generation.
        if len(conversation.turns)>=2:
            user_turn=conversation.turns[-2]
            add_message(st.session_state.conversation_id,"user",user_turn.content,"text",user_turn.content,"[]")
            add_message(st.session_state.conversation_id,"assistant",turn.content,turn.mode,turn.source_query,_context_json(turn))
            log_activity(_user_id(),_course_id(),"question_asked",query[:200])
            # Give a useful automatic title after the first question.
            chats=list_conversations(_user_id(),_course_id())
            current=next((x for x in chats if x["id"]==st.session_state.conversation_id),None)
            if current and current["title"]=="New chat":
                rename_conversation(current["id"],_user_id(),query[:60])
        _feedback_widget(len(conversation.turns)-1)

def _course_workspace():
    course=get_course(_course_id(),_user_id())
    st.title("📚 Course Workspace")
    st.caption("A dedicated workspace for this course: material, chats, saved visuals and activity.")
    st.subheader(course["name"])
    if course["description"]: st.write(course["description"])
    d=dashboard(_user_id(),_course_id())
    qstats=quiz_stats(_user_id(),_course_id())
    a,b,c,dcol,e=st.columns(5)
    a.metric("Questions",d["questions"]); b.metric("Chats",d["chats"]); c.metric("Visualizations",d["visuals"]); dcol.metric("Course PDFs",d["sources"]); e.metric("Quiz accuracy", f"{qstats['accuracy']*100:.0f}%")
    st.markdown("### Sources")
    sources=db_list_sources(_course_id())
    if sources:
        for s in sources: st.write(f"📄 **{s['filename']}** — {s['chunks']} chunks")
    else: st.info("Upload your first course PDF from the sidebar.")

def _saved_visualizations():
    st.title("💾 Saved Visualizations")
    items=list_visualizations(_user_id(),_course_id())
    if not items: st.info("No saved visualizations yet. Use the Save button under a generated visualization."); return
    for item in items:
        with st.container(border=True):
            cols=st.columns([5,2,1])
            cols[0].markdown(f"**{item['title']}**  \n`{item['kind']}` • {time.strftime('%Y-%m-%d %H:%M',time.localtime(item['created_at']))}")
            if item["file_path"] and Path(item["file_path"]).exists():
                if item["kind"]=="diagram":
                    source=Path(item["file_path"]).read_text(encoding="utf-8")
                    with cols[1].expander("Open"):
                        components.html(MERMAID_TEMPLATE.format(diagram=source),height=300,scrolling=True)
                    cols[1].download_button("Download",data=source,file_name=Path(item["file_path"]).name,mime="text/plain",key=f"dl_{item['id']}")
                else:
                    data=Path(item["file_path"]).read_bytes()
                    with cols[1].expander("Open"):
                        st.image(data,use_container_width=True)
                    cols[1].download_button("Download",data=data,file_name=Path(item["file_path"]).name,mime="image/png",key=f"dl_{item['id']}")
            if cols[2].button("Delete",key=f"del_viz_{item['id']}"):
                delete_visualization(item["id"],_user_id()); st.rerun()

def _progress_dashboard():
    st.title("📈 Progress Dashboard")
    st.caption("This dashboard reports real activity from your CogniGraph workspace; it does not pretend activity is the same as mastery.")
    d=dashboard(_user_id(),_course_id())
    cols=st.columns(5)
    cols[0].metric("Questions asked",d["questions"])
    cols[1].metric("Chats",d["chats"])
    cols[2].metric("Visualizations",d["visuals"])
    cols[3].metric("Course PDFs",d["sources"])
    cols[4].metric("Quiz accuracy",f"{quiz_stats(_user_id(),_course_id())['accuracy']*100:.0f}%")
    st.markdown("### Learning activity")
    if d["modes"]:
        import pandas as pd
        mode_counts={x["mode"]:x["n"] for x in d["modes"]}
        st.bar_chart(pd.DataFrame({"Responses":mode_counts}))
    else: st.info("Ask questions to start building your activity profile.")
    st.markdown("### Recent activity")
    if d["recent"]:
        for r in d["recent"]:
            st.write(f"• **{r['event_type'].replace('_',' ').title()}** — {r['detail']}  \n  {time.strftime('%d %b %Y %H:%M',time.localtime(r['created_at']))}")
    else: st.info("No activity recorded yet.")
    st.markdown("### Honest progress indicator")
    # A transparent activity indicator, not a fabricated mastery score.
    score=min(100,d["questions"]*5 + d["sources"]*10 + d["visuals"]*3)
    st.progress(score/100,text=f"Workspace engagement: {score}%")
    st.caption("Engagement is based on questions, uploaded material and saved visuals. Quizzes/mastery scoring should be added before calling this a true learning score.")

def _debug_tab():
    st.subheader("Router debug")
    sample=st.text_input("Try a query",value="How do these course topics relate to each other?")
    if sample: st.json(explain_classification(sample))
    st.subheader("Corpus preview")
    docs=get_vectorstore(_course_id()).get_all_documents()
    st.write(f"{len(docs)} chunks in the selected course.")
    log_path=DATA_DIR/"feedback.jsonl"
    if log_path.exists():
        records=[json.loads(x) for x in log_path.read_text(encoding="utf-8").splitlines() if x.strip()]
        st.write(f"{len(records)} feedback entries")

def main():
    _init_app_state()
    if not st.session_state.authenticated:
        login_screen(); return
    _sidebar()
    page=st.session_state.page
    if page=="Tutor": _chat_tab()
    elif page=="Quiz Mode": _quiz_mode()
    elif page=="Revision Mode": _revision_mode()
    elif page=="Weak Topics": _weak_topics_page()
    elif page=="Course Workspace": _course_workspace()
    elif page=="Saved Visualizations": _saved_visualizations()
    elif page=="Progress Dashboard": _progress_dashboard()
    else: _debug_tab()

if __name__=="__main__": main()
