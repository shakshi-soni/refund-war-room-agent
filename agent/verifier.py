
import hashlib
import json
import re
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "docs"


def _hash_rows(rows):
    """Calculate the same deterministic hash as the SQL tool."""
    payload = json.dumps(
        rows,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def numeric_values(value):
    """Extract numbers from text and nested SQL result structures."""
    if value is None or isinstance(value, bool):
        return set()

    if isinstance(value, (int, float)):
        return {str(value)}

    if isinstance(value, dict):
        numbers = set()
        for item in value.values():
            numbers.update(numeric_values(item))
        return numbers

    if isinstance(value, (list, tuple)):
        numbers = set()
        for item in value:
            numbers.update(numeric_values(item))
        return numbers

    if isinstance(value, str):
        return set(
            re.findall(r"(?<![\w.])-?\d+(?:\.\d+)?", value)
        )

    return set()


def _verify_refund_rate(claim_text, rows):
    """Verify a refund rate by recomputing it from cited SQL counts."""
    errors = []

    if len(rows) != 1:
        return ["Refund-rate evidence must contain exactly one result row."]

    row = rows[0]

    if "total_refunds" not in row or "total_orders" not in row:
        return [
            "Refund-rate evidence must include total_refunds and total_orders."
        ]

    refunds = row["total_refunds"]
    orders = row["total_orders"]

    if (
        isinstance(refunds, bool)
        or not isinstance(refunds, (int, float))
        or isinstance(orders, bool)
        or not isinstance(orders, (int, float))
        or refunds < 0
        or orders <= 0
    ):
        return ["Refund-rate evidence contains invalid counts."]

    expected_rate = round(refunds / orders * 100, 2)
    matches = re.findall(
        r"(?<![\w.])(\d+(?:\.\d+)?)\s*%",
        claim_text,
    )

    if not matches:
        errors.append("Refund-rate claim does not state a percentage.")
    elif not any(
        abs(float(value) - expected_rate) < 0.005
        for value in matches
    ):
        errors.append(
            f"Refund rate mismatch: expected {expected_rate:.2f}% "
            "from the cited SQL counts."
        )

    return errors


def verify_claim(claim, tool_results, superseded_policy=False):
    """Check a claim's type, evidence, source integrity, and basic numbers."""
    errors = []

    if not isinstance(claim, dict):
        return {
            "valid": False,
            "errors": ["Claim must be a dictionary."],
            "claim": "",
        }

    claim_text = claim.get("claim", "")
    claim_type = claim.get("type")
    evidence_items = claim.get("evidence", [])

    if not isinstance(claim_text, str) or not claim_text.strip():
        errors.append("Claim text is missing.")

    if claim_type not in {"fact", "assumption", "recommendation"}:
        errors.append(
            "Claim type must be fact, assumption, or recommendation."
        )

    if not isinstance(evidence_items, list):
        errors.append("Claim evidence must be a list.")
        evidence_items = []

    if claim_type == "fact" and not evidence_items:
        errors.append("A factual claim requires evidence.")

    if superseded_policy or claim.get("superseded_policy", False):
        errors.append("Claim relies on a superseded policy.")

    for index, evidence in enumerate(evidence_items):
        if not isinstance(evidence, dict):
            errors.append(f"Evidence item {index} must be a dictionary.")
            continue

        document_id = evidence.get("document_id")
        quote = evidence.get("quote")
        sql = evidence.get("sql")
        result_hash = evidence.get("result_hash")

        # Verify document-backed evidence.
        if document_id is not None:
            if (
                not isinstance(document_id, str)
                or not document_id.strip()
                or Path(document_id).name != document_id
            ):
                errors.append(
                    f"Evidence item {index} has an invalid document ID."
                )
                continue

            path = DOCS_DIR / f"{document_id}.txt"

            if not path.is_file():
                errors.append(
                    f"Evidence document '{document_id}' does not exist."
                )
                continue

            try:
                document_text = path.read_text(encoding="utf-8")
            except OSError:
                errors.append(
                    f"Evidence document '{document_id}' could not be read."
                )
                continue

            if not isinstance(quote, str) or not quote.strip():
                errors.append(
                    f"Evidence document '{document_id}' has no quoted text."
                )
                continue

            if quote not in document_text:
                errors.append(
                    f"Quoted text was not found in '{document_id}'."
                )
                continue

            # For a direct factual statement, reject numbers not supported
            # by the quoted span. Derived claims need a separate rule.
            if claim_type == "fact":
                claim_numbers = numeric_values(claim_text)
                quote_numbers = numeric_values(quote)
                unsupported = claim_numbers - quote_numbers

                if unsupported:
                    errors.append(
                        "Claim contains numeric values absent from its "
                        f"document quote: {sorted(unsupported)}"
                    )

        # Verify SQL-backed evidence.
        elif sql is not None:
            if not isinstance(sql, str) or not sql.strip():
                errors.append(f"Evidence item {index} has invalid SQL.")
                continue

            matching = [
                result
                for result in tool_results
                if isinstance(result, dict)
                and result.get("ok") is True
                and result.get("sql") == sql
            ]

            if not matching:
                errors.append(
                    f"No successful tool result matches SQL: {sql}"
                )
                continue

            result = matching[-1]
            rows = result.get("rows", [])

            if not isinstance(rows, list):
                errors.append("SQL result rows must be a list.")
                continue

            recorded_hash = result.get("result_hash")

            if not isinstance(result_hash, str) or not result_hash:
                errors.append("SQL evidence is missing its result hash.")
                continue

            if result_hash != recorded_hash:
                errors.append(
                    "Evidence hash does not match the SQL result."
                )
                continue

            calculated_hash = _hash_rows(rows)

            if calculated_hash != recorded_hash:
                errors.append(
                    "SQL result rows do not match the recorded result hash."
                )
                continue

            if claim_type == "fact":
                if "refund rate" in claim_text.casefold():
                    errors.extend(_verify_refund_rate(claim_text, rows))
                else:
                    claim_numbers = numeric_values(claim_text)
                    result_numbers = numeric_values(rows)
                    unsupported = claim_numbers - result_numbers

                    if unsupported:
                        errors.append(
                            "Claim contains numeric values absent from "
                            f"the cited SQL rows: {sorted(unsupported)}"
                        )

        else:
            errors.append(
                f"Evidence item {index} must reference a document or SQL result."
            )

    return {
        "valid": not errors,
        "errors": errors,
        "claim": claim_text,
    }


def verify_response(response, tool_results):
    """Verify every claim in a structured agent response."""
    if not isinstance(response, dict):
        return {
            "valid": False,
            "errors": ["Response must be a dictionary."],
            "verified_claims": [],
        }

    errors = []
    verified_claims = []
    claims = response.get("claims", [])

    if not isinstance(claims, list):
        return {
            "valid": False,
            "errors": ["Response claims must be a list."],
            "verified_claims": [],
        }

    for claim in claims:
        result = verify_claim(claim, tool_results)
        verified_claims.append(result)

        if not result["valid"]:
            errors.extend(result["errors"])

    if response.get("status") == "answered" and not claims:
        errors.append(
            "An answered response must contain at least one claim."
        )

    if response.get("status") == "cannot_determine":
        if not response.get("missing_evidence"):
            errors.append(
                "A cannot_determine response must explain what evidence is missing."
            )

    return {
        "valid": not errors,
        "errors": errors,
        "verified_claims": verified_claims,
    }
