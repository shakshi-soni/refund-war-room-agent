
import hashlib
import json
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bazaar.db"


def _hash_rows(rows):
    payload = json.dumps(
        rows,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _authorize_read_only(action, arg1, arg2, database, trigger):
    """SQLite authorizer: permit reads and deny database modifications."""
    denied_actions = {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_INDEX,
        sqlite3.SQLITE_DROP_TEMP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_TRIGGER,
        sqlite3.SQLITE_DROP_TEMP_VIEW,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_SAVEPOINT,
        sqlite3.SQLITE_PRAGMA,
        sqlite3.SQLITE_REINDEX,
        sqlite3.SQLITE_ANALYZE,
    }

    if action in denied_actions:
        return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


def run_sql(sql):
    """Execute one read-only SELECT statement and return hashed rows."""
    if not isinstance(sql, str) or not sql.strip():
        return {"ok": False, "error": "SQL query must be a non-empty string."}

    cleaned = sql.strip()

    # Require a SELECT statement. Scalar subqueries are permitted.
    # WITH statements are intentionally not accepted by this simple interface.
    if not re.match(r"(?is)^SELECT\b", cleaned):
        return {
            "ok": False,
            "error": "Read-only queries only: query must start with SELECT.",
        }

    try:
        # mode=ro prevents writes even if another safeguard fails.
        db_uri = DB_PATH.resolve().as_uri() + "?mode=ro"

        with sqlite3.connect(db_uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.set_authorizer(_authorize_read_only)

            # sqlite3.execute rejects multiple SQL statements.
            cursor = connection.execute(cleaned)
            rows = [dict(row) for row in cursor.fetchall()]

        return {
            "ok": True,
            "sql": cleaned,
            "rows": rows,
            "result_hash": _hash_rows(rows),
        }

    except sqlite3.Error as exc:
        return {
            "ok": False,
            "sql": cleaned,
            "error": str(exc),
        }
