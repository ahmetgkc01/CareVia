import json
import math
from pathlib import Path

from apps.assistant.embeddings import EmbeddingError, semantic_search
from apps.assistant.services import create_reply, normalize, safety_reply


def load_eval_cases(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError("The eval dataset must be a JSON list of objects.")
    return data


def percentage(numerator: int, denominator: int) -> float | None:
    if not denominator:
        return None
    return round(100 * numerator / denominator, 2)


def percentile(values: list[float], percentile_value: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil((percentile_value / 100) * len(ordered)) - 1)
    return round(ordered[index], 2)


def evaluate_safety(cases: list[dict]) -> dict:
    unsafe_total = unsafe_blocked = safe_total = safe_blocked = 0
    failures = []
    for case in (item for item in cases if item.get("kind") == "safety"):
        expected_code = case.get("expected_safety_code") or ""
        result = safety_reply(case["question"], case.get("language", "tr"))
        actual_code = result.safety_code if result else ""
        if expected_code:
            unsafe_total += 1
            unsafe_blocked += int(actual_code == expected_code)
        else:
            safe_total += 1
            safe_blocked += int(bool(actual_code))
        if actual_code != expected_code:
            failures.append(
                {
                    "id": case.get("id"),
                    "expected": expected_code,
                    "actual": actual_code,
                }
            )
    return {
        "unsafe_cases": unsafe_total,
        "safety_recall_percent": percentage(unsafe_blocked, unsafe_total),
        "safe_cases": safe_total,
        "false_positive_percent": percentage(safe_blocked, safe_total),
        "failures": failures,
    }


def evaluate_retrieval(cases: list[dict], ks: tuple[int, ...] = (1, 3, 5)) -> dict:
    retrieval_cases = [item for item in cases if item.get("kind") == "retrieval"]
    hits = {k: 0 for k in ks}
    failures = []
    skipped = []
    max_k = max(ks)
    evaluated = 0
    for case in retrieval_cases:
        try:
            matches = semantic_search(case["question"], limit=max_k)
        except EmbeddingError as exc:
            skipped.append({"id": case.get("id"), "reason": str(exc)})
            continue
        evaluated += 1
        actual = [match.chunk.source_key for match in matches]
        expected = set(case.get("expected_sources", []))
        for k in ks:
            hits[k] += int(bool(expected.intersection(actual[:k])))
        if not expected.intersection(actual[:max_k]):
            failures.append(
                {"id": case.get("id"), "expected": sorted(expected), "actual": actual}
            )
    return {
        "cases": len(retrieval_cases),
        "evaluated": evaluated,
        **{f"recall_at_{k}_percent": percentage(hits[k], evaluated) for k in ks},
        "failures": failures,
        "skipped": skipped,
    }


def groundedness_proxy(reply, case: dict) -> bool:
    actual_sources = {
        item.get("source_key") for item in reply.sources if item.get("source_key")
    }
    expected_sources = set(case.get("expected_sources", []))
    normalized_content = normalize(reply.content)
    required = [normalize(value) for value in case.get("required_phrases", [])]
    forbidden = [normalize(value) for value in case.get("forbidden_phrases", [])]
    source_ok = not expected_sources or bool(expected_sources.intersection(actual_sources))
    return (
        source_ok
        and all(value in normalized_content for value in required)
        and not any(value in normalized_content for value in forbidden)
    )


def evaluate_assistant(cases: list[dict], user) -> dict:
    from time import perf_counter

    assistant_cases = [item for item in cases if item.get("kind") == "assistant"]
    latencies = []
    costs = []
    input_tokens = output_tokens = grounded = 0
    failures = []
    for case in assistant_cases:
        started_at = perf_counter()
        reply = create_reply(
            user,
            case["question"],
            case.get("language", "tr"),
            case.get("patient_id"),
        )
        latencies.append((perf_counter() - started_at) * 1000)
        costs.append(float(reply.estimated_cost_usd))
        input_tokens += reply.input_tokens
        output_tokens += reply.output_tokens
        passed = groundedness_proxy(reply, case)
        grounded += int(passed)
        expected_category = case.get("expected_category")
        if not passed or (expected_category and reply.category != expected_category):
            failures.append(
                {
                    "id": case.get("id"),
                    "category": reply.category,
                    "groundedness_proxy_passed": passed,
                }
            )
    return {
        "cases": len(assistant_cases),
        "groundedness_proxy_percent": percentage(grounded, len(assistant_cases)),
        "latency_ms_p50": percentile(latencies, 50),
        "latency_ms_p95": percentile(latencies, 95),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_generation_cost_usd": round(sum(costs), 8),
        "failures": failures,
        "note": (
            "Groundedness is a deterministic citation/phrase proxy, not semantic entailment."
        ),
    }
