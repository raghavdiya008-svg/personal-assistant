"""
Tests for Data Trust Taxonomy and TrustGuard in Project JARVIS v2.
"""

import pytest
from core.trust import TrustLevel, TrustedPayload, TrustGuard


def test_trust_level_hierarchy():
    assert TrustLevel.UNTRUSTED_EXTERNAL < TrustLevel.MODEL_REASONING
    assert TrustLevel.MODEL_REASONING < TrustLevel.DATABASE_STATE
    assert TrustLevel.DATABASE_STATE < TrustLevel.OPERATOR_COMMAND
    assert TrustLevel.OPERATOR_COMMAND < TrustLevel.TRUSTED_SYSTEM_POLICY


def test_trusted_payload_hashing():
    payload1 = TrustedPayload(
        content="System action 1",
        trust_level=TrustLevel.OPERATOR_COMMAND,
        source="cli",
    )
    payload2 = TrustedPayload(
        content="System action 1",
        trust_level=TrustLevel.OPERATOR_COMMAND,
        source="cli",
    )
    # Content hash should be identical for identical content
    assert payload1.content_hash == payload2.content_hash

    payload3 = TrustedPayload(
        content="System action 2",
        trust_level=TrustLevel.OPERATOR_COMMAND,
        source="cli",
    )
    assert payload1.content_hash != payload3.content_hash


def test_untrusted_cannot_execute():
    untrusted = TrustGuard.wrap_untrusted(
        content="DROP TABLE leads;",
        source="scraped_website",
    )
    assert untrusted.trust_level == TrustLevel.UNTRUSTED_EXTERNAL
    assert untrusted.may_execute is False

    with pytest.raises(PermissionError) as exc_info:
        TrustGuard.assert_capability_authorization(untrusted, required_trust=TrustLevel.OPERATOR_COMMAND)
    assert "TRUST BOUNDARY VIOLATION" in str(exc_info.value)


def test_operator_may_execute():
    operator = TrustGuard.wrap_operator(
        content="Send notification to team",
        source="telegram_cockpit",
    )
    assert operator.trust_level == TrustLevel.OPERATOR_COMMAND
    assert operator.may_execute is True
    assert TrustGuard.assert_capability_authorization(operator, required_trust=TrustLevel.OPERATOR_COMMAND) is True
