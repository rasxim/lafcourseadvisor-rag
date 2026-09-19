"""
quick_eval.py — Single test case eval to verify pipeline without burning API tokens.
Runs 1 query through all 4 DeepEval metrics (~5 API calls total).

Run from project root:
    python eval/quick_eval.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from deepeval import evaluate
from deepeval.metrics import (
    FaithfulnessMetric,
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
)
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase
from google import genai
from google.genai import types

from rag import ask
from retriever import Retriever

# ---------------------------------------------------------------------------
# Judge model — Gemini 2.0 Flash
# ---------------------------------------------------------------------------
class GeminiJudge(DeepEvalBaseLLM):
    def __init__(self):
        self._client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    def load_model(self):
        return self._client

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model="gemini-3.6-flash",
            config=types.GenerateContentConfig(temperature=0.0),
            contents=prompt,
        )
        return response.text

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return "gemini-3.6-flash"

judge = GeminiJudge()

faithfulness        = FaithfulnessMetric(threshold=0.7, model=judge, include_reason=True)
answer_relevancy    = AnswerRelevancyMetric(threshold=0.7, model=judge, include_reason=True)
contextual_precision = ContextualPrecisionMetric(threshold=0.7, model=judge, include_reason=True)
contextual_recall   = ContextualRecallMetric(threshold=0.7, model=judge, include_reason=True)

# ---------------------------------------------------------------------------
# Single test query
# ---------------------------------------------------------------------------
QUERY           = "What are the prerequisites for CS 301?"
EXPECTED_ANSWER = "CS 301 requires CS 203 (Computer Organization) as a prerequisite."

if __name__ == "__main__":
    retriever = Retriever()

    print(f"Query: {QUERY}\n")

    chunks  = retriever.retrieve(QUERY)
    context = [c["text"] for c in chunks]
    answer  = ask(QUERY)

    print(f"Answer: {answer}\n")
    print(f"Chunks retrieved: {len(chunks)}")
    for c in chunks:
        print(f"  [{c['score']:.3f}] {c['text'][:80]}...")

    if not context:
        print("No chunks retrieved — skipping eval.")
        sys.exit(0)

    tc = LLMTestCase(
        input=QUERY,
        actual_output=answer,
        expected_output=EXPECTED_ANSWER,
        retrieval_context=context,
    )

    print("\nRunning metrics...\n")
    results = evaluate(
        test_cases=[tc],
        metrics=[faithfulness, answer_relevancy, contextual_precision, contextual_recall],
    )
 
 
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    for metric, name in [
        (faithfulness,         "Faithfulness"),
        (answer_relevancy,     "Answer Relevancy"),
        (contextual_precision, "Contextual Precision"),
        (contextual_recall,    "Contextual Recall"),
    ]:
        status = "PASS" if metric.score >= 0.7 else "FAIL"
        print(f"  {name:<25} {metric.score:.3f}  [{status}]")
        if metric.reason:
            print(f"    Reason: {metric.reason}")
    print("=" * 50)
