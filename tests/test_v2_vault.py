"""
Tests for Zero-Trust Secrets Vault in Project JARVIS v2.
"""

import pytest
from core.vault import ZeroTrustVault


@pytest.fixture
def vault():
    v = ZeroTrustVault(master_key="test_master_key_12345")
    v.store_secret("EMAIL_API_KEY", "secret_smtp_token_xyz")
    v.store_secret("VAPI_API_KEY", "secret_vapi_token_abc")
    return v


def test_authorized_secret_injection(vault):
    # 'outbound.email' is permitted to access 'EMAIL_API_KEY'
    key = vault.inject_for_capability("outbound.email", "EMAIL_API_KEY")
    assert key == "secret_smtp_token_xyz"


def test_unauthorized_secret_injection_blocked(vault):
    # 'second_brain.index' is NOT permitted to access 'EMAIL_API_KEY'
    with pytest.raises(PermissionError) as exc_info:
        vault.inject_for_capability("second_brain.index", "EMAIL_API_KEY")
    assert "not authorized to access secret" in str(exc_info.value)


def test_secret_masking(vault):
    raw_text = "Sending payload with secret_smtp_token_xyz to server"
    masked = vault.mask_secret(raw_text)
    assert "secret_smtp_token_xyz" not in masked
    assert "[VAULT_REDACTED_EMAIL_API_KEY]" in masked
