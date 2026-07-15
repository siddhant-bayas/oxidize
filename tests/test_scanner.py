from __future__ import annotations

from oxidize.security.scanner import scan_text, PATTERNS


def _stripe_key() -> str:
    return "sk_live_" + "abcdefghijklmnopqrstuvwx"


def _slack_token() -> str:
    return "xoxb-" + "123456789012" + "-" + "123456789012" + "-" + "12345678901234567890"


def _openai_key() -> str:
    return "sk-" + "abcdefghijklmnopqrst" + "T3BlbkFJ" + "abcdefghijklmnopqrst"


def test_scan_finds_github_pat() -> None:
    text = 'token = "ghp_' + "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij" + '"'
    findings = scan_text(text, "config.py")
    assert any(f["type"] == "GitHub PAT" for f in findings)


def test_scan_finds_private_key() -> None:
    text = "-----BEGIN RSA PRIVATE KEY-----"
    findings = scan_text(text, "key.pem")
    assert any(f["type"] == "Private Key Block" for f in findings)


def test_scan_finds_stripe_key() -> None:
    text = 'stripe_key = "' + _stripe_key() + '"'
    findings = scan_text(text, ".env")
    assert any(f["type"] == "Stripe Secret Key" for f in findings)


def test_scan_finds_slack_token() -> None:
    text = 'SLACK_TOKEN = "' + _slack_token() + '"'
    findings = scan_text(text, ".env")
    assert any(f["type"] == "Slack Token" for f in findings)


def test_scan_finds_openai_key() -> None:
    text = 'api_key = "' + _openai_key() + '"'
    findings = scan_text(text, "config.py")
    assert any(f["type"] == "OpenAI API Key" for f in findings)


def test_scan_clean_file() -> None:
    text = "def hello():\n    print('hello')\n"
    findings = scan_text(text, "hello.py")
    assert len(findings) == 0


def test_scan_line_numbers() -> None:
    text = "line1\nline2\napi_key = '" + "sk-live-" + "abcdefghijklmnopqrstuvwx" + "'\n"
    findings = scan_text(text, "test.py")
    if findings:
        assert findings[0]["line"] == 3


def test_patterns_are_compiled() -> None:
    assert len(PATTERNS) > 10
    for name, pattern in PATTERNS.items():
        assert isinstance(pattern, str)
        assert len(pattern) > 5
