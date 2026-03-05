"""
RAG evaluation script.
Run from project root: python scripts/evaluate.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.settings import Settings
from app.services.rag_service import RAGService

TEST_CASES = [
    {
        "question": "What must all consumer-facing claims be?",
        "expected_keywords": ["truthful", "misleading"],
        "expected_citation": "marketing_policy.md",
    },
    {
        "question": "What is the Green content risk level?",
        "expected_keywords": ["low risk", "product facts"],
        "expected_citation": "marketing_policy.md",
    },
    {
        "question": "What approval is required for Red risk content?",
        "expected_keywords": ["mlr", "legal"],
        "expected_citation": "marketing_policy.md",
    },
    {
        "question": "What are the indications for ExampleBrand Vitamin C?",
        "expected_keywords": ["immune", "collagen"],
        "expected_citation": "product_facts.txt",
    },
    {
        "question": "What is the recommended daily dose for the Vitamin C tablet?",
        "expected_keywords": ["1 tablet", "daily"],
        "expected_citation": "product_facts.txt",
    },
]


def run_evaluation(rag: RAGService) -> None:
    passed = 0

    for i, case in enumerate(TEST_CASES, 1):
        result = rag.answer(case["question"])
        answer_lower = result.answer.lower()
        citations_str = " ".join(result.citations)

        keyword_results = {kw: kw.lower() in answer_lower for kw in case["expected_keywords"]}
        citation_hit = case["expected_citation"] in citations_str
        all_keywords_hit = all(keyword_results.values())
        case_passed = all_keywords_hit and citation_hit

        if case_passed:
            passed += 1

        status = "PASS" if case_passed else "FAIL"
        print(f"Q{i}: {case['question']}")
        print(f"   Answer:   {result.answer[:120]}...")
        kw_str = "  ".join(f"{'✓' if hit else '✗'} {kw}" for kw, hit in keyword_results.items())
        print(f"   Keywords: {kw_str}")
        print(f"   Citation: {'✓' if citation_hit else '✗'}  {case['expected_citation']}")
        print(f"   Result:   {status}")
        print()

    total = len(TEST_CASES)
    pct = int(passed / total * 100)
    print("-" * 40)
    print(f"Score: {passed}/{total} ({pct}%)")


if __name__ == "__main__":
    s = Settings()
    rag = RAGService(
        documents_dir=s.documents_dir,
        openai_api_key=s.openai_api_key,
        embedding_model=s.embedding_model,
        chat_model=s.chat_model,
        retrieval_k=s.retrieval_k,
        llm_temperature=s.llm_temperature,
    )
    run_evaluation(rag)
