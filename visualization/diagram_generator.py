"""
Phase 3 — Visualization: System Diagrams (Mermaid.js integration).

Given a query routed to OutputMode.DIAGRAM plus its retrieved course
context, produce Mermaid flowchart syntax the UI can render directly
(Streamlit has no native Mermaid widget, so app/streamlit_app.py embeds it
via `streamlit.components.v1.html` — see that file).

Like chart_generator, the "understand the process and break it into steps"
part is a reasoning task your fine-tuned LLM should eventually own (prompt
it to emit the numbered-step text below, or Mermaid syntax directly). The
regex-based step splitter here is the placeholder seam for that.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class DiagramSpec:
    title: str
    steps: List[str] = field(default_factory=list)
    is_placeholder: bool = False
    mermaid_source: str | None = None


_STEP_SPLIT_PATTERN = re.compile(
    r"(?:^|\.\s+)(?:\d+[\.\)]\s*|first,?\s+|then,?\s+|next,?\s+|finally,?\s+|after that,?\s+)",
    re.IGNORECASE,
)



def _topic_specific_mermaid(query: str, context_text: str) -> str | None:
    """Create a domain-specific diagram for well-recognized workflows."""
    q = (query or "").casefold()
    combined = f"{query}\n{context_text}".casefold()

    # Python for/while loops: show the actual repeat-and-exit behavior.
    if re.search(r"\bwhile\b.*\bloop|\bwhile\s+loops?\b", q):
        return """flowchart TD
    A([Start]) --> B{"Is the loop condition true?"}
    B -- Yes --> C["Execute the loop body"]
    C --> D["Check the condition again"]
    D --> B
    B -- No --> E([Finish])"""

    if re.search(r"\b(?:python\s+)?loops?\b|\brange\s*\(", q):
        source_text = f"{query}\n{context_text}"
        range_match = re.search(
            r"\brange\s*\(\s*(\d+)\s*\)", source_text, re.IGNORECASE
        )
        iterable = (
            f"range({range_match.group(1)})"
            if range_match else "the iterable"
        )

        body_match = re.search(
            r"(?m)^[ \t]*for\s+([a-z_]\w*)\s+in\b[^\n:]*:"
            r"[ \t]*\n[ \t]+([^\n]+)",
            source_text,
            re.IGNORECASE,
        )
        variable_match = re.search(
            r"\bfor\s+([a-z_]\w*)\s+in\b",
            source_text,
            re.IGNORECASE,
        )
        variable = (
            body_match.group(1) if body_match
            else variable_match.group(1) if variable_match
            else "item"
        )
        operation = (
            body_match.group(2).strip()
            if body_match else "Execute the loop body"
        )
        operation = re.sub(r"^[`* ]+|[`* ]+$", "", operation).strip()
        operation = _sanitize_node_label(operation)

        return f"""flowchart TD
    A([Start]) --> B["Get the next value from {iterable}"]
    B --> C{{"Is another value available?"}}
    C -- Yes --> D["Assign {variable} = current value"]
    D --> E["Run: {operation}"]
    E --> B
    C -- No --> F([Finish])"""

    # Retrieval-augmented generation pipeline.
    if re.search(r"\b(?:rag|retrieval augmented generation|vector database)\b", q):
        return """flowchart TD
    A["User question"] --> B["Create query embedding"]
    B --> C["Retrieve relevant document chunks"]
    C --> D["Combine question and retrieved context"]
    D --> E["Generate a grounded LLM response"]
    E --> F["Return answer with supporting sources"]"""

    # Machine-learning training workflow.
    if re.search(
        r"\b(?:machine learning workflow|train(?:ing)? a model|"
        r"model training|supervised learning)\b",
        q,
    ):
        return """flowchart TD
    A["Collect labelled data"] --> B["Clean and prepare features"]
    B --> C["Split training and evaluation data"]
    C --> D["Train the model"]
    D --> E["Evaluate model performance"]
    E --> F{"Performance acceptable?"}
    F -- No --> D
    F -- Yes --> G["Use the trained model"]"""

    # Neural networks and backpropagation.
    if re.search(r"\bbackpropagation\b", q):
        return """flowchart TD
    A["Input features"] --> B["Forward pass through the network"]
    B --> C["Calculate prediction error"]
    C --> D["Propagate error backward"]
    D --> E["Update weights"]
    E --> B"""

    if re.search(r"\bneural network\b", q):
        return """flowchart TD
    A["Input layer"] --> B["Weighted connections"]
    B --> C["Hidden layers and activation"]
    C --> D["Output prediction"]
    D --> E["Calculate loss during training"]
    E --> F["Adjust weights to improve predictions"]"""

    # Conditional statements.
    if re.search(r"\b(?:if.?else|if statement|conditional logic)\b", q):
        return """flowchart TD
    A([Start]) --> B{"Evaluate condition"}
    B -- True --> C["Run if branch"]
    B -- False --> D["Run else branch"]
    C --> E([Continue])
    D --> E"""

    return None


def _context_sentence_steps(query: str, context_text: str) -> list[str]:
    """Extract short, topic-relevant statements if no explicit sequence exists."""
    # Prefer the tutor's explanation when supplied by the API.
    marker = "TUTOR EXPLANATION:"
    if marker.casefold() in context_text.casefold():
        context_text = re.split(
            re.escape(marker), context_text, maxsplit=1, flags=re.IGNORECASE
        )[1]

    stopwords = {
        "the", "and", "for", "are", "was", "were", "what", "when",
        "where", "which", "with", "from", "that", "this", "into",
        "you", "your", "can", "could", "would", "should", "please",
        "explain", "create", "make", "draw", "diagram", "visualize",
        "step", "steps", "about", "using", "show", "help", "me",
    }

    def terms(text: str) -> set[str]:
        words = re.findall(r"[a-z]{3,}", text.casefold())
        normalized = {word[:-1] if word.endswith("s") else word for word in words}
        return normalized - stopwords

    query_terms = terms(query)
    candidates = []

    for sentence in re.split(r"(?<=[.!?])\s+|\n+|[•]\s*", context_text):
        clean = re.sub(r"[*`#\t]+", "", sentence).strip(" -•\r\n")
        if not 20 <= len(clean) <= 180:
            continue
        if ".pdf" in clean.casefold() or "relevance=" in clean.casefold():
            continue
        overlap = len(query_terms & terms(clean))
        if overlap:
            candidates.append((overlap, clean[:100]))

    # Rank by topic overlap, preserve original order among equally relevant items.
    candidates.sort(key=lambda item: -item[0])
    selected = []
    for _, sentence in candidates:
        if sentence not in selected:
            selected.append(sentence)
        if len(selected) == 5:
            break
    return selected


def extract_diagram_spec(query: str, context_text: str) -> DiagramSpec:
    """Splits retrieved context into ordered steps using numbering / sequence
    words ("first", "then", "next", "finally"). Falls back to a generic
    3-node placeholder when no clear sequence is detected."""
    topic_diagram = _topic_specific_mermaid(query, context_text)
    if topic_diagram:
        return DiagramSpec(
            title=query[:60] or "Topic workflow",
            is_placeholder=False,
            mermaid_source=topic_diagram,
        )

    raw_steps = [s.strip() for s in _STEP_SPLIT_PATTERN.split(context_text) if s.strip()]
    # Keep steps short enough to fit in a diagram node; drop obvious non-steps.
    steps = [s[:80] for s in raw_steps if len(s) > 8][:8]

    if len(steps) >= 2:
        return DiagramSpec(title=query[:60], steps=steps, is_placeholder=False)

    context_steps = _context_sentence_steps(query, context_text)
    if len(context_steps) >= 2:
        return DiagramSpec(
            title=f"Topic overview: {query[:45]}",
            steps=context_steps,
            is_placeholder=False,
        )

    topic = re.sub(
        r"^(please|can you|could you|teach me|help me|show me|"
        r"visualize|visualise|draw|create|make|explain)\\s+",
        "",
        (query or "").strip(),
        flags=re.IGNORECASE,
    )
    topic = re.sub(r"\\s+", " ", topic).strip(" .?!")[:55] or "Selected topic"

    return DiagramSpec(
        title=f"Illustrative overview: {topic}",
        steps=[f"Topic: {topic}", "Key concept or component", "Result or application"],
        is_placeholder=True,
    )


def _sanitize_node_label(text: str) -> str:
    # Mermaid node labels can't contain brackets/quotes unescaped.
    return text.replace('"', "'").replace("[", "(").replace("]", ")")


def spec_to_mermaid(spec: DiagramSpec) -> str:
    """Renders a DiagramSpec as Mermaid flowchart syntax (top-down)."""
    if spec.mermaid_source:
        return spec.mermaid_source

    lines = ["flowchart TD"]
    node_ids = [f"N{i}" for i in range(len(spec.steps))]

    for node_id, step in zip(node_ids, spec.steps):
        label = _sanitize_node_label(step)
        lines.append(f'    {node_id}["{label}"]')

    for a, b in zip(node_ids, node_ids[1:]):
        lines.append(f"    {a} --> {b}")

    return "\n".join(lines)


def generate_mermaid(query: str, context_text: str) -> str:
    spec = extract_diagram_spec(query, context_text)
    return spec_to_mermaid(spec)
