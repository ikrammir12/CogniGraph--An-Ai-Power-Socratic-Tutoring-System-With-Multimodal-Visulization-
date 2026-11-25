"""Citation checks and configurable RAG answer acceptance.

Citation/source-page membership remains deterministic. For document-grounded
chat, the caller may use a lenient mode so an imperfect semantic audit does not
blanket-reject a useful answer when it contains a substantive response and only
citations that actually occur in retrieved evidence. Audit warnings remain
visible in logs and should be used for quality review.
"""
from __future__ import annotations

import re
from typing import Any

# Accept both the required [file.pdf, p. 12] style and common model variants
# such as (file.pdf, p. 12). Do not synthesize citations that are not present.
_CITATION_RE = re.compile(
    r"[\[(]\s*([^\[\]\n]{1,240}?,\s*(?:p\.?|page)\s*\d+)\s*[\])]",
    flags=re.IGNORECASE,
)


def citation_key(reference: str) -> str:
    """Normalize case, whitespace, and punctuation in source/page labels."""
    return re.sub(r"[\W_]+", "", str(reference)).casefold()


def extract_citations(text: str) -> list[str]:
    """Extract citation labels in square brackets or parentheses."""
    return [match.group(1).strip() for match in _CITATION_RE.finditer(str(text or ""))]


def normalize_citation_format(text: str) -> str:
    """Convert citation markers to square brackets without adding or changing refs."""
    return _CITATION_RE.sub(lambda match: f"[{match.group(1).strip()}]", str(text or ""))



def reconcile_citations(
    answer: str, evidence: str
) -> tuple[str, dict[str, list[str]]]:
    """Normalize citation variants and remove references absent from evidence."""
    canonical = {}
    for ref in extract_citations(evidence):
        canonical.setdefault(citation_key(ref), ref)

    changed = []
    removed = []

    def fix(match):
        raw = match.group(1).strip()
        target = canonical.get(citation_key(raw))
        if target is None:
            removed.append(raw)
            return ""
        if raw != target:
            changed.append(raw)
        return f"[{target}]"

    text = _CITATION_RE.sub(fix, str(answer or ""))
    text = re.sub(r"[ \t]+([,;:.!?])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\[\s*\]", "", text)

    return text.strip(), {"canonicalized": changed, "removed": removed}


def validate_citations(answer: str, evidence: str) -> dict[str, Any]:
    """Require at least one citation and require every reference to exist in evidence."""
    answer_refs = extract_citations(answer)
    evidence_refs = extract_citations(evidence)
    evidence_keys = {citation_key(value) for value in evidence_refs}
    unmatched = [value for value in answer_refs if citation_key(value) not in evidence_keys]
    return {
        "valid": bool(answer_refs) and not unmatched,
        "answer_citations": answer_refs,
        "evidence_citations": evidence_refs,
        "unmatched_citations": unmatched,
    }


def has_substantive_answer(text: str) -> bool:
    """True when a response contains prose beyond citations/source-only lines."""
    value = re.sub(r"(?im)^\s*Sources:\s*.*$", "", str(text or ""))
    value = _CITATION_RE.sub("", value)
    return bool(re.search(r"\b[A-Za-z]{3,}\b", value))


def grounding_decision(
    answer: str,
    audit: dict[str, Any],
    evidence: str,
    *,
    allow_partial: bool = False,
) -> dict[str, Any]:
    """Decide whether to return a response, with a user-friendly partial mode.

    Strict mode is available for regression tests and sensitive teaching flows.
    Partial mode does not require a perfect semantic-auditor verdict, but it
    still requires a substantive answer, at least one citation, and every
    citation to match an actual source/page label in retrieved evidence. An
    auditor-declared invalid citation still blocks acceptance.
    """
    citation_check = validate_citations(answer, evidence)
    has_answer = has_substantive_answer(answer)
    audit_supported = audit.get("supported") is True
    unsupported_claims = audit.get("unsupported_claims")
    invalid_citations = audit.get("invalid_citations")
    uncited_claims = audit.get("uncited_claims")

    strict_acceptance = bool(
        has_answer
        and audit_supported
        and unsupported_claims == []
        and invalid_citations == []
        and uncited_claims == []
        and citation_check["valid"]
    )
    # For normal PDF Q&A, an uncertain/incomplete audit is a warning rather
    # than an automatic refusal. Still reject absent/mismatched citations and
    # a citation the auditor specifically marks invalid.
    # Lenient normal Q&A: auditor warnings do not alone block a useful answer.
    # Still require substantive text and citations found in retrieved evidence.
    # Lenient normal Q&A: missing or imperfect citations alone do not
    # suppress substantive prose. Callers should sanitize citation markers.
    partial_acceptance = bool(has_answer)
    accepted = partial_acceptance if allow_partial else strict_acceptance
    return {
        "accepted": accepted,
        "soft_accept": bool(allow_partial and accepted and not strict_acceptance),
        "has_answer_text": has_answer,
        "citations_valid": citation_check["valid"],
        "citation_check": citation_check,
        "audit_supported": audit_supported,
        "unsupported_claims": unsupported_claims,
        "invalid_citations": invalid_citations,
        "uncited_claims": uncited_claims,
    }

_OBJECTIVE_QUERY_TERMS = (
    "objective", "purpose", "aim", "goals", "goal", "overview",
    "expected outcome", "expected outcomes", "key deliverable",
    "key deliverables", "problem statement", "what problem",
)


def is_objective_overview_query(query: str) -> bool:
    """Detect broad project-purpose questions needing diversified retrieval."""
    normalized = " ".join(str(query or "").casefold().split())
    return any(term in normalized for term in _OBJECTIVE_QUERY_TERMS)
