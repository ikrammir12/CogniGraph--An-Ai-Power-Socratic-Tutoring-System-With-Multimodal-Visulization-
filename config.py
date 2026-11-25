"""
CogniGraph — central configuration.

Every tunable knob lives here so the rest of the codebase never hardcodes
paths, model names, or thresholds. Override any of these with environment
variables of the same name if you don't want to edit this file directly.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma_db"

for _d in (DATA_DIR, UPLOAD_DIR, CHROMA_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass
class IngestionConfig:
    chunk_size: int = 800          # characters per chunk
    chunk_overlap: int = 150       # characters of overlap between chunks
    min_chunk_chars: int = 40      # drop near-empty chunks (headers, page numbers)


@dataclass
class RAGConfig:
    collection_name: str = "cognigraph_courses"
    embedding_model: str = _env("COGNIGRAPH_EMBED_MODEL", "BAAI/bge-m3")
    top_k: int = 5
    # Below this similarity score a chunk is considered irrelevant and dropped,
    # which is what lets the system say "not in your course materials" instead
    # of hallucinating from the base model's own knowledge.
    relevance_threshold: float = float(_env("COGNIGRAPH_RAG_THRESHOLD", "0.55"))


@dataclass
class SocraticConfig:
    min_questions_before_answer: int = 3
    max_questions_before_answer: int = 4
    persona_name: str = "CogniGraph Tutor"
    system_prompt: str = (
        "You are {persona_name}, a patient Socratic tutor. Adapt to the learner's "
        "request: answer direct factual questions directly when supported; for "
        "teaching requests, explain concepts step by step and encourage reasoning. "
        "Use supplied course context for document-specific claims, cite relevant "
        "source pages, and admit when the evidence is insufficient."
    )


@dataclass
class LLMConfig:
    backend: str = _env("COGNIGRAPH_LLM_BACKEND", "finetuned")

    base_model_id: str = _env(
        "COGNIGRAPH_BASE_MODEL",
        "unsloth/llama-3.2-3b-instruct-unsloth-bnb-4bit"
    )

    model_path: str = _env(
        "COGNIGRAPH_MODEL_PATH",
        r"D:\CogniGraph_Socratic_V2\adapter"
    )

    load_in_4bit: bool = True
    max_new_tokens: int = 512
    temperature: float = 0.7

    # --- hosted API backends ---
    claude_model: str = _env("COGNIGRAPH_CLAUDE_MODEL", "claude-sonnet-4-6")
    openai_model: str = _env("COGNIGRAPH_OPENAI_MODEL", "gpt-6.1-sol")
    openai_reasoning_effort: str = _env("COGNIGRAPH_OPENAI_REASONING_EFFORT", "medium")

@dataclass
class RouterConfig:
    # Rule-based keyword sets used by the multimodal router (Phase 3 in the proposal).
    graph_keywords: tuple = (
        "plot", "chart", "graph", "trend", "compare values", "over time",
        "distribution", "histogram", "scatter", "bar chart", "line chart",
        "correlation", "statistics", "data",
    )
    diagram_keywords: tuple = (
        "architecture", "flow", "pipeline", "diagram", "workflow", "steps",
        "process", "how does .* work", "structure of", "components of",
        "system design", "sequence of",
    )
    concept_map_keywords: tuple = (
        "concept map", "knowledge graph", "mind map",
        "relationship between", "relationships between", "how .* relate",
        "how are .* related", "connections between", "map out the concepts",
        "map the topics", "overview of the concepts", "overview of topics",
        "topics in this course", "related concepts",
    )
    image_keywords: tuple = (
        "visualize the concept", "concept art", "draw", "illustration",
        "imagine", "picture of", "metaphor for",
    )


@dataclass
class AppConfig:
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    socratic: SocraticConfig = field(default_factory=SocraticConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    router: RouterConfig = field(default_factory=RouterConfig)


CONFIG = AppConfig()
