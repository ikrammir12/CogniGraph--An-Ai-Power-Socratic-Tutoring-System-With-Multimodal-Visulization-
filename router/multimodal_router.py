"""
Phase 3 — Voice Layer: Rule-Based Multimodal Router.

Per the proposal's digest ("a Rule-Based Multimodal Router to intelligently
analyze student queries and determine the best output format"), this is
deliberately NOT an ML classifier — it's fast, deterministic, and fully
explainable, which matters for a final-year-project demo where you need to
be able to say exactly why a given query produced a given output mode.

Priority order when multiple keyword sets match:
    CONCEPT_MAP > DIAGRAM > GRAPH > IMAGE > TEXT
Concept map is checked first because it's the most specific category
("how do these course topics relate to each other" is a corpus-wide
overview, not a single process/architecture explanation). Diagram beats
graph/image for the same reason described in the original design: "explain
how X works" is far more common in a CS course than a genuine
data-plotting or image request, even though wording can overlap.
"""
from __future__ import annotations

import re
from enum import Enum

from config import CONFIG


class OutputMode(str, Enum):
    TEXT = "text"
    GRAPH = "graph"
    DIAGRAM = "diagram"
    CONCEPT_MAP = "concept_map"
    IMAGE = "image"


def _matches_any(query: str, patterns: tuple) -> bool:
    query_l = query.lower()
    for pattern in patterns:
        if re.search(pattern, query_l):
            return True
    return False


def classify(query: str) -> OutputMode:
    """Rule-based classification of a student query into an output mode."""
    router_cfg = CONFIG.router

    if _matches_any(query, router_cfg.concept_map_keywords):
        return OutputMode.CONCEPT_MAP
    if _matches_any(query, router_cfg.diagram_keywords):
        return OutputMode.DIAGRAM
    if _matches_any(query, router_cfg.graph_keywords):
        return OutputMode.GRAPH
    if _matches_any(query, router_cfg.image_keywords):
        return OutputMode.IMAGE
    return OutputMode.TEXT


def explain_classification(query: str) -> dict:
    """Returns which keyword(s) triggered the classification — useful for the
    UI's 'why did it choose this mode?' debug panel, and for your FYP demo/viva."""
    router_cfg = CONFIG.router
    query_l = query.lower()

    matched = {
        "concept_map": [p for p in router_cfg.concept_map_keywords if re.search(p, query_l)],
        "diagram": [p for p in router_cfg.diagram_keywords if re.search(p, query_l)],
        "graph": [p for p in router_cfg.graph_keywords if re.search(p, query_l)],
        "image": [p for p in router_cfg.image_keywords if re.search(p, query_l)],
    }
    mode = classify(query)
    return {"mode": mode.value, "matched_keywords": matched}
