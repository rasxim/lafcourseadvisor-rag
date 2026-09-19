import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from retriever import Retriever

load_dotenv()

_client    = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_retriever = Retriever()

STUDENT_PROFILE: dict = json.loads(
    Path("student_profile.json").read_text(encoding="utf-8")
)

MODEL = "gemini-3.6-flash"

OFF_TOPIC_REPLY = (
    "I can only help with Lafayette academic and degree planning questions."
)

SYSTEM_PROMPT = """\
You are an AI academic advisor for Lafayette College.

Your purpose is to answer questions about Lafayette College academic policies,
degree requirements, majors, minors, graduation requirements, courses,
prerequisites, registration rules, and the student's academic progress.

You will receive:
1. Relevant excerpts from the Lafayette College catalog (retrieved context).
2. Optionally, the student's degree audit (only for student-specific questions).
3. The user's question.

## Source Rules

The retrieved catalog excerpts are the ONLY authoritative source for
academic policies, course descriptions, and degree requirements.

NEVER use outside knowledge about Lafayette College. If a fact about
Lafayette is not present in the retrieved catalog excerpts, treat it as
unknown and say so.

The student profile is provided only to personalize answers about the
student's own academic progress. Do NOT use the student profile as
evidence for what requirements exist — always derive requirements
exclusively from the catalog excerpts.

If the retrieved context is insufficient to answer the question
confidently, say so explicitly rather than guessing or inferring.

## Answering Rules

- Base every factual claim ONLY on the retrieved catalog excerpts.
- Do not invent or infer policies, prerequisites, or requirements.
- Cite page numbers inline when making factual claims, e.g. (p. 45).
- If multiple retrieved passages disagree, acknowledge the ambiguity.
- If information is incomplete, explain exactly what is missing.

## Student-Specific Questions

For questions about the student's own degree progress (remaining courses,
graduation status, requirements met, course planning, etc.), reason in order:

1. Identify the relevant requirement from the catalog excerpts.
2. Compare it with the student's profile (completed courses, credits, GPA, etc.).
3. Explain the reasoning step by step.
4. State the conclusion clearly.

## Course Questions

When discussing a course:
- Always include the course code.
- Mention prerequisites if present in the retrieved context.
- Distinguish between required and elective.
- Explain why the course is relevant to the question.

## Policy Questions

- Explain the rule clearly and directly.
- Note important exceptions if present in the retrieved context.
- Avoid adding detail not found in the retrieved passages.

## Formatting

- Prefer short, well-organized answers.
- Use bullet points when listing multiple items.
- When possible, end with a Sources section:

Sources:
- p. X – [brief description]
- p. Y – [brief description]

## Off-topic Questions

Only answer questions about:
- Lafayette academics, majors, and minors
- Graduation and degree requirements
- Course planning and prerequisites
- Academic policies and registration
- The student's degree progress

For any other topic, respond ONLY with:
"I can only help with Lafayette academic and degree planning questions."
"""

# Patterns that indicate a question is about the student's own academic situation.
# When matched, the student profile is included in the prompt.
_STUDENT_RE = re.compile(
    r"\b(my |i |i'm |i've |i need|i still|am i\b|do i\b|have i\b|will i\b|"
    r"remaining|still need|on track|my major|my course|my degree|"
    r"my progress|my plan|my graduation|my transcript)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def is_student_specific_query(query: str) -> bool:
    """True when the query is about the student's personal academic situation."""
    return bool(_STUDENT_RE.search(query))


def build_catalog_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered, structured context block."""
    parts = []
    for i, c in enumerate(chunks, 1):
        hp      = c.get("heading_path", "")
        section = c.get("section", "")
        sp      = c.get("start_page", "?")
        ep      = c.get("end_page",   "?")
        pages   = str(sp) if sp == ep else f"{sp}–{ep}"

        header = f"Source {i}"
        if hp:
            header += f"\nHeading: {hp}"
        header += f"\nSection: {section}"
        header += f"\nPages: {pages}"

        parts.append(f"{header}\n\nContent:\n{c['text']}")

    return "\n\n---\n\n".join(parts)


def build_prompt(query: str, chunks: list[dict], student_profile: dict | None = None) -> str:
    """Assemble the user-turn prompt, including the student profile only when
    the query is student-specific."""
    sections: list[str] = []

    profile = student_profile if student_profile is not None else STUDENT_PROFILE
    if is_student_specific_query(query):
        sections.append(
            "## Student Degree Audit\n"
            f"```json\n{json.dumps(profile, indent=2)}\n```"
        )

    sections.append(
        f"## Relevant Catalog Excerpts\n{build_catalog_context(chunks)}"
    )

    sections.append(f"## Question\n{query}")

    return "\n\n".join(sections)


def generate_answer(prompt: str) -> str:
    """Send the assembled prompt to the LLM and return the raw response text."""
    response = _client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0,
        ),
        contents=prompt,
    )
    return response.text.strip()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def ask(query: str, student_profile: dict | None = None) -> str:
    chunks = _retriever.retrieve(query)
    if not chunks:
        return OFF_TOPIC_REPLY
    prompt = build_prompt(query, chunks, student_profile=student_profile)
    return generate_answer(prompt)


if __name__ == "__main__":
    test_queries = [
        "What is the pre requisite for CS 303?"
    ]
    for q in test_queries:
        print(f"\nQ: {q}")
        print(f"A: {ask(q)}")
        print("-" * 60)
