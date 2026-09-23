"""
Tests for Capability Broker and Policy Engine in Project JARVIS v2.
"""

import pytest
from pathlib import Path
from core.capability_broker import CapabilityBroker, CapabilityDefinition, RiskLevel, ApprovalRequiredError
from core.approvals import approval_engine
from core.trust import TrustLevel
from core.config import settings


@pytest.fixture
def broker():
    return CapabilityBroker()


@pytest.mark.asyncio
async def test_sandboxed_fs_read_success(broker, tmp_path):
    # Create test file inside settings.DATA_DIR
    test_file = settings.DATA_DIR / "test_read.txt"
    test_file.write_text("Hello Sovereign Jarvis v2", encoding="utf-8")

    result = await broker.invoke(
        agent_id="research_agent",
        capability_name="filesystem.read",
        parameters={"path": str(test_file)},
    )
    assert result.content == "Hello Sovereign Jarvis v2"
    assert result.trust_level == TrustLevel.TRUSTED_SYSTEM_POLICY


@pytest.mark.asyncio
async def test_fs_read_sandbox_violation(broker):
    # Path traversal outside DATA_DIR must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        await broker.invoke(
            agent_id="research_agent",
            capability_name="filesystem.read",
            parameters={"path": "C:\\Windows\\System32\\drivers\\etc\\hosts"},
        )
    assert "blocked outside sandbox" in str(exc_info.value)


@pytest.mark.asyncio
async def test_agent_acl_enforcement(broker):
    # Agent 'guest_user' is not authorized for 'shell.execute'
    with pytest.raises(PermissionError) as exc_info:
        await broker.invoke(
            agent_id="guest_user",
            capability_name="shell.execute",
            parameters={"command": "dir"},
        )
    assert "not authorized" in str(exc_info.value)


@pytest.mark.asyncio
async def test_high_risk_approval_flow(broker):
    params = {
        "recipient": "partner@corp.com",
        "subject": "Proposal",
        "body": "Here is the proposal details.",
    }

    # 1. First invocation without approval ticket MUST raise ApprovalRequiredError
    ticket_id = None
    with pytest.raises(ApprovalRequiredError) as exc_info:
        await broker.invoke(
            agent_id="outreach_agent",
            capability_name="outbound.email",
            parameters=params,
        )
    ticket_id = exc_info.value.ticket_id
    assert ticket_id.startswith("appr_")

    # 2. Operator signs and approves the ticket
    approval_engine.approve_ticket(ticket_id, operator_id="admin_user")

    # 3. Re-invoke with the valid approval ticket MUST succeed
    result = await broker.invoke(
        agent_id="outreach_agent",
        capability_name="outbound.email",
        parameters=params,
        approval_ticket_id=ticket_id,
    )
    assert result.content["status"] == "SENT"
