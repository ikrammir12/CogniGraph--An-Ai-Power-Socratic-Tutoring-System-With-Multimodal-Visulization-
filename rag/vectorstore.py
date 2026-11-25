"""
Phase 1/2 — Memory Layer: LangChain-orchestrated ChromaDB vector store.

Per your proposal's Backend section ("Uses LangChain to orchestrate the
interaction between the LLM, Vector DB, and visualization tools"), the
actual ChromaDB interaction here goes through LangChain's Chroma vector
store class, not a raw chromadb client. Our BGE-M3 embedding model is
wrapped as a LangChain Embeddings implementation so it plugs directly into
that class.

The embedding model is loaded lazily on first use, since it requires a
network fetch (or local cache) the first time it's downloaded — importing
this module never touches the network, only calling `get_vectorstore()`
and then actually embedding something does.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Optional, Sequence

from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from config import CONFIG
from ingestion.pdf_processor import Chunk


class BGELangChainEmbeddings(Embeddings):
    """Wraps sentence-transformers' BGE-M3 model as a LangChain Embeddings class."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or CONFIG.rag.embedding_model
        self._model = None

    def _load(self):
        if self._model is None:
            # Imported lazily: sentence-transformers + torch are heavy and only
            # needed once we actually embed something.
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        model = self._load()
        vectors = model.encode(list(texts), batch_size=1, normalize_embeddings=True)
        return vectors.tolist()

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class VectorStore:
    """Thin, typed wrapper around a LangChain Chroma collection, keeping the
    same public API the rest of the app already relies on (add_chunks,
    query, list_sources, get_all_documents, clear) regardless of which
    library sits underneath."""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        embedding_fn: Optional[Embeddings] = None,
    ):
        from config import CHROMA_DIR

        self.collection_name = collection_name or CONFIG.rag.collection_name
        self.embedding_fn = embedding_fn or BGELangChainEmbeddings()
        self.persist_directory = str(CHROMA_DIR)
        self.store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding_fn,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: Sequence[Chunk]) -> int:
        if not chunks:
            return 0
        self.store.add_texts(
            ids=[c.id for c in chunks],
            texts=[c.text for c in chunks],
            metadatas=[
                {"source": c.source, "page": c.page, "chunk_index": c.chunk_index}
                for c in chunks
            ],
        )
        return len(chunks)

    def query(self, query_text: str, top_k: Optional[int] = None) -> List[dict]:
        """Returns a list of {text, source, page, similarity} dicts, best first."""
        top_k = top_k or CONFIG.rag.top_k
        if self._count() == 0:
            return []

        # LangChain's Chroma returns cosine *distance*; convert to a 0..1 similarity
        # to keep the same contract the rest of the app (retriever.py) expects.
        results = self.store.similarity_search_with_score(query_text, k=min(top_k, self._count()))
        hits = []
        for doc, distance in results:
            hits.append(
                {
                    "text": doc.page_content,
                    "source": doc.metadata.get("source"),
                    "page": doc.metadata.get("page"),
                    "similarity": max(0.0, 1 - distance),
                }
            )
        return hits

    def _count(self) -> int:
        return self.store._collection.count()

    def list_sources(self) -> List[str]:
        if self._count() == 0:
            return []
        data = self.store.get()
        sources = {m.get("source") for m in data.get("metadatas", []) if m}
        return sorted(s for s in sources if s)

    def get_all_documents(self) -> List[str]:
        """All ingested chunk texts across every source — used by the
        knowledge-graph/concept-map generator, which needs the whole corpus
        rather than a per-query top-k retrieval."""
        if self._count() == 0:
            return []
        data = self.store.get()
        return list(data.get("documents", []))

    def clear(self) -> None:
        self.store.delete_collection()
        self.store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedding_fn,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine"},
        )


@lru_cache(maxsize=64)
def get_vectorstore(course_id: int | None = None) -> VectorStore:
    """Return a course-isolated Chroma collection.

    course_id=None preserves the original collection for backward compatibility
    with existing tests/demo data. User workspaces get their own collections.
    """
    if course_id is None:
        return VectorStore()
    import hashlib
    suffix = hashlib.sha1(str(course_id).encode("utf-8")).hexdigest()[:12]
    return VectorStore(collection_name="cognigraph_course_" + suffix)

def clone_legacy_collection_to_course(course_id: int) -> int:
    """Copy the pre-workspace demo collection into a user's first course once."""
    legacy = get_vectorstore(None)
    target = get_vectorstore(course_id)
    if legacy._count() == 0 or target._count() != 0:
        return 0
    data = legacy.store.get(include=["documents", "metadatas"])
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []
    if not docs:
        return 0
    import hashlib
    ids=[]
    for i, text in enumerate(docs):
        ids.append(hashlib.sha1(f"{course_id}|{i}|{text}".encode("utf-8")).hexdigest())
    target.store.add_texts(ids=ids, texts=docs, metadatas=metas)
    return len(docs)
