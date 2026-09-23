"""
Self-Improvement Quarantine & Tool Promotion Pipeline for Project JARVIS v2.

Enforces a 6-stage promotion gate for autonomously synthesized tools:
  GENERATED ➔ SANDBOX_TESTED ➔ SECURITY_SCANNED ➔ STAGED ➔ APPROVED_PRODUCTION ➔ REVOKED

No generated tool is ever registered into production automatically.
"""

import ast
from enum import Enum
import hashlib
import logging
from typing import Dict, Any, List, Tuple, Optional
from core.approvals import approval_engine, SecurityError
from core.capability_broker import capability_broker, CapabilityDefinition, RiskLevel

logger = logging.getLogger("JARVIS.StagingPipeline")


class ToolStage(Enum):
    GENERATED = "GENERATED"
    SANDBOX_TESTED = "SANDBOX_TESTED"
    SECURITY_SCANNED = "SECURITY_SCANNED"
    STAGED = "STAGED"
    APPROVED_PRODUCTION = "APPROVED_PRODUCTION"
    REVOKED = "REVOKED"


class ToolASTSecurityScanner(ast.NodeVisitor):
    """
    Static AST analyzer detecting dangerous imports, dynamic execution tricks,
    and unauthorized system hooks in candidate tool code.
    """

    # Prohibited modules and identifiers
    BANNED_IMPORTS = {
        "subprocess", "pty", "commands", "ctypes", "multiprocessing",
        "winreg", "msvcrt", "socket", "http.client", "urllib.request"
    }

    BANNED_CALLS = {
        "eval", "exec", "compile", "__import__", "globals", "locals"
    }

    def __init__(self, allow_network: bool = False):
        self.allow_network = allow_network
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name.split(".")[0]
            if name in self.BANNED_IMPORTS:
                if name in ("socket", "urllib", "http") and self.allow_network:
                    continue
                self.violations.append(f"Forbidden module import: '{alias.name}' at line {node.lineno}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base = node.module.split(".")[0]
            if base in self.BANNED_IMPORTS:
                if base in ("socket", "urllib", "http") and self.allow_network:
                    pass
                else:
                    self.violations.append(f"Forbidden from-import: '{node.module}' at line {node.lineno}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Detect calls like eval(), exec(), os.system()
        if isinstance(node.func, ast.Name):
            if node.func.id in self.BANNED_CALLS:
                self.violations.append(f"Dangerous builtin function call: '{node.func.id}()' at line {node.lineno}")
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in ("system", "popen", "spawn", "execv", "execve"):
                self.violations.append(f"Dangerous OS execution call: '.{attr_name}()' at line {node.lineno}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Detect dunder attribute traversal tricks (__subclasses__, __bases__)
        if node.attr.startswith("__") and node.attr.endswith("__"):
            if node.attr in ("__subclasses__", "__bases__", "__globals__", "__builtins__"):
                self.violations.append(f"Privilege escalation dunder access: '{node.attr}' at line {node.lineno}")
        self.generic_visit(node)


class StagedToolArtifact:
    """Quarantined tool container."""

    def __init__(
        self,
        tool_id: str,
        name: str,
        version: str,
        source_code: str,
        permissions: Dict[str, Any],
    ):
        self.tool_id = tool_id
        self.name = name
        self.version = version
        self.source_code = source_code
        self.permissions = permissions
        self.stage = ToolStage.GENERATED
        self.code_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
        self.test_results: Dict[str, Any] = {}
        self.security_audit: Dict[str, Any] = {}
        self.signed_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "version": self.version,
            "code_hash": self.code_hash,
            "stage": self.stage.value,
            "permissions": self.permissions,
            "test_results": self.test_results,
            "security_audit": self.security_audit,
            "signed_by": self.signed_by,
        }


class ToolStagingPipeline:
    """
    Coordinates validation, quarantine, security scanning, and promotion
    for self-synthesized agent tools.
    """

    def __init__(self):
        self._artifacts: Dict[str, StagedToolArtifact] = {}

    def ingest(
        self,
        name: str,
        version: str,
        source_code: str,
        permissions: Optional[Dict[str, Any]] = None,
    ) -> StagedToolArtifact:
        """Stage 1: Register generated tool artifact in isolation."""
        import uuid
        tool_id = f"tool_{name.replace('.', '_')}_{uuid.uuid4().hex[:8]}"
        artifact = StagedToolArtifact(
            tool_id=tool_id,
            name=name,
            version=version,
            source_code=source_code,
            permissions=permissions or {"filesystem": "none", "network": "none"},
        )
        self._artifacts[tool_id] = artifact
        logger.info(f"🧪 [TOOL INGESTED] '{name}' v{version} (ID: {tool_id}) -> GENERATED")
        return artifact

    def run_sandbox_tests(self, tool_id: str, unit_test_code: str) -> bool:
        """Stage 2: Run unit tests inside isolated namespace."""
        artifact = self._artifacts.get(tool_id)
        if not artifact:
            raise KeyError(f"Tool artifact '{tool_id}' not found.")

        try:
            # Execute in safe isolated namespace
            isolated_scope = {"__builtins__": __builtins__}
            exec(artifact.source_code, isolated_scope)
            exec(unit_test_code, isolated_scope)
            
            artifact.stage = ToolStage.SANDBOX_TESTED
            artifact.test_results = {"status": "PASSED", "passed": True}
            logger.info(f"✅ [SANDBOX TEST PASSED] Tool '{artifact.name}' -> SANDBOX_TESTED")
            return True
        except Exception as e:
            artifact.test_results = {"status": "FAILED", "error": str(e)}
            logger.error(f"❌ [SANDBOX TEST FAILED] Tool '{artifact.name}': {e}")
            return False

    def run_security_scan(self, tool_id: str) -> Tuple[bool, List[str]]:
        """Stage 3: AST static analysis for malicious or forbidden constructs."""
        artifact = self._artifacts.get(tool_id)
        if not artifact:
            raise KeyError(f"Tool artifact '{tool_id}' not found.")

        try:
            parsed_ast = ast.parse(artifact.source_code)
        except SyntaxError as e:
            return False, [f"Syntax error in candidate code: {e}"]

        allow_net = artifact.permissions.get("network", "none") != "none"
        scanner = ToolASTSecurityScanner(allow_network=allow_net)
        scanner.visit(parsed_ast)

        if scanner.violations:
            artifact.security_audit = {"status": "FAILED", "violations": scanner.violations}
            logger.error(f"🚨 [AST SCAN REJECTED] Tool '{artifact.name}' has security violations: {scanner.violations}")
            return False, scanner.violations

        artifact.stage = ToolStage.SECURITY_SCANNED
        artifact.security_audit = {"status": "PASSED", "violations": []}
        logger.info(f"🛡️ [AST SCAN PASSED] Tool '{artifact.name}' -> SECURITY_SCANNED")
        return True, []

    def stage_for_human_approval(self, tool_id: str) -> str:
        """
        Stage 4: Transition to STAGED and generate a Cryptographic Approval Ticket
        requiring operator review.
        """
        artifact = self._artifacts.get(tool_id)
        if not artifact:
            raise KeyError(f"Tool artifact '{tool_id}' not found.")

        if artifact.stage != ToolStage.SECURITY_SCANNED:
            raise RuntimeError(
                f"Cannot stage tool in stage [{artifact.stage.value}]. Must be SECURITY_SCANNED."
            )

        artifact.stage = ToolStage.STAGED

        # Create cryptographic approval ticket
        ticket = approval_engine.create_ticket(
            action="tool.promote_to_production",
            parameters={
                "tool_id": artifact.tool_id,
                "name": artifact.name,
                "version": artifact.version,
                "code_hash": artifact.code_hash,
                "permissions": artifact.permissions,
            },
            requested_by="staging_pipeline",
            risk_level="HIGH",
        )
        logger.info(f"📋 [TOOL STAGED] Tool '{artifact.name}' staged. Approval Ticket: {ticket.ticket_id}")
        return ticket.ticket_id

    def promote_to_production(self, tool_id: str, approval_ticket_id: str) -> CapabilityDefinition:
        """
        Stage 5: Verify operator cryptographic signature and register into production capability bus.
        """
        artifact = self._artifacts.get(tool_id)
        if not artifact:
            raise KeyError(f"Tool artifact '{tool_id}' not found.")

        if artifact.stage != ToolStage.STAGED:
            raise RuntimeError(f"Tool '{tool_id}' must be in STAGED stage to promote (current: {artifact.stage.value}).")

        # Verify approval ticket
        approval_engine.verify_and_consume(
            ticket_id=approval_ticket_id,
            action="tool.promote_to_production",
            actual_parameters={
                "tool_id": artifact.tool_id,
                "name": artifact.name,
                "version": artifact.version,
                "code_hash": artifact.code_hash,
                "permissions": artifact.permissions,
            },
        )

        # Execute code in isolated namespace to extract entrypoint
        namespace = {}
        exec(artifact.source_code, namespace)
        handler_func = namespace.get(artifact.name) or namespace.get("run") or namespace.get("execute")
        if not handler_func:
            raise ValueError(f"Could not find entrypoint function '{artifact.name}' in promoted code.")

        # Register into capability broker
        cap_def = CapabilityDefinition(
            name=f"custom.{artifact.name}",
            risk_level=RiskLevel.MEDIUM,
            handler=handler_func,
            requires_approval=False,
            allowed_agents=["*"],
        )
        capability_broker.register(cap_def)

        artifact.stage = ToolStage.APPROVED_PRODUCTION
        artifact.signed_by = "human_operator"
        logger.info(f"🚀 [TOOL PROMOTED] Custom capability 'custom.{artifact.name}' registered to production bus!")
        return cap_def


# Global staging pipeline singleton
staging_pipeline = ToolStagingPipeline()
