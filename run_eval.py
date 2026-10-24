
"""Validate evaluation questions for Refund War Room."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVAL_PATH = ROOT / "data" / "eval_questions.json"


def run_eval():
    if not EVAL_PATH.exists():
        print(f"ERROR: Evaluation file not found: {EVAL_PATH}")
        return 1

    try:
        with EVAL_PATH.open("r", encoding="utf-8") as file:
            questions = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Could not load evaluation questions: {exc}")
        return 1

    if not isinstance(questions, list) or not questions:
        print("ERROR: Evaluation data must be a non-empty JSON list.")
        return 1

    required_fields = {
        "id",
        "category",
        "question",
        "expected_behavior",
        "expected_status",
    }

    seen_ids = set()
    passed = 0
    failed = 0

    print("\nRefund War Room — Evaluation Dataset Check")
    print("=" * 48)

    for item in questions:
        errors = []

        if not isinstance(item, dict):
            print(f"FAIL: Invalid entry: {item!r}")
            failed += 1
            continue

        missing = required_fields - item.keys()
        if missing:
            errors.append(f"missing fields: {', '.join(sorted(missing))}")

        item_id = item.get("id")

        if not isinstance(item_id, str) or not item_id.strip():
            errors.append("invalid ID")
        elif item_id in seen_ids:
            errors.append("duplicate ID")
        else:
            seen_ids.add(item_id)

        for field in ("category", "question", "expected_behavior",
                      "expected_status"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"empty or invalid {field}")

        if errors:
            failed += 1
            print(f"FAIL: {item_id or 'UNKNOWN'} — {'; '.join(errors)}")
        else:
            passed += 1
            print(f"PASS: {item_id} — {item['category']}")

    print("=" * 48)
    print(f"Total cases: {len(questions)}")
    print(f"Passed:      {passed}")
    print(f"Failed:      {failed}")

    if failed:
        print("\nDataset validation FAILED.")
        return 1

    print("\nDataset validation PASSED.")
    print("Note: Agent behavior has not been evaluated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_eval())
