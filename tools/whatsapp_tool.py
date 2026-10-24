
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = ROOT / "logs" / "whatsapp_log.txt"


def send_seller_whatsapp(seller_id, message):
    if not isinstance(seller_id, (str, int)) or isinstance(seller_id, bool):
        return {"ok": False, "error": "Invalid seller ID"}

    seller_id = str(seller_id).strip()

    if not seller_id.isdigit():
        return {"ok": False, "error": "Invalid seller ID"}

    if not isinstance(message, str) or not message.strip():
        return {"ok": False, "error": "Invalid message"}

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seller_id": seller_id,
        "message": message.strip(),
        "status": "simulated"
    }

    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"ok": True, "status": "simulated", "seller_id": seller_id}
