"""
eval/run_eval.py — DeepEval evaluation of the Lafayette RAG pipeline.

Metrics: Faithfulness, Answer Relevancy, Contextual Precision, Contextual Recall
Judge model: the same Gemini model the app uses (rag.MODEL)

Student-specific questions use backend/student_profile.json if it exists.

Run from backend/:
    python eval/run_eval.py            # full golden dataset
    python eval/run_eval.py --quick    # first test case only
    python eval/run_eval.py gap_01 edge_02   # specific ids
"""

import json
import sys
from pathlib import Path

from common import OFF_TOPIC_REPLIES, load_profile, make_metrics, print_summary, run_pipeline

from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, CacheConfig
from deepeval.test_case import LLMTestCase

DATASET_PATH = Path(__file__).parent / "golden_dataset.json"


def build_test_case(entry: dict, profile: dict | None) -> LLMTestCase | None:
    answer, context = run_pipeline(entry["query"], profile)

    # Off-topic queries: no metrics, just check the pipeline declined
    if entry["category"] == "off_topic":
        passed = any(r in answer for r in OFF_TOPIC_REPLIES)
        print(f"[{entry['id']}] off-topic gate: {'PASS' if passed else 'FAIL'} | {answer[:80]}")
        return None

    if not context:
        print(f"[{entry['id']}] SKIP — nothing retrieved")
        return None

    print(f"[{entry['id']}] {len(context)} sources | {answer[:80]!r}")
    return LLMTestCase(
        input=entry["query"],
        actual_output=answer,
        expected_output=entry["expected_answer"],
        retrieval_context=context,
        name=entry["id"],
    )


if __name__ == "__main__":
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    args = sys.argv[1:]
    if "--quick" in args:
        entries = dataset[:1]
    elif args:
        entries = [e for e in dataset if e["id"] in args]
    else:
        entries = dataset

    profile = load_profile()
    print(f"Student profile: {'loaded' if profile else 'not found — gap questions run without one'}")
    print(f"Building {len(entries)} test cases...\n")
    test_cases = [tc for e in entries if (tc := build_test_case(e, profile))]

    if not test_cases:
        sys.exit(0)

    print(f"\nRunning DeepEval on {len(test_cases)} test cases...\n")
    results = evaluate(
        test_cases=test_cases,
        metrics=make_metrics(),
        async_config=AsyncConfig(run_async=False),
        cache_config=CacheConfig(write_cache=False),
    )
    print_summary(results)
