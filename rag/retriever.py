"""
Phase 2 — Course-Aware RAG.

Sits on top of VectorStore and adds the two things the Socratic engine
actually needs: relevance filtering (so the model can say "that's not in
your course materials" instead of hallucinating) and ready-to-quote
citations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from config import CONFIG
from rag.vectorstore import get_vectorstore


@dataclass
class RetrievedContext:
    text: str
    source: str
    page: int
    similarity: float | None

    def citation(self) -> str:
        return f"{self.source}, p.{self.page}"


def retrieve(query: str, top_k: int | None = None, course_id: int | None = None) -> List[RetrievedContext]:
    """Retrieve relevant course chunks, with a cautious fallback for near-threshold results."""
    store = get_vectorstore(course_id)
    hits = store.query(query, top_k=top_k)

    candidates = [
        RetrievedContext(
            text=h["text"],
            source=h["source"],
            page=h["page"],
            similarity=h["similarity"],
        )
        for h in hits
    ]

    threshold = CONFIG.rag.relevance_threshold
    accepted = [
        item for item in candidates
        if item.similarity is not None and item.similarity >= threshold
    ]

    if accepted:
        return accepted

    # If the strict filter rejects everything, retain only the closest candidates.
    fallback_floor = max(0.0, threshold - 0.10)
    fallback = [
        item for item in candidates
        if item.similarity is not None and item.similarity >= fallback_floor
    ][:min(top_k or 3, 3)]

    if fallback:
        print(
            "RAG_RETRIEVAL near_threshold_fallback "
            f"threshold={threshold:.3f} "
            f"floor={fallback_floor:.3f} "
            f"scores={[round(item.similarity, 3) for item in fallback]}",
            flush=True,
        )

    return fallback

def build_context_block(results: List[RetrievedContext], include_citation_ids: bool = False) -> str:
    """Formats retrieved chunks into a block the LLM prompt can drop in directly,
    each one pre-labelled with its citation so the model can reference it."""
    if not results:
        return "[No relevant course material was found for this query.]"

    lines = []
    for i, r in enumerate(results, start=1):
        relevance = f", relevance={r.similarity:.2f}" if r.similarity is not None else ""
        ref_id = f" [E{i}]" if include_citation_ids else ""
        lines.append(f"[{i}]{ref_id} [{r.citation()}]{relevance}\n{r.text}")
    return "\n\n".join(lines)


def sample_course_context(course_id: int, limit: int = 5) -> List[RetrievedContext]:
    """Select a spread of chunks from the chosen course when no topic is given.

    This avoids searching for the artificial phrase 'course material', which can
    retrieve a table of contents or unrelated text. Sampled chunks are marked
    unranked (similarity=None), not assigned a fake similarity score.
    """
    store = get_vectorstore(course_id)
    data = store.store.get(include=["documents", "metadatas"])
    documents = data.get("documents") or []
    metadatas = data.get("metadatas") or []
    total = len(documents)
    if total == 0:
        return []
    count = min(max(1, limit), total)
    if count == 1:
        indices = [total // 2]
    else:
        indices = sorted({round(i * (total - 1) / (count - 1)) for i in range(count)})
    results: List[RetrievedContext] = []
    for idx in indices:
        meta = metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {}
        results.append(RetrievedContext(
            text=documents[idx] or "",
            source=str(meta.get("source") or "course material"),
            page=int(meta.get("page") or 1),
            similarity=None,
        ))
    return [item for item in results if item.text.strip()]


def has_course_material(course_id: int | None = None) -> bool:
    return bool(get_vectorstore(course_id).list_sources())
