"""
Tests for Cryptographic HITL Approval Engine in Project JARVIS v2.
"""

import time
import pytest
from core.approvals import CryptographicApprovalEngine, SecurityError


@pytest.fixture
def engine():
    return CryptographicApprovalEngine(secret_key="test_secret_key_12345")


def test_ticket_creation_and_hash(engine):
    params = {"recipient": "client@example.com", "amount": 250.0}
    ticket = engine.create_ticket("outbound.email", params, requested_by="agent_alpha")
    
    assert ticket.ticket_id.startswith("appr_")
    assert ticket.status == "PENDING"
    assert len(ticket.params_hash) == 64  # SHA-256 hex string


def test_ticket_approval_and_verification(engine):
    params = {"recipient": "client@example.com", "subject": "Quarterly Report"}
    ticket = engine.create_ticket("outbound.email", params)

    # Sign ticket
    engine.approve_ticket(ticket.ticket_id, operator_id="admin_user")
    assert ticket.status == "APPROVED"
    assert ticket.signature is not None

    # Verify and consume with identical parameters
    consumed = engine.verify_and_consume(ticket.ticket_id, "outbound.email", params)
    assert consumed is True
    assert ticket.status == "EXECUTED"


def test_tamper_detection(engine):
    approved_params = {"recipient": "client@example.com", "body": "Original text"}
    ticket = engine.create_ticket("outbound.email", approved_params)
    engine.approve_ticket(ticket.ticket_id, operator_id="admin_user")

    # Attempt to execute with modified parameters (e.g. modified recipient or body)
    tampered_params = {"recipient": "attacker@evil.com", "body": "Original text"}
    
    with pytest.raises(SecurityError) as exc_info:
        engine.verify_and_consume(ticket.ticket_id, "outbound.email", tampered_params)
    assert "Parameter tampering detected" in str(exc_info.value)


def test_replay_attack_prevention(engine):
    params = {"command": "deploy_staging"}
    ticket = engine.create_ticket("system.deploy", params)
    engine.approve_ticket(ticket.ticket_id, operator_id="admin_user")

    # First consumption succeeds
    engine.verify_and_consume(ticket.ticket_id, "system.deploy", params)
    assert ticket.status == "EXECUTED"

    # Second consumption MUST fail
    with pytest.raises(SecurityError) as exc_info:
        engine.verify_and_consume(ticket.ticket_id, "system.deploy", params)
    assert "is not APPROVED" in str(exc_info.value) or "Replay attack" in str(exc_info.value)


def test_expired_ticket_rejection(engine):
    params = {"action_item": "critical_update"}
    # Create ticket with 1-second TTL
    ticket = engine.create_ticket("system.update", params, ttl_seconds=1)
    time.sleep(1.2)  # Wait for expiry

    with pytest.raises(ValueError) as exc_info:
        engine.approve_ticket(ticket.ticket_id)
    assert "has expired" in str(exc_info.value)
