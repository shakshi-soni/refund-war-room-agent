
from agent.injection_gate import authorize_action


def test_allows_explicit_whatsapp_request():
    allowed, reason = authorize_action(
        action="send_seller_whatsapp",
        user_message="Please send a WhatsApp message to seller 123.",
        seller_id="123",
        message="Please confirm the refund status.",
    )

    assert allowed is True


def test_blocks_unapproved_action():
    allowed, reason = authorize_action(
        action="delete_database",
        user_message="Please do this.",
        seller_id="123",
        message="Hello",
    )

    assert allowed is False


def test_blocks_request_without_explicit_intent():
    allowed, reason = authorize_action(
        action="send_seller_whatsapp",
        user_message="Check the refund status.",
        seller_id="123",
        message="Hello",
    )

    assert allowed is False


def test_blocks_invalid_seller_id():
    allowed, reason = authorize_action(
        action="send_seller_whatsapp",
        user_message="Please send a WhatsApp message.",
        seller_id="seller-abc",
        message="Hello",
    )

    assert allowed is False


def test_blocks_empty_message():
    allowed, reason = authorize_action(
        action="send_seller_whatsapp",
        user_message="Please send a WhatsApp message.",
        seller_id="123",
        message="   ",
    )

    assert allowed is False
