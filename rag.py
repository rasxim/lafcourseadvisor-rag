"""
rag.py — Prompt assembly + Gemini LLM call.
Combines retrieved catalog chunks + student profile -> answer.
"""

import json
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from retriever import Retriever

load_dotenv()

_client   = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_retriever = Retriever()

STUDENT_PROFILE = json.loads(
    Path("student_profile.json").read_text(encoding="utf-8")
)

SYSTEM_PROMPT = """\
You are a Lafayette College academic advisor.
Answer ONLY based on the provided context documents (catalog excerpts) and the \
student's degree audit below.
If the question is not about Lafayette courses, degree requirements, or academic \
policies, respond exactly: \
"I can only help with Lafayette degree planning questions."
Do not use outside knowledge. Be specific and cite course codes when relevant.\
"""

OFF_TOPIC_REPLY = "I can only help with Lafayette degree planning questions."


def ask(query: str) -> str:
    """Run the full RAG pipeline for a single query. Returns the answer string."""

    # 1. Retrieve relevant catalog chunks
    chunks = _retriever.retrieve(query)
    if not chunks:
        return OFF_TOPIC_REPLY

    # 2. Format retrieved context
    catalog_context = "\n\n---\n\n".join(
        f"[Page {c['metadata']['page']} | {c['metadata']['section_type']}]\n{c['text']}"
        for c in chunks
    )

    # 3. Assemble prompt
    prompt = f"""\
## Student Degree Audit
```json
{json.dumps(STUDENT_PROFILE, indent=2)}
```

## Relevant Catalog Excerpts
{catalog_context}

## Question
{query}
"""

    # 4. Call Gemini
    response = _client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
        contents=prompt,
    )

    return response.text.strip()


if __name__ == "__main__":
    test_queries = [
        "What CS courses do I still need to graduate?",
        "What courses do i need to take for the Documentary StoryMaking minor?",
        "What courses satisfy the writing requirement in my major?",
        "What are the pre requisites for Maths 182"
    ]
    for q in test_queries:
        print(f"\nQ: {q}")
        print(f"A: {ask(q)}")
        print("-" * 60)
