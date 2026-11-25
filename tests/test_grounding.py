"""Offline regression tests for evidence-audit and citation acceptance."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm.grounding import (
    extract_citations,
    grounding_decision,
    normalize_citation_format,
    validate_citations,
    is_objective_overview_query,
)

EVIDENCE = """[1] [CogniGraph.pdf, p. 1], relevance=0.81
CogniGraph is an AI-Powered Socratic Tutoring System.

[2] [CogniGraph.pdf, p. 19], relevance=0.78
Key deliverables include a PDF upload and chat interface, automatic text/graph/diagram generation, and a local private deployment option."""


def test_parenthesized_citations_are_recognized_and_normalized():
    answer = "CogniGraph is an AI-powered Socratic tutoring system (CogniGraph.pdf, p. 1)."
    normalized = normalize_citation_format(answer)
    assert normalized.endswith("[CogniGraph.pdf, p. 1].")
    assert extract_citations(normalized) == ["CogniGraph.pdf, p. 1"]
    assert validate_citations(normalized, EVIDENCE)["valid"] is True


def test_valid_multiple_citations_pass_source_membership():
    answer = (
        "CogniGraph is a Socratic tutoring system [CogniGraph.pdf, p. 1]. "
        "Its deliverables include PDF chat and diagrams [CogniGraph.pdf, p. 19]."
    )
    result = validate_citations(answer, EVIDENCE)
    assert result["valid"] is True
    assert result["unmatched_citations"] == []


def test_unknown_page_is_rejected():
    result = validate_citations(
        "CogniGraph uses a framework [CogniGraph.pdf, p. 99].", EVIDENCE
    )
    assert result["valid"] is False
    assert result["unmatched_citations"] == ["CogniGraph.pdf, p. 99"]


def test_missing_citation_is_rejected():
    result = validate_citations("CogniGraph is a tutoring system.", EVIDENCE)
    assert result["valid"] is False


def test_unsupported_audit_is_rejected_even_with_valid_citation():
    answer = "CogniGraph uses PostgreSQL [CogniGraph.pdf, p. 19]."
    audit = {
        "supported": False,
        "unsupported_claims": ["The PDF does not mention PostgreSQL."],
        "invalid_citations": [],
        "uncited_claims": [],
    }
    assert grounding_decision(answer, audit, EVIDENCE)["accepted"] is False


def test_positive_acceptance_requires_complete_affirmative_audit_and_citation():
    answer = "CogniGraph is an AI-powered Socratic tutoring system [CogniGraph.pdf, p. 1]."
    audit = {
        "supported": True,
        "unsupported_claims": [],
        "invalid_citations": [],
        "uncited_claims": [],
    }
    assert grounding_decision(answer, audit, EVIDENCE)["accepted"] is True


def test_missing_uncited_claims_field_fails_closed():
    answer = "CogniGraph is a tutoring system [CogniGraph.pdf, p. 1]."
    audit = {"supported": True, "unsupported_claims": [], "invalid_citations": []}
    assert grounding_decision(answer, audit, EVIDENCE)["accepted"] is False


def test_objective_questions_trigger_broader_retrieval():
    assert is_objective_overview_query("What is the main objective of this project?")
    assert is_objective_overview_query("List the key deliverables from this PDF")
    assert not is_objective_overview_query("What is gradient descent?")


if __name__ == "__main__":
    tests = [
        test_parenthesized_citations_are_recognized_and_normalized,
        test_valid_multiple_citations_pass_source_membership,
        test_unknown_page_is_rejected,
        test_missing_citation_is_rejected,
        test_unsupported_audit_is_rejected_even_with_valid_citation,
        test_positive_acceptance_requires_complete_affirmative_audit_and_citation,
        test_missing_uncited_claims_field_fails_closed,
        test_objective_questions_trigger_broader_retrieval,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print("All grounding tests passed.")
