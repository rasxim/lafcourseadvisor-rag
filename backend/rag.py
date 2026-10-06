"""Answer generation over retrieved catalog units."""

import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from retriever import Retrieval, Retriever

load_dotenv()

_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_retriever = Retriever()

MODEL = "gemini-3.6-flash"
MAX_SOURCE_CHARS = 2000
CONTEXT_SEPARATOR = "\n\n---\n\n"

NO_CONTEXT_REPLY = (
    "I couldn't find anything in the Lafayette catalog for that. Try asking about a "
    "specific course, major, minor, or academic policy."
)

_SECTION_BY_TYPE = {
    "course": "course_description",
    "program": "major_requirements",
    "department": "major_requirements",
    "policy": "academic_policy",
    "other": "other",
}

SYSTEM_PROMPT = """\
You are an academic advisor for Lafayette College.

You answer questions about Lafayette's courses, majors, minors, degree
requirements, prerequisites, academic policies, and a student's own progress
toward their degree.

## Sources

The numbered catalog sources you are given are your ONLY authority on what
Lafayette requires. Never use outside knowledge about Lafayette. If the sources
don't cover something, say so plainly instead of guessing.

The student profile, when present, tells you what the student has already
completed. Use it to personalize your answer — never as evidence for what the
requirements are. Requirements come only from the catalog sources.

Cite sources inline with bracketed numbers matching the source you used, like
[1] or [2][3]. Cite the specific source a claim comes from, not everything.

## Course planning

When the student asks what to take, or about adding a major or minor, work
through it in order:

1. State the requirements from the catalog sources.
2. Compare them against what the student has already completed.
3. List what is still outstanding.
4. Recommend specific courses they are eligible for now — check the prerequisite
   reference and do not recommend a course whose prerequisites they haven't met.
5. Note any policy limits that apply, such as how many courses may be shared
   between two majors.

If something material is missing (their class year, a requirement the catalog
doesn't spell out), say what you'd need rather than assuming.

## Style

Be direct and specific. Use short paragraphs, bullets for lists, and always give
course codes. Lead with the answer, then the reasoning. Don't pad.

Only answer questions about Lafayette academics. For anything else, reply:
"I can only help with Lafayette academic and degree planning questions."
"""


def build_context(retrieval: Retrieval) -> tuple[str, list[dict]]:
    """Render retrieved units as numbered sources for the prompt and the API."""
    blocks: list[str] = []
    sources: list[dict] = []

    for n, hit in enumerate(retrieval.hits, 1):
        u = hit.unit
        pages = str(u["start_page"]) if u["start_page"] == u["end_page"] else f"{u['start_page']}–{u['end_page']}"
        label = u["name"]
        if u["type"] == "program" and u.get("kind"):
            label = f"{label} [{u['kind']}]"

        blocks.append(f"[{n}] {label} (pages {pages})\n{u['text']}")
        sources.append(
            {
                "text": u["text"][:MAX_SOURCE_CHARS],
                "score": hit.score,
                "start_page": u["start_page"],
                "end_page": u["end_page"],
                "heading_path": f"{u['h1']} > {u['name']}" if u.get("h1") else u["name"],
                "section": _SECTION_BY_TYPE.get(u["type"], "other"),
                "metadata": {"unit_id": u["id"], "unit_type": u["type"], "reason": hit.reason},
            }
        )

    if retrieval.digest:
        n = len(blocks) + 1
        lo, hi = retrieval.digest_pages
        blocks.append(
            f"[{n}] Prerequisite reference for courses named above (pages {lo}–{hi})\n"
            f"{retrieval.digest}"
        )
        sources.append(
            {
                "text": retrieval.digest[:MAX_SOURCE_CHARS],
                "score": 1.0,
                "start_page": lo,
                "end_page": hi,
                "heading_path": "Courses > Prerequisite reference",
                "section": "course_description",
                "metadata": {"unit_id": "digest", "unit_type": "digest", "reason": "prerequisites for referenced courses"},
            }
        )

    return CONTEXT_SEPARATOR.join(blocks), sources


def build_prompt(query: str, context: str, profile: dict | None, intent: str) -> str:
    parts = []
    if profile:
        parts.append(f"## Student Profile\n```json\n{json.dumps(profile, indent=2)}\n```")
    parts.append(f"## Catalog Sources\n{context}")
    if intent == "planning":
        parts.append(
            "## Task\nThis is a planning question. Compare the requirements against what "
            "the student has completed, and recommend only courses whose prerequisites they meet."
        )
    parts.append(f"## Question\n{query}")
    return "\n\n".join(parts)


RETRY_CODES = (429, 500, 502, 503)
RETRY_DELAYS = (1, 3, 7, 15)

BUSY_REPLY = (
    "The model is temporarily unavailable (Gemini is reporting high demand). "
    "Your question and the catalog sources were retrieved fine — please try again in a moment."
)


def generate_answer(prompt: str) -> str:
    """Call the model, retrying transient server errors with backoff.

    Gemini's free tier returns 503 under load often enough that a demo needs to
    ride it out rather than surface a stack trace.
    """
    for attempt, delay in enumerate(RETRY_DELAYS + (None,)):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.0,
                ),
                contents=prompt,
            )
            return (response.text or "").strip()
        except errors.APIError as e:
            if getattr(e, "code", None) not in RETRY_CODES or delay is None:
                if getattr(e, "code", None) in RETRY_CODES:
                    return BUSY_REPLY
                raise
            time.sleep(delay)
    return BUSY_REPLY


def answer_with_context(query: str, student_profile: dict | None = None) -> tuple[str, list[dict], list[str]]:
    """Like answer(), but also returns the full source blocks the model saw (for eval)."""
    profile = student_profile or None
    retrieval = _retriever.retrieve(query, profile)
    if not retrieval.hits:
        return NO_CONTEXT_REPLY, [], []

    context, sources = build_context(retrieval)
    prompt = build_prompt(query, context, profile, retrieval.intent)
    return generate_answer(prompt), sources, context.split(CONTEXT_SEPARATOR)


def answer(query: str, student_profile: dict | None = None) -> tuple[str, list[dict]]:
    """Retrieve once, answer once. Returns (answer_text, sources)."""
    text, sources, _ = answer_with_context(query, student_profile)
    return text, sources


if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "What is the prerequisite for CS 203?"
    text, srcs = answer(q)
    print(f"Q: {q}\n\n{text}\n\nSources: {[s['heading_path'] for s in srcs]}")
