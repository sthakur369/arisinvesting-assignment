import json
import math
import sqlite3
import sys
import time
from pathlib import Path

# Allow running this file as: python eval/run_eval.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from assistant import ask
from config.config import DB_PATH


EVAL_FILE = Path(__file__).parent / "questions.json"
RESULTS_FILE = Path(__file__).parent / "results.json"


def open_gold_database():
    """Open a separate read-only connection for independently derived gold answers."""
    uri = DB_PATH.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def get_gold_result(connection, case):
    """Run the independent SQL answer stored in the evaluation set."""
    result_type = case.get("gold_result_type", "none")

    if result_type == "none":
        return None

    rows = connection.execute(
        case["gold_sql"],
        case.get("gold_params", [])
    ).fetchall()

    if result_type == "scalar":
        return rows[0][0] if rows else None

    if result_type == "list":
        return [row[0] for row in rows]

    raise ValueError(f"Unknown gold_result_type: {result_type}")


def results_match(actual, expected):
    """Compare structured results, allowing small floating-point differences."""
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return False
        return math.isclose(actual, expected, rel_tol=1e-6, abs_tol=0.01)

    return actual == expected


def run_evaluation():
    cases = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    gold_connection = open_gold_database()

    case_results = []

    try:
        for case in cases:
            gold_result = get_gold_result(gold_connection, case)

            start_time = time.perf_counter()
            error = None

            try:
                # Each case gets a fresh conversation to prevent test contamination.
                actual = ask(case["question"], case["user"])
            except Exception as exc:
                actual = None
                error = str(exc)

            latency = round(time.perf_counter() - start_time, 3)

            actual_status = actual.get("status") if actual else None
            actual_result = actual.get("result") if actual else None
            usage = actual.get("usage", {}) if actual else {}

            status_passed = actual_status == case["expected_status"]

            if case.get("gold_result_type") == "none":
                result_passed = actual_result is None
            else:
                result_passed = results_match(actual_result, gold_result)

            injection_passed = True
            forbidden_values = []

            if case.get("forbidden_text_sql"):
                forbidden_values = [
                    row[0] for row in gold_connection.execute(
                        case["forbidden_text_sql"],
                        case.get("forbidden_text_params", [])
                    ).fetchall()
                    if row[0]
                ]

                answer_text = actual.get("answer", "") if actual else ""
                injection_passed = not any(
                    value.lower() in answer_text.lower()
                    for value in forbidden_values
                )

            passed = (
                status_passed
                and result_passed
                and injection_passed
                and error is None
            )

            case_results.append({
                "id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "expected_status": case["expected_status"],
                "actual_status": actual_status,
                "gold_result": gold_result,
                "actual_result": actual_result,
                "status_passed": status_passed,
                "result_passed": result_passed,
                "prompt_injection_passed": injection_passed,
                "passed": passed,
                "latency_seconds": latency,
                "usage": usage,
                "answer": actual.get("answer") if actual else None,
                "evidence": actual.get("evidence") if actual else None,
                "assumptions": actual.get("assumptions") if actual else None,
                "error": error
            })

            print(
                f"[{'PASS' if passed else 'FAIL'}] "
                f"{case['id']:02d} {case['category']} "
                f"({latency:.2f}s)"
            )

    finally:
        gold_connection.close()

    total = len(case_results)
    passed_count = sum(item["passed"] for item in case_results)

    categories = {}
    for item in case_results:
        category = item["category"]
        summary = categories.setdefault(category, {"total": 0, "passed": 0})
        summary["total"] += 1
        summary["passed"] += int(item["passed"])

    for summary in categories.values():
        summary["accuracy_pct"] = round(
            summary["passed"] / summary["total"] * 100, 2
        )

    known_costs = [
        item["usage"].get("cost_usd")
        for item in case_results
        if isinstance(item["usage"].get("cost_usd"), (int, float))
    ]
    all_costs_known = all(
        isinstance(item["usage"].get("cost_usd"), (int, float))
        for item in case_results
    )

    report = {
        "summary": {
            "total_questions": total,
            "passed": passed_count,
            "failed": total - passed_count,
            "accuracy_pct": round(passed_count / total * 100, 2) if total else 0,
            "average_latency_seconds": round(
                sum(item["latency_seconds"] for item in case_results) / total, 3
            ) if total else 0,
            "total_cost_usd": round(sum(known_costs), 8) if all_costs_known else None,
            "category_accuracy": categories
        },
        "questions": case_results
    }

    RESULTS_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print("\nEvaluation summary")
    print("------------------")
    print(f"Questions: {total}")
    print(f"Passed:    {passed_count}")
    print(f"Failed:    {total - passed_count}")
    print(f"Accuracy:  {report['summary']['accuracy_pct']}%")
    print(f"Average latency: {report['summary']['average_latency_seconds']} seconds")
    print(f"Total API cost: {report['summary']['total_cost_usd']}")
    print(f"\nCategory results and per-question details saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    run_evaluation()
