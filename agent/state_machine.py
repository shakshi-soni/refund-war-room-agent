
import json
import re
from datetime import date

from agent.schema import make_response
from agent.verifier import verify_response

MAX_TOOL_CALLS = 8


def run_agent(question, tools, use_verifier=True):
    question = question.strip()
    observations = []
    tool_results = []
    calls = 0

    def call_tool(name, *args):
        nonlocal calls

        if calls >= MAX_TOOL_CALLS:
            return None

        tool = tools.get(name)
        if not callable(tool):
            return None

        calls += 1
        try:
            result = tool(*args)
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}

        observations.append({
            "tool": name,
            "ok": isinstance(result, dict) and result.get("ok") is True,
            "result": result,
        })

        if isinstance(result, dict):
            tool_results.append(result)

        return result

    def finish(status, answer="", claims=None, conflicts=None, missing=None):
        response = make_response(
            status=status,
            answer=answer,
            claims=claims or [],
            conflicts=conflicts or [],
            missing_evidence=missing or [],
            tool_calls=calls,
        )

        if use_verifier:
            response["verification"] = verify_response(response, tool_results)

            if status == "answered" and not response["verification"]["valid"]:
                response["status"] = "cannot_determine"
                response["answer"] = ""
                response["missing_evidence"] = (
                    response["verification"]["errors"]
                )

        response["observations"] = observations
        return response

    if not question:
        return finish(
            "cannot_determine",
            missing=["Please enter a question."],
        )

    q = question.casefold()

    # Handle refund rate BEFORE generic refund-question routing.
    if "refund rate" in q or "refund percentage" in q:
        sql = """
            SELECT
                (SELECT COUNT(*) FROM refunds) AS total_refunds,
                (SELECT COUNT(*) FROM orders) AS total_orders
        """
        result = call_tool("run_sql", sql)

        if not isinstance(result, dict) or not result.get("ok"):
            return finish(
                "cannot_determine",
                missing=["A successful query for refund and order counts."],
            )

        rows = result.get("rows", [])
        if not rows:
            return finish(
                "cannot_determine",
                missing=["Refund and order counts from the database."],
            )

        row = rows[0]
        refunds = row.get("total_refunds")
        orders = row.get("total_orders")

        if not isinstance(refunds, int) or not isinstance(orders, int) or orders <= 0:
            return finish(
                "cannot_determine",
                missing=["Valid refund count and positive order count."],
            )

        # State the chosen definition explicitly.
        rate = refunds / orders * 100
        claim = {
            "claim": (
                f"The recorded refund rate is {rate:.2f}%, "
                "defined as refund records divided by order records."
            ),
            "type": "fact",
            "evidence": [{
                "sql": result["sql"],
                "result_hash": result["result_hash"],
            }],
            "superseded_policy": False,
        }

        return finish(
            "answered",
            claim["claim"],
            claims=[claim],
        )

    # Policy questions: surface conflicts instead of silently selecting a version.
    if "policy" in q or "replacement" in q:
        requested_date = date.today().isoformat()
        match = re.search(r"\b(2026-\d{2}-\d{2})\b", question)
        if match:
            requested_date = match.group(1)

        result = call_tool(
            "get_policy", "Replacement Policy", requested_date
        )

        if not isinstance(result, dict) or not result.get("ok"):
            return finish(
                "cannot_determine",
                missing=["A successful policy lookup."],
            )

        docs = result.get("results", [])

        if result.get("status") == "conflict" or len(docs) > 1:
            return finish(
                "cannot_determine",
                conflicts=[{
                    "policy_name": "Replacement Policy",
                    "as_of_date": requested_date,
                    "documents": docs,
                    "reason": "Multiple or conflicting policy records require resolution.",
                }],
                missing=[
                    "An explicit, validated policy precedence rule for the conflicting records."
                ],
            )

        if result.get("status") == "found" and len(docs) == 1:
            doc = docs[0]
            text = doc.get("text", "").strip()

            claim = {
                "claim": text,
                "type": "fact",
                "evidence": [{
                    "document_id": doc["document_id"],
                    "quote": text,
                }],
                "superseded_policy": False,
            }

            return finish(
                "answered",
                text,
                claims=[claim],
            )

        return finish(
            "cannot_determine",
            missing=[
                f"No unambiguous replacement policy was found for {requested_date}."
            ],
        )

    # Database questions.
    if any(word in q for word in (
        "refund", "pincode", "tier", "orders", "count",
        "reason", "how many",
    )):
        if "reason" in q and "tier" not in q and "pincode" not in q:
            sql = """
                SELECT r.refund_reason, COUNT(*) AS refund_count
                FROM refunds r
                GROUP BY r.refund_reason
                ORDER BY refund_count DESC, r.refund_reason
            """
        else:
            sql = """
                SELECT o.pincode_tier, r.refund_reason,
                       COUNT(*) AS refund_count
                FROM refunds r
                JOIN orders o ON o.order_id = r.order_id
                GROUP BY o.pincode_tier, r.refund_reason
                ORDER BY o.pincode_tier, refund_count DESC
            """

        result = call_tool("run_sql", sql)

        if isinstance(result, dict) and result.get("ok"):
            rows = result.get("rows", [])
            if rows:
                lines = []
                for row in rows:
                    if "pincode_tier" in row:
                        lines.append(
                            f"{row['pincode_tier']} — "
                            f"{row['refund_reason']}: "
                            f"{row['refund_count']} refunds"
                        )
                    else:
                        lines.append(
                            f"{row['refund_reason']}: "
                            f"{row['refund_count']} refunds"
                        )

                claim = {
                    "claim": "Refund counts returned by the database query.",
                    "type": "fact",
                    "evidence": [{
                        "sql": result["sql"],
                        "result_hash": result["result_hash"],
                    }],
                    "superseded_policy": False,
                }

                return finish(
                    "answered",
                    "\n".join(lines),
                    claims=[claim],
                )

        return finish(
            "cannot_determine",
            missing=["A successful SQL result containing the requested counts."],
        )

    # General document retrieval.
    result = call_tool("search_docs", question)

    if isinstance(result, dict) and result.get("ok"):
        docs = result.get("results", [])
        if docs:
            doc = docs[0]
            text = doc.get("text", "").strip()

            if text:
                return finish(
                    "partial",
                    f"Relevant document: {text}",
                    missing=[
                        "A verified answer directly addressing the question."
                    ],
                )

    return finish(
        "cannot_determine",
        missing=["Sufficient evidence from the available tools."],
    )


if __name__ == "__main__":
    from tools.doc_tools import search_docs, get_policy
    from tools.sql_tool import run_sql

    tools = {
        "search_docs": search_docs,
        "get_policy": get_policy,
        "run_sql": run_sql,
    }

    while True:
        question = input("\nAsk Refund War Room (or type exit): ").strip()

        if question.casefold() == "exit":
            break

        response = run_agent(question, tools)
        print(json.dumps(response, indent=2, ensure_ascii=False, default=str))
