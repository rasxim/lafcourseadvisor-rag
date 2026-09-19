"""
eval/run_eval.py — DeepEval evaluation of the Lafayette RAG pipeline.

Metrics: Faithfulness, Answer Relevancy, Contextual Precision, Contextual Recall
Judge model: gemini-2.5-flash (via DeepEval's GeminiModel wrapper)

Run from the project root:
    python eval/run_eval.py
"""

import json
import os
import sys
from pathlib import Path

# Ensure project root is on the path so we can import rag / retriever
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
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(temperature=0.0),
            contents=prompt,
        )
        return response.text

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return "gemini-2.0-flash"

judge = GeminiJudge()

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
faithfulness        = FaithfulnessMetric(threshold=0.7,  model=judge, include_reason=True)
answer_relevancy    = AnswerRelevancyMetric(threshold=0.7, model=judge, include_reason=True)
contextual_precision = ContextualPrecisionMetric(threshold=0.7, model=judge, include_reason=True)
contextual_recall   = ContextualRecallMetric(threshold=0.7, model=judge, include_reason=True)

# ---------------------------------------------------------------------------
# Load golden dataset and build test cases
# ---------------------------------------------------------------------------
DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
dataset      = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

retriever = Retriever()

def build_test_case(entry: dict) -> LLMTestCase | None:
    query            = entry["query"]
    expected_answer  = entry["expected_answer"]

    # Get retrieval context
    chunks  = retriever.retrieve(query)
    context = [c["text"] for c in chunks] if chunks else []

    # Get pipeline answer
    actual_answer = ask(query)

    # Off-topic queries: skip metric scoring — just verify the canned reply
    if entry["category"] == "off_topic":
        passed = "I can only help" in actual_answer
        print(f"[{entry['id']}] off-topic gate: {'PASS' if passed else 'FAIL'} | answer: {actual_answer[:80]}")
        return None

    if not context:
        print(f"[{entry['id']}] SKIP — no chunks retrieved")
        return None

    return LLMTestCase(
        input=query,
        actual_output=actual_answer,
        expected_output=expected_answer,
        retrieval_context=context,
        name=entry["id"],
    )


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Set QUICK=1 to run only 1 test case (saves API tokens)
    import sys
    quick = "--quick" in sys.argv
    entries = dataset[:1] if quick else dataset

    print("Building test cases...\n")
    test_cases = []
    for entry in entries:
        tc = build_test_case(entry)
        if tc:
            test_cases.append(tc)

    print(f"\nRunning DeepEval on {len(test_cases)} test cases...\n")

    results = evaluate(
        test_cases=test_cases,
        metrics=[
            faithfulness,
            answer_relevancy,
            contextual_precision,
            contextual_recall,
        ],
        print_results=True,
        write_cache=False,
    )

    # ---------------------------------------------------------------------------
    # Summary table
    # ---------------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("EVAL SUMMARY")
    print("=" * 60)

    metric_scores: dict[str, list[float]] = {
        "Faithfulness":          [],
        "Answer Relevancy":      [],
        "Contextual Precision":  [],
        "Contextual Recall":     [],
    }

    metric_map = {
        "Faithfulness":         faithfulness,
        "Answer Relevancy":     answer_relevancy,
        "Contextual Precision": contextual_precision,
        "Contextual Recall":     contextual_recall,
    }

    for tc in test_cases:
        for label, metric in metric_map.items():
            score = metric.score
            if score is not None:
                metric_scores[label].append(score)

    for label, scores in metric_scores.items():
        if scores:
            avg = sum(scores) / len(scores)
            print(f"  {label:<25} avg={avg:.3f}  (n={len(scores)})")
        else:
            print(f"  {label:<25} no scores")

    print("=" * 60)
