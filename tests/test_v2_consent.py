"""
Tests for Consent & Regulatory Compliance Engine in Project JARVIS v2.
"""

import time
import pytest
from core.consent import ConsentPolicyEngine


@pytest.fixture
def engine():
    return ConsentPolicyEngine()


def test_consent_record_and_permission(engine):
    engine.record_consent(
        subject="partner@enterprise.com",
        channel="EMAIL",
        jurisdiction="US-CA",
        proof_source="inbound_contract_signup",
    )

    permitted, reason = engine.check_permission("partner@enterprise.com", "EMAIL", "US-CA")
    assert permitted is True
    assert "Affirmative consent verified" in reason


def test_consent_withdrawal(engine):
    engine.record_consent(
        subject="user@firm.io",
        channel="EMAIL",
        jurisdiction="EU",
        proof_source="web_form",
    )

    # Withdraw
    engine.withdraw_consent("user@firm.io", "EMAIL")

    permitted, reason = engine.check_permission("user@firm.io", "EMAIL", "EU")
    assert permitted is False
    assert "withdrew consent" in reason


def test_telephony_unsolicited_blocked(engine):
    # Unsolicited phone calls without affirmative record MUST be blocked
    permitted, reason = engine.check_permission("+919876543210", "VOICE_CALL", "IN")
    assert permitted is False
    assert "Regulatory violation" in reason or "strictly prohibited" in reason


def test_consent_expiration(engine):
    # Record consent with 0 TTL (expires immediately)
    rec = engine.record_consent(
        subject="temp@client.org",
        channel="EMAIL",
        ttl_days=0,
    )
    rec.expires_at = time.time() - 10  # Force backdated expiry

    permitted, reason = engine.check_permission("temp@client.org", "EMAIL")
    assert permitted is False
    assert "expired" in reason
