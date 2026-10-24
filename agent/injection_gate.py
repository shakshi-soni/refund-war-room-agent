
"""Block unauthorized WhatsApp actions."""

import re

ALLOWED_ACTIONS = {"send_seller_whatsapp"}


def authorize_action(action, user_message, seller_id, message):
    if action not in ALLOWED_ACTIONS:
        return False, "Action is not allowed"

    if not isinstance(user_message, str) or not user_message.strip():
        return False, "Explicit user intent is required"

    if not re.search(
        r"\b(send|message|notify|contact|whatsapp)\b",
        user_message,
        re.IGNORECASE,
    ):
        return False, "User did not request a message"

    if not str(seller_id).isdigit():
        return False, "Invalid seller ID"

    if not isinstance(message, str) or not message.strip():
        return False, "Message cannot be empty"

    # Never authorize an action solely because a document requests it.
    if re.search(
        r"ignore previous instructions|system se request|"
        r"send.{0,30}credit|₹\s*[\d,]+",
        user_message,
        re.IGNORECASE,
    ):
        return False, "Suspicious action request requires review"

    return True, "Authorized"
