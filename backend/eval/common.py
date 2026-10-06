"""Shared pieces for the eval scripts: judge model, metrics, and pipeline runner."""

import json
import os
import re
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    FaithfulnessMetric,
)
from deepeval.models import DeepEvalBaseLLM
from google import genai
from google.genai import errors, types

import rag

THRESHOLD = 0.7
OFF_TOPIC_REPLIES = ("I can only help", rag.NO_CONTEXT_REPLY)
PROFILE_PATH = BACKEND_DIR / "student_profile.json"


def _call_with_backoff(fn, attempts: int = 8):
    """Retry rate limits and transient errors, waiting as long as Gemini asks.

    The free tier allows a few requests per minute, and an eval run makes dozens.
    """
    for attempt in range(attempts):
        try:
            return fn()
        except errors.APIError as e:
            if getattr(e, "code", None) not in rag.RETRY_CODES or attempt == attempts - 1:
                raise
            if "PerDay" in str(e):
                raise SystemExit("Gemini daily quota exhausted — eval can't continue until it resets.") from e
            m = re.search(r"retry in ([\d.]+)s", str(e))
            wait = float(m.group(1)) + 1 if m else 15
            print(f"  (Gemini {e.code}, waiting {wait:.0f}s)", flush=True)
            time.sleep(wait)


class GeminiJudge(DeepEvalBaseLLM):
    """DeepEval judge backed by the same Gemini model the app uses."""

    def __init__(self):
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def load_model(self):
        return self._client

    def generate(self, prompt: str) -> str:
        return _call_with_backoff(
            lambda: self._client.models.generate_content(
                model=rag.MODEL,
                config=types.GenerateContentConfig(temperature=0.0),
                contents=prompt,
            ).text
        )

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return rag.MODEL


def make_metrics() -> list:
    judge = GeminiJudge()
    return [
        FaithfulnessMetric(threshold=THRESHOLD, model=judge, include_reason=True),
        AnswerRelevancyMetric(threshold=THRESHOLD, model=judge, include_reason=True),
        ContextualPrecisionMetric(threshold=THRESHOLD, model=judge, include_reason=True),
        ContextualRecallMetric(threshold=THRESHOLD, model=judge, include_reason=True),
    ]


def load_profile() -> dict | None:
    """The local degree audit, if present (it's gitignored)."""
    if PROFILE_PATH.exists():
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return None


def run_pipeline(query: str, profile: dict | None) -> tuple[str, list[str]]:
    """Answer the query exactly as /ask would. Returns (answer, retrieval_context)."""
    # rag's own retries give up after ~26s and return BUSY_REPLY, which would be
    # scored as a real answer. Retry the whole call on that instead.
    for _ in range(8):
        text, _, context = rag.answer_with_context(query, profile)
        if text != rag.BUSY_REPLY:
            return text, context
        print("  (pipeline rate-limited, waiting 60s)", flush=True)
        time.sleep(60)
    raise RuntimeError(f"Gemini stayed unavailable for: {query}")


def print_summary(results) -> None:
    """Average each metric across test cases and list failures."""
    scores: dict[str, list[float]] = {}
    failures: list[str] = []
    for tr in results.test_results:
        for md in tr.metrics_data or []:
            if md.score is not None:
                scores.setdefault(md.name, []).append(md.score)
            if not md.success:
                failures.append(f"  {tr.name:<14} {md.name:<22} {md.score if md.score is not None else 'error'}")

    print("\n" + "=" * 60)
    print("EVAL SUMMARY")
    print("=" * 60)
    for name, vals in scores.items():
        print(f"  {name:<25} avg={sum(vals) / len(vals):.3f}  (n={len(vals)})")
    if failures:
        print("\nBelow threshold:")
        print("\n".join(failures))
    print("=" * 60)
