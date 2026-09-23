"""
Tests for Tool Staging Pipeline and AST Security Scanner in Project JARVIS v2.
"""

import pytest
from core.staging_pipeline import ToolStagingPipeline, ToolStage
from core.approvals import approval_engine
from core.capability_broker import capability_broker


@pytest.fixture
def pipeline():
    return ToolStagingPipeline()


def test_safe_tool_lifecycle(pipeline):
    safe_code = """
def calculate_tax(amount, rate=0.2):
    return round(amount * (1.0 + rate), 2)
"""
    unit_test_code = """
assert calculate_tax(100, 0.1) == 110.0
"""
    # 1. Ingest
    artifact = pipeline.ingest("calculate_tax", "1.0.0", safe_code)
    assert artifact.stage == ToolStage.GENERATED

    # 2. Sandbox Test
    passed = pipeline.run_sandbox_tests(artifact.tool_id, unit_test_code)
    assert passed is True
    assert artifact.stage == ToolStage.SANDBOX_TESTED

    # 3. AST Security Scan
    is_safe, violations = pipeline.run_security_scan(artifact.tool_id)
    assert is_safe is True
    assert len(violations) == 0
    assert artifact.stage == ToolStage.SECURITY_SCANNED

    # 4. Stage for Human Approval
    ticket_id = pipeline.stage_for_human_approval(artifact.tool_id)
    assert artifact.stage == ToolStage.STAGED
    assert ticket_id.startswith("appr_")

    # 5. Sign and Promote
    approval_engine.approve_ticket(ticket_id, operator_id="admin_user")
    cap_def = pipeline.promote_to_production(artifact.tool_id, ticket_id)
    assert artifact.stage == ToolStage.APPROVED_PRODUCTION
    assert cap_def.name == "custom.calculate_tax"
    assert "custom.calculate_tax" in capability_broker._capabilities


def test_malicious_code_rejection_subprocess(pipeline):
    malicious_code = """
import subprocess
def run_command(cmd):
    return subprocess.check_output(cmd)
"""
    artifact = pipeline.ingest("run_command", "1.0.0", malicious_code)
    is_safe, violations = pipeline.run_security_scan(artifact.tool_id)
    
    assert is_safe is False
    assert any("Forbidden module import: 'subprocess'" in v for v in violations)


def test_malicious_code_rejection_eval(pipeline):
    malicious_code = """
def execute_dynamic(payload):
    return eval(payload)
"""
    artifact = pipeline.ingest("execute_dynamic", "1.0.0", malicious_code)
    is_safe, violations = pipeline.run_security_scan(artifact.tool_id)

    assert is_safe is False
    assert any("Dangerous builtin function call: 'eval()'" in v for v in violations)


def test_malicious_dunder_traversal_rejection(pipeline):
    malicious_code = """
def escalate():
    return ().__class__.__bases__[0].__subclasses__()
"""
    artifact = pipeline.ingest("escalate", "1.0.0", malicious_code)
    is_safe, violations = pipeline.run_security_scan(artifact.tool_id)

    assert is_safe is False
    assert any("Privilege escalation dunder access" in v for v in violations)
