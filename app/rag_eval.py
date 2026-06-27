from __future__ import annotations

import re
from collections.abc import Callable

from app.schemas import RagEvalCitation, RagEvalQuestion, RagEvalResult, RagEvaluationOut, RetrievedContext


def evaluate_retrieval(
    *,
    questions: list[RagEvalQuestion],
    embed: Callable[[str], list[float]],
    search: Callable[[list[float], int], list[RetrievedContext]],
) -> RagEvaluationOut:
    results = [
        evaluate_question(question=question, contexts=search(embed(question.question), question.top_k))
        for question in questions
    ]
    passed = sum(result.passed for result in results)
    total = len(results)
    return RagEvaluationOut(
        ok=total > 0 and passed == total,
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=round(passed / total, 4) if total else 0.0,
        results=results,
    )


def evaluate_question(
    *,
    question: RagEvalQuestion,
    contexts: list[RetrievedContext],
) -> RagEvalResult:
    citations = [
        RagEvalCitation(
            source=context.source,
            score=context.score,
            excerpt=excerpt(context.text),
            matched_expected_source=context.source == question.expected_source,
            matched_terms=matched_terms(context.text, question.required_terms),
        )
        for context in contexts
    ]
    top = contexts[0] if contexts else None
    expected_contexts = [
        context for context in contexts if context.source == question.expected_source
    ]
    expected_text = " ".join(context.text for context in expected_contexts)
    matched = matched_terms(expected_text, question.required_terms)
    missing = [term for term in question.required_terms if term not in matched]
    matched_score = max((context.score for context in expected_contexts), default=None)
    matched_source = matched_score is not None
    score_ok = matched_score is not None and matched_score >= question.score_floor
    return RagEvalResult(
        question=question.question,
        expected_source=question.expected_source,
        required_terms=question.required_terms,
        top_k=question.top_k,
        score_floor=question.score_floor,
        top_source=top.source if top else None,
        top_score=top.score if top else None,
        matched_source=matched_source,
        matched_score=matched_score,
        matched_terms=matched,
        missing_terms=missing,
        citations=citations,
        passed=matched_source and score_ok and not missing,
    )


def matched_terms(text: str, terms: list[str]) -> list[str]:
    lower_text = text.lower()
    return [term for term in terms if term.lower() in lower_text]


def excerpt(text: str, max_chars: int = 220) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3].rstrip()}..."
