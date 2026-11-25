#!/usr/bin/env python3
"""Authenticated end-to-end RAG/citation demo against the local CogniGraph API.

Requires COGNIGRAPH_DEMO_USERNAME, COGNIGRAPH_DEMO_PASSWORD, and optionally
COGNIGRAPH_DEMO_COURSE_ID (defaults to 4). Does not print credentials or tokens.
Each test creates a new chat and makes a real, billable model request.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from llm.grounding import extract_citations  # noqa: E402

BASE_URL = os.environ.get("COGNIGRAPH_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
USERNAME = os.environ.get("COGNIGRAPH_DEMO_USERNAME", "")
PASSWORD = os.environ.get("COGNIGRAPH_DEMO_PASSWORD", "")
COURSE_ID = int(os.environ.get("COGNIGRAPH_DEMO_COURSE_ID", "4"))
TIMEOUT = int(os.environ.get("COGNIGRAPH_DEMO_TIMEOUT", "180"))

CASES = [
    {
        "name": "project objective",
        "query": "According to the selected PDF, what is CogniGraph's main objective? Explain briefly and cite the relevant page(s).",
        "required_cited_pages": {1},
        "abstention": False,
    },
    {
        "name": "key deliverables",
        "query": "According to the selected PDF, what are the project's key deliverables? Summarize briefly and cite the page.",
        "required_cited_pages": {19},
        "abstention": False,
    },
    {
        "name": "memory layer",
        "query": "According to the selected PDF, what does the Memory Layer use to retrieve course-aware answers? Cite the page.",
        "required_cited_pages": {7},
        "abstention": False,
    },
    {
        "name": "fine-tuning versus RAG teaching",
        "query": "Teach me the difference between fine-tuning and RAG using only the selected PDF. Explain each role simply, cite the page(s), and finish with exactly one comprehension question.",
        "required_cited_pages": {7},
        "exactly_one_question": True,
        "abstention": False,
    },
    {
        "name": "unsupported detail must abstain",
        "query": "According to the selected PDF, which exact version of PostgreSQL is required to run CogniGraph?",
        "required_cited_pages": set(),
        "abstention": True,
    },
]


def call_api(path: str, payload=None, token: str | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(BASE_URL + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"detail": raw[:400]}
        return exc.code, body


def norm_source(value: str) -> str:
    return "".join(str(value or "").casefold().split())


def citation_pair(reference: str):
    match = re.match(r"^(.*?),\s*p\.\s*(\d+)\s*$", reference, flags=re.I)
    if not match:
        return None
    return norm_source(match.group(1)), int(match.group(2))


def main() -> int:
    if not USERNAME or not PASSWORD:
        print("Missing credentials. Set COGNIGRAPH_DEMO_USERNAME and COGNIGRAPH_DEMO_PASSWORD interactively.")
        return 2

    status, login = call_api("/api/auth/login", {"username": USERNAME, "password": PASSWORD})
    if status != 200 or not login.get("token"):
        print(f"FAIL: login HTTP {status}; detail={login.get('detail', 'no token returned')}")
        return 2
    token = login["token"]

    status, courses_payload = call_api("/api/courses", token=token)
    if status != 200 or not isinstance(courses_payload, list):
        print(f"FAIL: could not list courses; HTTP {status}")
        return 2
    matching = [item for item in courses_payload if int(item.get("id", -1)) == COURSE_ID]
    if not matching:
        print(f"FAIL: course id {COURSE_ID} is not available to the signed-in account.")
        print("Available course IDs:", [item.get("id") for item in courses_payload])
        return 2

    print(f"CogniGraph RAG demo | course_id={COURSE_ID} | base_url={BASE_URL}")
    outcomes = []
    for case in CASES:
        status, result = call_api(
            "/api/chat",
            {"course_id": COURSE_ID, "message": case["query"]},
            token=token,
        )
        answer = str(result.get("answer") or "")
        sources = result.get("sources") or []
        available_pairs = {
            (norm_source(source.get("source", "")), int(source.get("page", 0)))
            for source in sources
            if source.get("source") and source.get("page") is not None
        }
        refs = extract_citations(answer)
        pairs = [citation_pair(ref) for ref in refs]
        pairs = [pair for pair in pairs if pair is not None]
        citations_in_context = all(pair in available_pairs for pair in pairs)
        cited_pages = {page for _, page in pairs}
        required_pages_ok = set(case["required_cited_pages"]).issubset(cited_pages)

        if case.get("abstention"):
            lowered = answer.casefold()
            abstention_terms = (
                "not specified", "does not specify", "doesn't specify",
                "not mentioned", "does not establish", "cannot verify",
                "could not verify", "not enough information", "will not guess",
            )
            content_ok = any(term in lowered for term in abstention_terms)
        else:
            content_ok = bool(answer.strip()) and required_pages_ok and bool(refs)

        if case.get("exactly_one_question"):
            content_ok = content_ok and answer.count("?") == 1

        passed = status == 200 and content_ok and citations_in_context
        outcomes.append(passed)
        print("\n" + ("PASS" if passed else "FAIL") + f" — {case['name']} (HTTP {status})")
        print("Question:", case["query"])
        print("Answer:", answer.replace("\n", " "))
        print("Citations:", refs or "NONE")
        print("Retrieved source pages:", sorted(available_pairs, key=lambda pair: (pair[0], pair[1])))
        if not citations_in_context:
            print("Problem: one or more answer citations do not match source/page pairs returned by retrieval.")
        if not case.get("abstention") and not required_pages_ok:
            print("Problem: expected cited page(s) missing:", sorted(case["required_cited_pages"]))
        if case.get("abstention") and not content_ok:
            print("Problem: unsupported-detail test did not clearly abstain.")
        if case.get("exactly_one_question") and answer.count("?") != 1:
            print("Problem: teaching answer should end with exactly one comprehension question.")

    passed_count = sum(outcomes)
    print(f"\nDEMO RESULT: {passed_count}/{len(outcomes)} passed")
    print("Inspect journal logs for RAG_GROUNDING summary_verified=true/false for each chat.")
    return 0 if all(outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
