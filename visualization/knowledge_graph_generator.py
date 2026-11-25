"""
Phase 3 — Visualization: Knowledge Graphs / Concept Maps.

Distinct from diagram_generator.py's process-flow diagrams (Mermaid
flowcharts for "how does X work"), this builds a course-wide concept map:
nodes are recurring technical terms across ALL ingested course material,
edges are co-occurrence within the same chunk. This matches Slide 10's
"Knowledge Graphs: Concept maps showing relationships between course topics
and key ideas" — a corpus-wide overview, not a per-query answer.

Rendered locally with networkx + matplotlib (no CDN, no internet needed at
render time — the only network dependency in the whole visualization layer
is the one-time BGE-M3 embedding-model download in rag/vectorstore.py).

Like chart_generator and diagram_generator, concept extraction here is
heuristic (capitalization + frequency), not LLM-reasoned — consistent with
the existing regex-based approach elsewhere in visualization/.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations
from typing import List, Tuple

import matplotlib

matplotlib.use("Agg")  # headless rendering, safe for Streamlit/servers
import matplotlib.pyplot as plt
import networkx as nx

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to", "for",
    "with", "is", "are", "was", "were", "be", "been", "being", "this", "that",
    "these", "those", "it", "its", "as", "by", "from", "into", "then", "than",
    "which", "what", "when", "where", "how", "why", "not", "no", "can", "will",
    "would", "should", "could", "may", "might", "must", "also", "such", "each",
    "lecture", "chapter", "page", "figure", "table", "section", "example",
}

# A "concept" is either a capitalized multi-word phrase ("Neural Network") or
# a single technical-looking word of reasonable length, both stopword-filtered.
_PHRASE_PATTERN = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b")
_WORD_PATTERN = re.compile(r"\b[a-zA-Z][a-zA-Z\-]{4,}\b")


@dataclass
class ConceptMapSpec:
    concepts: List[str] = field(default_factory=list)
    edges: List[Tuple[str, str, int]] = field(default_factory=list)  # (a, b, weight)
    is_placeholder: bool = False


def _extract_concepts_per_chunk(text: str, max_per_chunk: int = 6) -> List[str]:
    phrases = {p.strip() for p in _PHRASE_PATTERN.findall(text) if p.lower() not in _STOPWORDS}
    words = {
        w.lower()
        for w in _WORD_PATTERN.findall(text)
        if w.lower() not in _STOPWORDS
    }
    # Prefer multi-word phrases (more informative); backfill with frequent words.
    concepts = list(phrases)[:max_per_chunk]
    if len(concepts) < max_per_chunk:
        concepts += list(words)[: max_per_chunk - len(concepts)]
    return concepts


def build_concept_map(
    documents: List[str],
    max_concepts: int = 15,
    min_edge_weight: int = 1,
) -> ConceptMapSpec:
    """Builds a concept co-occurrence graph across the whole ingested corpus.

    documents: every chunk's raw text, e.g. from VectorStore.get_all_documents().
    """
    if not documents:
        return ConceptMapSpec(
            concepts=["Upload course material", "to see", "a concept map"],
            edges=[("Upload course material", "to see", 1), ("to see", "a concept map", 1)],
            is_placeholder=True,
        )

    concept_freq: Counter = Counter()
    edge_weight: Counter = Counter()

    for doc in documents:
        chunk_concepts = _extract_concepts_per_chunk(doc)
        concept_freq.update(chunk_concepts)
        for a, b in combinations(sorted(set(chunk_concepts)), 2):
            edge_weight[(a, b)] += 1

    if not concept_freq:
        return ConceptMapSpec(
            concepts=["No concepts extracted"],
            edges=[],
            is_placeholder=True,
        )

    top_concepts = {c for c, _ in concept_freq.most_common(max_concepts)}
    edges = [
        (a, b, w)
        for (a, b), w in edge_weight.items()
        if w >= min_edge_weight and a in top_concepts and b in top_concepts
    ]

    return ConceptMapSpec(concepts=sorted(top_concepts), edges=edges, is_placeholder=False)


def render_concept_map(spec: ConceptMapSpec):
    """Returns a matplotlib Figure. Caller (Streamlit UI) does st.pyplot(fig)."""
    graph = nx.Graph()
    graph.add_nodes_from(spec.concepts)
    for a, b, w in spec.edges:
        graph.add_edge(a, b, weight=w)

    fig, ax = plt.subplots(figsize=(8, 6))

    if graph.number_of_nodes() == 0:
        ax.text(0.5, 0.5, "No concepts to display", ha="center", va="center")
        ax.axis("off")
        return fig

    pos = nx.spring_layout(graph, seed=42, k=0.9)
    degrees = dict(graph.degree())
    node_sizes = [300 + 400 * degrees.get(n, 0) for n in graph.nodes()]
    edge_widths = [0.5 + 0.5 * graph[u][v].get("weight", 1) for u, v in graph.edges()]

    nx.draw_networkx_nodes(graph, pos, ax=ax, node_size=node_sizes, node_color="#4C72B0", alpha=0.85)
    nx.draw_networkx_edges(graph, pos, ax=ax, width=edge_widths, alpha=0.4)
    nx.draw_networkx_labels(graph, pos, ax=ax, font_size=8)

    title = "Course Concept Map" if not spec.is_placeholder else spec.concepts[0]
    ax.set_title(title, fontsize=11)
    ax.axis("off")
    fig.tight_layout()
    return fig


def generate_concept_map(documents: List[str]):
    """Convenience one-shot: documents -> rendered matplotlib Figure + spec."""
    spec = build_concept_map(documents)
    fig = render_concept_map(spec)
    return spec, fig
