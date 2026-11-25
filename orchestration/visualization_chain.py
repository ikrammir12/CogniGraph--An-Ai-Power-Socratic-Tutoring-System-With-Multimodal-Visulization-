"""
Orchestration Layer — visualization tool dispatch via LangChain.

Completes the last piece of your proposal's Backend claim ("LangChain to
orchestrate the interaction between the LLM, Vector DB, and visualization
tools"): this module wraps chart/diagram/concept-map/image generation as a
LangChain RunnableBranch keyed on the router's chosen OutputMode.

app/streamlit_app.py calls `visualization_chain.invoke(...)` and gets back
a small, render-agnostic result describing what was produced; it stays
responsible for the actual `st.pyplot(...)` / `st.image(...)` calls, since
Streamlit rendering isn't something LangChain has any business owning.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.runnables import RunnableBranch, RunnableLambda

from router.multimodal_router import OutputMode
from visualization.chart_generator import extract_chart_spec, render_chart
from visualization.diagram_generator import extract_diagram_spec, spec_to_mermaid
from visualization.image_generator import generate_concept_image
from visualization.knowledge_graph_generator import generate_concept_map


@dataclass
class VisualizationResult:
    kind: str                       # "chart" | "diagram" | "concept_map" | "image" | "none"
    figure: Optional[Any] = None    # matplotlib Figure, for "chart" / "concept_map"
    mermaid_source: Optional[str] = None  # for "diagram"
    image_message: Optional[str] = None   # for "image" (stub message)
    image_bytes: Optional[bytes] = None   # for "image", once a backend is wired in
    is_placeholder: bool = False


def _run_chart(inputs: dict) -> VisualizationResult:
    spec = extract_chart_spec(inputs["query"], inputs["context_text"])
    fig = render_chart(spec)
    return VisualizationResult(kind="chart", figure=fig, is_placeholder=spec.is_placeholder)


def _run_diagram(inputs: dict) -> VisualizationResult:
    spec = extract_diagram_spec(inputs["query"], inputs["context_text"])
    mermaid = spec_to_mermaid(spec)
    return VisualizationResult(
        kind="diagram",
        mermaid_source=mermaid,
        is_placeholder=spec.is_placeholder,
    )


def _run_concept_map(inputs: dict) -> VisualizationResult:
    # Corpus-wide, not per-query: ignores context_text and uses everything
    # ingested so far, per Slide 10's "concept maps showing relationships
    # between course topics" (a course-wide overview).
    documents = inputs["get_all_documents"]()
    spec, fig = generate_concept_map(documents)
    return VisualizationResult(kind="concept_map", figure=fig, is_placeholder=spec.is_placeholder)


def _run_image(inputs: dict) -> VisualizationResult:
    result = generate_concept_image(inputs["query"])
    return VisualizationResult(
        kind="image",
        image_message=result.message,
        image_bytes=result.image_bytes,
        is_placeholder=not result.available,
    )


def _run_none(_inputs: dict) -> VisualizationResult:
    return VisualizationResult(kind="none")


# RunnableBranch: (condition, runnable), ..., default_runnable
visualization_chain = RunnableBranch(
    (lambda x: x["mode"] == OutputMode.GRAPH, RunnableLambda(_run_chart)),
    (lambda x: x["mode"] == OutputMode.DIAGRAM, RunnableLambda(_run_diagram)),
    (lambda x: x["mode"] == OutputMode.CONCEPT_MAP, RunnableLambda(_run_concept_map)),
    (lambda x: x["mode"] == OutputMode.IMAGE, RunnableLambda(_run_image)),
    RunnableLambda(_run_none),
)


def run_visualization(
    mode: OutputMode, query: str, context_text: str, get_all_documents
) -> VisualizationResult:
    """Convenience wrapper so callers don't need to know the RunnableBranch's
    input dict shape."""
    return visualization_chain.invoke(
        {
            "mode": mode,
            "query": query,
            "context_text": context_text,
            "get_all_documents": get_all_documents,
        }
    )
