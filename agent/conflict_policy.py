
"""Resolve conflicting policies using dates and source authority."""

from datetime import date


def resolve_conflict(documents, as_of_date):
    try:
        requested_date = date.fromisoformat(as_of_date)
    except (ValueError, TypeError):
        return {
            "status": "cannot_determine",
            "selected": None,
            "conflicts": [],
            "outdated": [],
            "reason": "Invalid requested date",
        }

    applicable = []
    outdated = []
    unknown = []

    for doc in documents:
        start = doc.get("effective_from")
        end = doc.get("effective_to")
        authority = doc.get("authority")
        revision = doc.get("revision_date")

        try:
            if not start or authority is None:
                raise ValueError("Missing effective date or authority")

            start_date = date.fromisoformat(start)
            end_date = (
                None if end in (None, "", "open")
                else date.fromisoformat(end)
            )
            revision_date = (
                date.fromisoformat(revision) if revision
                else date.min
            )

            if end_date and end_date < start_date:
                raise ValueError("Invalid effective date range")

        except (ValueError, TypeError):
            unknown.append(doc)
            continue

        if start_date > requested_date:
            continue

        if end_date and requested_date > end_date:
            outdated.append(doc)
            continue

        applicable.append({
            **doc,
            "_authority": authority,
            "_start_date": start_date,
            "_revision_date": revision_date,
        })

    if unknown:
        return {
            "status": "cannot_determine",
            "selected": None,
            "conflicts": [],
            "outdated": outdated,
            "unknown_validity": unknown,
            "reason": "Some policy records have missing or invalid metadata",
        }

    if not applicable:
        return {
            "status": "cannot_determine",
            "selected": None,
            "conflicts": [],
            "outdated": outdated,
            "unknown_validity": [],
            "reason": "No applicable policy found",
        }

    # Higher authority wins; then latest effective date;
    # then latest revision date.
    best_rank = max(
        (
            doc["_authority"],
            doc["_start_date"],
            doc["_revision_date"],
        )
        for doc in applicable
    )

    candidates = [
        doc for doc in applicable
        if (
            doc["_authority"],
            doc["_start_date"],
            doc["_revision_date"],
        ) == best_rank
    ]

    # Remove internal ranking fields from returned documents.
    candidates = [
        {k: v for k, v in doc.items() if not k.startswith("_")}
        for doc in candidates
    ]

    if len(candidates) != 1:
        return {
            "status": "conflict",
            "selected": None,
            "conflicts": candidates,
            "outdated": outdated,
            "unknown_validity": [],
            "reason": "Multiple equally ranked policies apply",
        }

    return {
        "status": "resolved",
        "selected": candidates[0],
        "conflicts": [],
        "outdated": outdated,
        "unknown_validity": [],
        "reason": "Policy selected by authority, effective date, and revision date",
    }
