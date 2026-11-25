"""
Phase 3 — Visualization: Data Charts.

Given a student query (already routed to OutputMode.GRAPH) and whatever
RAG context was retrieved for it, produce a matplotlib chart.

The extractor supports several common formats found in course material:
- label: number / label = number
- student-performance table rows such as:
    S1 2 72 55 58
- markdown table rows such as:
    | S1 | 2 | 72 | 55 | 58 |
- sentence form such as:
    Student S1 got a score of 58.

The first two formats are useful for the CogniGraph demonstration because
the uploaded course PDF contains a student-performance table.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import List

import matplotlib

matplotlib.use("Agg")  # headless rendering, safe for Streamlit/servers
import matplotlib.pyplot as plt


@dataclass
class ChartSpec:
    chart_type: str                     # "bar" | "line" | "scatter"
    title: str
    x_label: str
    y_label: str
    categories: List[str] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    is_placeholder: bool = False        # True when no real numbers could be extracted


# Original generic "label: number" format, e.g. Accuracy: 92
_NUMBER_PATTERN = re.compile(
    r"([A-Za-z][A-Za-z0-9 _\-]{1,30}?)\s*[:=\-]\s*(-?\d+(?:\.\d+)?)\s*%?"
)

# Student performance rows, e.g.:
# S1  2  72  55  58
# S2  3  78  60  63
_STUDENT_ROW_PATTERN = re.compile(
    r"^\s*\|?\s*(S\d{1,3})\s*\|?\s+"
    r"(\d+(?:\.\d+)?)\s*\|?\s+"
    r"(\d+(?:\.\d+)?)\s*\|?\s+"
    r"(\d+(?:\.\d+)?)\s*\|?\s+"
    r"(\d+(?:\.\d+)?)\s*\|?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# More permissive student-row pattern for whitespace/table extraction where
# PDF text extraction collapses columns in slightly different ways.
_STUDENT_ROW_FALLBACK_PATTERN = re.compile(
    r"\b(S\d{1,3})\b\s+"
    r"(\d+(?:\.\d+)?)\s+"
    r"(\d+(?:\.\d+)?)\s+"
    r"(\d+(?:\.\d+)?)\s+"
    r"(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

# Sentence form, e.g. "Student S1 got a score of 58."
_STUDENT_SCORE_PATTERN = re.compile(
    r"\b(?:Student\s+)?(S\d{1,3})\b"
    r"\s+(?:got\s+(?:a\s+)?(?:final\s+)?score\s+of|score\s*[:=])\s*"
    r"(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)


def _build_student_chart(categories: list[str], values: list[float], query: str) -> ChartSpec:
    """Build a student-score chart spec with stable labels."""
    return ChartSpec(
        chart_type="bar",
        title="Final Scores of Students from Course Material",
        x_label="Student",
        y_label="Final Score",
        categories=categories,
        values=values,
        is_placeholder=False,
    )


def _extract_student_rows(context_text: str) -> tuple[list[str], list[float]]:
    """Extract S1..S8-style table rows and use the final numeric column as score."""
    categories: list[str] = []
    values: list[float] = []
    seen: set[str] = set()

    # First try line-aware extraction.
    matches = _STUDENT_ROW_PATTERN.findall(context_text)

    # If PDF extraction collapsed the table, fall back to a whitespace scan.
    if not matches:
        matches = _STUDENT_ROW_FALLBACK_PATTERN.findall(context_text)

    for student, _hours, _attendance, _previous_score, final_score in matches:
        student = student.upper()
        if student in seen:
            continue
        seen.add(student)
        categories.append(student)
        values.append(float(final_score))
        if len(categories) >= 8:
            break

    return categories, values


def _extract_student_scores(context_text: str) -> tuple[list[str], list[float]]:
    """Extract sentence-style student score statements."""
    categories: list[str] = []
    values: list[float] = []
    seen: set[str] = set()

    for student, score in _STUDENT_SCORE_PATTERN.findall(context_text):
        student = student.upper()
        if student in seen:
            continue
        seen.add(student)
        categories.append(student)
        values.append(float(score))
        if len(categories) >= 8:
            break

    return categories, values


def extract_chart_spec(
    query: str,
    context_text: str,
    chart_type: str = "bar",
) -> ChartSpec:
    """Extract a chart specification from retrieved course context.

    Extraction priority:
    1. Student-performance rows (S1 ... S8) — uses the final numeric column.
    2. Sentence-style student scores ("Student S1 got a score of 58").
    3. Generic label:number pairs (original behavior).
    4. Clearly marked placeholder when no numeric data is available.
    """
    print("\n" + "=" * 80)
    print("[CHART DEBUG] QUERY:")
    print(query)
    print("\n[CHART DEBUG] RETRIEVED CONTEXT:")
    print(context_text)
    print("=" * 80 + "\n")
    # ---------------------------------------------------------
    # 1. Student-performance table
    # ---------------------------------------------------------
    categories, values = _extract_student_rows(context_text)
    if categories:
        spec = _build_student_chart(categories, values, query)
        spec.chart_type = chart_type
        return spec

    # ---------------------------------------------------------
    # 2. Sentence form: Student S1 got a score of 58
    # ---------------------------------------------------------
    categories, values = _extract_student_scores(context_text)
    if categories:
        spec = ChartSpec(
            chart_type=chart_type,
            title="Student Scores from Course Material",
            x_label="Student",
            y_label="Score",
            categories=categories,
            values=values,
            is_placeholder=False,
        )
        return spec

    # ---------------------------------------------------------
    # 3. Original generic label:number extraction
    # ---------------------------------------------------------
    matches = _NUMBER_PATTERN.findall(context_text)
    seen: set[str] = set()
    categories = []
    values = []

    for label, num in matches:
        label = label.strip()
        if label.lower() in seen or len(label) < 2:
            continue
        seen.add(label.lower())
        categories.append(label)
        values.append(float(num))
        if len(categories) >= 8:
            break

    if categories:
        return ChartSpec(
            chart_type=chart_type,
            title=f'Data referenced in your course material for: "{query[:60]}"',
            x_label="Category",
            y_label="Value",
            categories=categories,
            values=values,
            is_placeholder=False,
        )

    # ---------------------------------------------------------
    # 4. No data found -> safe placeholder
    # ---------------------------------------------------------
    return ChartSpec(
        chart_type=chart_type,
        title="Illustrative example (no numeric data found in retrieved context)",
        x_label="Category",
        y_label="Value",
        categories=["A", "B", "C", "D"],
        values=[3, 7, 4, 9],
        is_placeholder=True,
    )


def render_chart(spec: ChartSpec):
    """Return a matplotlib Figure. Caller (Streamlit UI) does st.pyplot(fig)."""
    fig, ax = plt.subplots(figsize=(6, 4))

    if spec.chart_type == "line":
        ax.plot(spec.categories, spec.values, marker="o")
    elif spec.chart_type == "scatter":
        ax.scatter(range(len(spec.values)), spec.values)
        ax.set_xticks(range(len(spec.categories)))
        ax.set_xticklabels(spec.categories)
    else:  # default: bar
        ax.bar(spec.categories, spec.values)

    ax.set_title(spec.title, fontsize=10, wrap=True)
    ax.set_xlabel(spec.x_label)
    ax.set_ylabel(spec.y_label)
    fig.tight_layout()
    return fig


def chart_to_png_bytes(spec: ChartSpec) -> bytes:
    fig = render_chart(spec)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
