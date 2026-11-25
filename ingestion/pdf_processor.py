"""
Phase 1 — Foundation: PDF processing pipeline.

Turns an uploaded course PDF into a list of Chunk objects, each carrying
enough metadata (source file, page number) that the RAG layer can later
cite exactly where an answer came from.
"""

from __future__ import annotations

import hashlib 
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from pypdf import PdfReader

from config import CONFIG


@dataclass
class Chunk:
    id: str
    text: str
    source: str          # original filename
    page: int            # 1-indexed page number
    chunk_index: int     # position of this chunk within the page
    metadata: dict = field(default_factory=dict)

    def citation(self) -> str:
        return f"{self.source}, p.{self.page}"


def extract_pages(pdf_path: str | Path) -> List[str]:
    """Return a list of raw text strings, one per page."""
    reader = PdfReader(str(pdf_path))

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(_clean_text(text))

    return pages


def _clean_text(text: str) -> str:
    """Clean common PDF extraction whitespace artifacts."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> List[str]:
    """
    Split text into character-based chunks.

    Sentences are kept together where possible, with a small overlap
    between consecutive chunks to preserve context.
    """

    if chunk_size is None:
        chunk_size = CONFIG.ingestion.chunk_size

    if overlap is None:
        overlap = CONFIG.ingestion.chunk_overlap

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        # Add sentence to current chunk when it still fits.
        if len(current) + len(sentence) + 1 <= chunk_size:
            current = f"{current} {sentence}".strip()

        else:
            # Store completed chunk.
            if current:
                chunks.append(current)

            # Preserve overlap from previous chunk.
            tail = current[-overlap:] if overlap > 0 and current else ""

            current = f"{tail} {sentence}".strip()

    # Store final chunk.
    if current:
        chunks.append(current)

    return chunks


def process_pdf(pdf_path: str | Path) -> List[Chunk]:
    """
    Full Phase 1 pipeline:

        PDF
        ↓
        page text extraction
        ↓
        text cleaning
        ↓
        chunking
        ↓
        deterministic Chunk IDs
    """

    pdf_path = Path(pdf_path)

    pages = extract_pages(pdf_path)

    chunks: List[Chunk] = []

    for page_num, page_text in enumerate(pages, start=1):

        if not page_text:
            continue

        page_chunks = chunk_text(page_text)

        for chunk_index, piece in enumerate(page_chunks):

            # Skip extremely small chunks.
            if len(piece) < CONFIG.ingestion.min_chunk_chars:
                continue

            # ---------------------------------------------------------
            # Deterministic ID
            #
            # The same PDF + page + chunk + text always gets the same ID.
            # This prevents duplicate ChromaDB entries when the same PDF
            # is uploaded multiple times.
            # ---------------------------------------------------------
            chunk_id = hashlib.sha1(
                f"{pdf_path.name}|{page_num}|{chunk_index}|{piece}".encode(
                    "utf-8"
                )
            ).hexdigest()

            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=piece,
                    source=pdf_path.name,
                    page=page_num,
                    chunk_index=chunk_index,
                )
            )

    return chunks


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python pdf_processor.py <path_to_pdf>")
        sys.exit(1)

    result = process_pdf(sys.argv[1])

    print(f"Extracted {len(result)} chunks from {sys.argv[1]}")

    for chunk in result[:3]:
        print(
            f"\n--- {chunk.citation()} ---\n"
            f"{chunk.text[:200]}..."
        )