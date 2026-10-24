
import hashlib
import json

from agent.verifier import verify_claim, verify_response


def make_sql_result(rows, sql="SELECT COUNT(*) AS total_orders FROM orders"):
    """Build a test SQL result with the same hashing scheme as the tool."""
    payload = json.dumps(
        rows,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    result_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return {
        "ok": True,
        "sql": sql,
        "rows": rows,
        "result_hash": result_hash,
    }


def test_rejects_fact_without_evidence():
    claim = {
        "claim": "There are 31 orders.",
        "type": "fact",
        "evidence": [],
        "superseded_policy": False,
    }

    result = verify_claim(claim, [])

    assert result["valid"] is False
    assert any("requires evidence" in error for error in result["errors"])


def test_rejects_wrong_number_32_when_sql_says_31():
    sql_result = make_sql_result([{"total_orders": 31}])

    claim = {
        "claim": "There are 32 orders.",
        "type": "fact",
        "evidence": [{
            "sql": sql_result["sql"],
            "result_hash": sql_result["result_hash"],
        }],
        "superseded_policy": False,
    }

    result = verify_claim(claim, [sql_result])

    assert result["valid"] is False
    assert any(
        "numeric" in error.lower()
        for error in result["errors"]
    )


def test_accepts_matching_number_31():
    sql_result = make_sql_result([{"total_orders": 31}])

    claim = {
        "claim": "There are 31 orders.",
        "type": "fact",
        "evidence": [{
            "sql": sql_result["sql"],
            "result_hash": sql_result["result_hash"],
        }],
        "superseded_policy": False,
    }

    result = verify_claim(claim, [sql_result])

    assert result["valid"] is True
    assert result["errors"] == []


def test_rejects_modified_result_hash():
    sql_result = make_sql_result([{"total_orders": 31}])

    claim = {
        "claim": "There are 31 orders.",
        "type": "fact",
        "evidence": [{
            "sql": sql_result["sql"],
            "result_hash": "incorrect-hash",
        }],
        "superseded_policy": False,
    }

    result = verify_claim(claim, [sql_result])

    assert result["valid"] is False
    assert any("hash" in error.lower() for error in result["errors"])


def test_rejects_superseded_policy_claim():
    claim = {
        "claim": "The old policy permits 14 days.",
        "type": "fact",
        "evidence": [{
            "document_id": "policy_return_window_old",
            "quote": "Return window: 14 days.",
        }],
        "superseded_policy": True,
    }

    # This claim must be rejected because it is explicitly marked superseded.
    result = verify_claim(
        claim,
        [],
        superseded_policy=True,
    )

    assert result["valid"] is False
    assert any(
        "superseded" in error.lower()
        for error in result["errors"]
    )


def test_response_verifier_rejects_answer_without_claims():
    response = {
        "status": "answered",
        "answer": "There are 31 orders.",
        "claims": [],
        "conflicts": [],
        "missing_evidence": [],
    }

    result = verify_response(response, [])

    assert result["valid"] is False
    assert any("claim" in error.lower() for error in result["errors"])


def test_response_verifier_accepts_abstention_with_missing_evidence():
    response = {
        "status": "cannot_determine",
        "answer": "",
        "claims": [],
        "conflicts": [],
        "missing_evidence": ["A valid order count is missing."],
    }

    result = verify_response(response, [])

    assert result["valid"] is True
    assert result["errors"] == []
