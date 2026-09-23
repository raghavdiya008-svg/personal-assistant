"""
Tests for Compliant Telephony Engine in Project JARVIS v2.
"""

import pytest
from core.telephony import CompliantTelephonyEngine
from core.consent import consent_engine


@pytest.fixture
def telephony():
    return CompliantTelephonyEngine()


@pytest.mark.asyncio
async def test_call_blocked_without_consent(telephony):
    # Outbound call without prior affirmative consent MUST raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        await telephony.initiate_call(
            phone_number="+15551234567",
            purpose="Product Demo",
            script_prompt="Hello, this is JARVIS.",
            jurisdiction="US-CA",
        )
    assert "Telephony blocked" in str(exc_info.value) or "Regulatory violation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_call_succeeds_with_affirmative_consent(telephony):
    # Record affirmative consent first
    consent_engine.record_consent(
        subject="+15559876543",
        channel="VOICE_CALL",
        jurisdiction="GLOBAL",
        proof_source="inbound_booking_form",
    )

    result = await telephony.initiate_call(
        phone_number="+15559876543",
        purpose="Scheduled Consultation",
        script_prompt="Hello, confirming our meeting.",
        jurisdiction="GLOBAL",
    )

    assert result.content["status"] == "CONNECTED"
    assert "call_id" in result.content

    # End call
    end_res = await telephony.end_call(result.content["call_id"])
    assert end_res.content["status"] == "COMPLETED"
