
from pathlib import Path
from datetime import date
import re

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "docs"


def search_docs(query, limit=5):
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "results": []}

    terms = set(query.lower().split())
    results = []

    for path in sorted(DOCS_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")
        matches = terms & set(text.lower().split())

        if matches:
            results.append({
                "document_id": path.stem,
                "text": text,
                "score": len(matches) / len(terms)
            })

    results.sort(key=lambda x: (-x["score"], x["document_id"]))
    return {"ok": True, "results": results[:limit]}


def get_policy(name, as_of_date):
    try:
        requested = date.fromisoformat(as_of_date)
    except (ValueError, TypeError):
        return {"ok": False, "status": "invalid_date", "results": []}

    results = []

    for path in sorted(DOCS_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8")

        def field(key):
            match = re.search(
                rf"(?im)^{key}:\s*(.+?)\s*$", text
            )
            return match.group(1).strip() if match else None

        policy = field("Policy-Name")
        start, end = field("Effective-From"), field("Effective-To")

        if not policy or policy.casefold() != name.casefold():
            continue

        try:
            start_date = date.fromisoformat(start)
            end_date = None if end == "open" else date.fromisoformat(end)
        except (ValueError, TypeError):
            results.append({
                "document_id": path.stem,
                "text": text,
                "status": "unknown_validity"
            })
            continue

        if end_date and end_date < start_date:
            results.append({
                "document_id": path.stem,
                "text": text,
                "status": "unknown_validity"
            })
        elif start_date <= requested and (
            end_date is None or requested <= end_date
        ):
            results.append({
                "document_id": path.stem,
                "text": text,
                "status": "applicable",
                "effective_from": start,
                "effective_to": end
            })

    unknown = any(r["status"] == "unknown_validity" for r in results)
    status = (
        "conflict" if unknown or len(results) > 1
        else "found" if results
        else "not_found"
    )

    return {
        "ok": True,
        "status": status,
        "policy_name": name,
        "as_of_date": as_of_date,
        "results": results
    }
