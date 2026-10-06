"""
quick_eval.py — Single query through all 4 DeepEval metrics, to check the
pipeline end to end without running the whole golden dataset.

Run from backend/:
    python eval/quick_eval.py
    python eval/quick_eval.py "What are the prerequisites for CS 203?"
"""

import sys

from common import load_profile, make_metrics, print_summary, run_pipeline

from deepeval import evaluate
from deepeval.evaluate.configs import AsyncConfig, CacheConfig
from deepeval.test_case import LLMTestCase

QUERY = "What are the prerequisites for CS 301?"
EXPECTED_ANSWER = "CS 301 requires CS 203 (Computer Organization) as a prerequisite."

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) or QUERY
    expected = EXPECTED_ANSWER if query == QUERY else None

    answer, context = run_pipeline(query, load_profile())
    print(f"Query: {query}\n\nAnswer: {answer}\n\nSources retrieved: {len(context)}")
    for block in context:
        print(f"  {block.splitlines()[0][:100]}")

    if not context:
        print("Nothing retrieved — skipping eval.")
        sys.exit(0)

    tc = LLMTestCase(
        input=query,
        actual_output=answer,
        expected_output=expected,
        retrieval_context=context,
        name="quick",
    )
    metrics = make_metrics()
    if expected is None:
        # Precision and recall need an expected answer
        metrics = metrics[:2]

    results = evaluate(
        test_cases=[tc],
        metrics=metrics,
        async_config=AsyncConfig(run_async=False),
        cache_config=CacheConfig(write_cache=False),
    )
    print_summary(results)
