from gateway.app import normalize
from gateway.pii import redact, redact_messages


def test_redact_types():
    t, n = redact("mail jane.doe@acme.com, iban FR76 3000 6000 0112 3456 7890 189, card 4111 1111 1111 1111")
    assert n == 3 and "@" not in t and "[EMAIL]" in t and "[IBAN]" in t and "[CARD]" in t


def test_redact_messages_parts_and_clean_text():
    msgs = [{"role": "user", "content": [{"type": "text", "text": "call +33 6 12 34 56 78"}]},
            {"role": "user", "content": "no pii here"}]
    assert redact_messages(msgs) == 1
    assert msgs[1]["content"] == "no pii here"


def test_budget_exceeded_is_clean_429():
    s, b = normalize(400, {"error": {"type": "budget_exceeded", "message": "Budget has been exceeded!"}})
    assert s == 429 and b["error"]["type"] == "budget_exceeded"


def test_other_errors_pass_through():
    assert normalize(500, {"error": {"message": "boom"}}) == (500, {"error": {"message": "boom"}})
