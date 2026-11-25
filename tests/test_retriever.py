"""
Lightweight tests for rag/retriever.py.

Uses a deterministic fake embedding function instead of downloading BGE-M3,
so these tests run instantly, offline, with no GPU — real semantic quality
is a manual/demo concern, not a unit-test concern.
"""
import hashlib
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.embeddings import Embeddings

from ingestion.pdf_processor import Chunk


class _FakeEmbeddings(Embeddings):
    """Deterministic, content-sensitive fake embedding: hashes the text so
    identical/near-identical text gets identical/near-identical vectors,
    without needing a real model."""

    def embed_documents(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)

    @staticmethod
    def _vec(text: str):
        h = hashlib.sha256(text.lower().encode()).digest()
        v = np.frombuffer(h, dtype=np.uint8).astype(float)
        return (v / (np.linalg.norm(v) + 1e-8)).tolist()


def _make_test_store():
    from rag.vectorstore import VectorStore

    store = VectorStore(collection_name="test_retriever", embedding_fn=_FakeEmbeddings())
    store.clear()
    chunks = [
        Chunk(id="c1", text="Overfitting occurs when a model memorizes training noise.", source="test.pdf", page=1, chunk_index=0),
        Chunk(id="c2", text="Gradient descent minimizes the loss function iteratively.", source="test.pdf", page=2, chunk_index=0),
    ]
    store.add_chunks(chunks)
    return store


def test_query_returns_citable_hits():
    import rag.retriever as retriever_module

    store = _make_test_store()
    retriever_module.get_vectorstore = lambda course_id=None: store

    # Query with text identical to an indexed chunk should retrieve it with
    # near-1.0 similarity (fake embeddings are hash-based, not semantic, so
    # we test exact/near-exact match rather than true semantic recall).
    results = retriever_module.retrieve("Overfitting occurs when a model memorizes training noise.")
    assert results, "expected at least one retrieved chunk"
    assert results[0].source == "test.pdf"
    assert results[0].citation() == "test.pdf, p.1"


def test_get_all_documents_returns_full_corpus():
    store = _make_test_store()
    docs = store.get_all_documents()
    assert len(docs) == 2


def test_build_context_block_handles_empty_results():
    from rag.retriever import build_context_block

    block = build_context_block([])
    assert "No relevant course material" in block


if __name__ == "__main__":
    test_query_returns_citable_hits()
    test_get_all_documents_returns_full_corpus()
    test_build_context_block_handles_empty_results()
    print("All retriever tests passed.")
