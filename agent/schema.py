
"""Shared response schema for Refund War Room."""

from typing import Any, Literal, TypedDict


class Evidence(TypedDict, total=False):
    document_id: str
    quote: str
    sql: str
    result_hash: str
    rows: list[dict[str, Any]]


class Claim(TypedDict):
    claim: str
    type: Literal["fact", "assumption", "recommendation"]
    evidence: list[Evidence]
    superseded_policy: bool


class AgentResponse(TypedDict):
    status: Literal["answered", "partial", "cannot_determine"]
    answer: str
    claims: list[Claim]
    conflicts: list[dict[str, Any]]
    missing_evidence: list[str]
    tool_calls: int


def make_response(
    status="cannot_determine",
    answer="",
    claims=None,
    conflicts=None,
    missing_evidence=None,
    tool_calls=0,
):
    if status not in {"answered", "partial", "cannot_determine"}:
        raise ValueError("Invalid response status")

    return {
        "status": status,
        "answer": answer,
        "claims": claims or [],
        "conflicts": conflicts or [],
        "missing_evidence": missing_evidence or [],
        "tool_calls": tool_calls,
    }
