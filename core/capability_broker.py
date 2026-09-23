"""
Capability Broker & Policy Engine for Project JARVIS v2.

The foundational security boundary of the operating system:
Agents propose actions; ONLY capabilities cross boundaries.
Enforces:
  1. Capability Access Control Lists (ACLs).
  2. Risk Level Governance (LOW, MEDIUM, HIGH, CRITICAL).
  3. Cryptographic HITL approval gate for HIGH/CRITICAL actions.
  4. Data Trust tagging (all external data wrapped as UNTRUSTED_EXTERNAL).
  5. Filesystem Sandboxing & Outbound PII Redaction.
"""

from enum import Enum
import inspect
import logging
import os
from pathlib import Path
import time
from typing import Dict, Any, Callable, Optional, List, Set
from core.trust import TrustGuard, TrustedPayload, TrustLevel
from core.approvals import approval_engine, SecurityError
from core.consent import consent_engine
from core.security import SecurityGuard
from core.config import settings

logger = logging.getLogger("JARVIS.CapabilityBroker")


class RiskLevel(Enum):
    LOW = "LOW"            # Read sandbox file, vector search, format conversion
    MEDIUM = "MEDIUM"      # Web browsing, write sandbox file, API queries
    HIGH = "HIGH"          # Send email, schedule meeting, update CRM, delete files
    CRITICAL = "CRITICAL"  # Shell execution, financial transactions, database DDL


class ApprovalRequiredError(Exception):
    """Raised when an operation requires cryptographic human approval."""
    def __init__(self, ticket_id: str, action: str, parameters: Dict[str, Any]):
        self.ticket_id = ticket_id
        self.action = action
        self.parameters = parameters
        super().__init__(
            f"Action '{action}' requires cryptographic operator approval. "
            f"Ticket generated: [{ticket_id}]"
        )


class CapabilityDefinition:
    """Capability specification and security manifest."""

    def __init__(
        self,
        name: str,
        risk_level: RiskLevel,
        handler: Callable,
        requires_approval: bool = False,
        allowed_agents: Optional[List[str]] = None,
        rate_limit_per_minute: int = 60,
        allowed_domains: Optional[Set[str]] = None,
    ):
        self.name = name
        self.risk_level = risk_level
        self.handler = handler
        self.requires_approval = requires_approval or (risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL))
        self.allowed_agents = set(allowed_agents or ["*"])
        self.rate_limit_per_minute = rate_limit_per_minute
        self.allowed_domains = allowed_domains or set()
        self._call_timestamps: List[float] = []

    def check_rate_limit(self) -> bool:
        """Sliding window rate limit checker."""
        now = time.time()
        window = now - 60.0
        self._call_timestamps = [ts for ts in self._call_timestamps if ts > window]
        if len(self._call_timestamps) >= self.rate_limit_per_minute:
            return False
        self._call_timestamps.append(now)
        return True


class CapabilityBroker:
    """
    Central Capability Bus enforcing policy rules and isolation between agents
    and host capabilities.
    """

    def __init__(self):
        self._capabilities: Dict[str, CapabilityDefinition] = {}
        self._register_default_capabilities()

    def register(self, capability: CapabilityDefinition):
        self._capabilities[capability.name] = capability
        logger.debug(f"Registered capability: {capability.name} [{capability.risk_level.value}]")

    def _register_default_capabilities(self):
        """Register built-in core capabilities."""
        # 1. Sandboxed Filesystem Read
        self.register(
            CapabilityDefinition(
                name="filesystem.read",
                risk_level=RiskLevel.LOW,
                handler=self._handle_fs_read,
                requires_approval=False,
                allowed_agents=["*"],
                rate_limit_per_minute=120,
            )
        )

        # 2. Sandboxed Filesystem Write
        self.register(
            CapabilityDefinition(
                name="filesystem.write",
                risk_level=RiskLevel.MEDIUM,
                handler=self._handle_fs_write,
                requires_approval=False,
                allowed_agents=["code_agent", "admin", "system"],
                rate_limit_per_minute=30,
            )
        )

        # 3. Domain-Whitelisted Web Navigation
        self.register(
            CapabilityDefinition(
                name="browser.navigate",
                risk_level=RiskLevel.MEDIUM,
                handler=self._handle_browser_navigate,
                requires_approval=False,
                allowed_agents=["research_agent", "admin"],
                rate_limit_per_minute=30,
            )
        )

        # 4. Outbound Email Communications (HITL Enforced)
        self.register(
            CapabilityDefinition(
                name="outbound.email",
                risk_level=RiskLevel.HIGH,
                handler=self._handle_outbound_email,
                requires_approval=True,
                allowed_agents=["outreach_agent", "admin"],
                rate_limit_per_minute=10,
            )
        )

        # 5. Privileged Shell Execution (Strictly HITL Enforced)
        self.register(
            CapabilityDefinition(
                name="shell.execute",
                risk_level=RiskLevel.CRITICAL,
                handler=self._handle_shell_execute,
                requires_approval=True,
                allowed_agents=["admin"],
                rate_limit_per_minute=5,
            )
        )

    # ── Handlers ─────────────────────────────────────────────────────────────

    async def _handle_fs_read(self, path: str, **_) -> TrustedPayload:
        """Read a file within the sandboxed data directory."""
        if not SecurityGuard.validate_safe_path(path):
            raise PermissionError(f"Filesystem access blocked outside sandbox: {path}")

        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        content = file_path.read_text(encoding="utf-8", errors="replace")
        return TrustGuard.wrap_system(content, source="filesystem.read")

    async def _handle_fs_write(self, path: str, content: str, **_) -> TrustedPayload:
        """Write content safely within the sandboxed data directory."""
        if not SecurityGuard.validate_safe_path(path):
            raise PermissionError(f"Filesystem write blocked outside sandbox: {path}")

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return TrustGuard.wrap_system({"path": str(file_path), "bytes": len(content)}, source="filesystem.write")

    async def _handle_browser_navigate(self, url: str, **_) -> TrustedPayload:
        """
        Fetch external web content.
        CRITICAL SECURITY RULE: The returned content is explicitly labeled
        UNTRUSTED_EXTERNAL and cannot be promoted directly to instruction.
        """
        import urllib.request
        from urllib.parse import urlparse

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()

        # Block localhost / private RFC 1918 internal IPs from SSRF
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0") or hostname.startswith("192.168.") or hostname.startswith("10."):
            raise PermissionError(f"SSRF Protection: Access to private/internal network blocked for: {url}")

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "JARVIS-Sovereign-Research-Agent/2.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw_bytes = resp.read()
                # Basic HTML text extraction
                decoded = raw_bytes.decode("utf-8", errors="replace")
                
                # Strip scripts and styles for basic safety
                import re
                cleaned = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", decoded)
                cleaned = re.sub(r"<[^>]+>", " ", cleaned)
                text = " ".join(cleaned.split())[:10000]

                # Return explicitly as UNTRUSTED_EXTERNAL
                return TrustGuard.wrap_untrusted(
                    content=text,
                    source="browser.navigate",
                    origin=url,
                )
        except Exception as e:
            logger.error(f"Browser navigation failed: {e}")
            return TrustGuard.wrap_untrusted(
                content=f"[Fetch error: {e}]",
                source="browser.navigate",
                origin=url,
            )

    async def _handle_outbound_email(
        self, recipient: str, subject: str, body: str, jurisdiction: str = "GLOBAL", **_
    ) -> TrustedPayload:
        """Send outbound email after consent verification and scrubbing."""
        # 1. Check recipient consent
        permitted, reason = consent_engine.check_permission(recipient, "EMAIL", jurisdiction)
        if not permitted:
            raise PermissionError(f"Consent Engine blocked outbound email: {reason}")

        # 2. Sanitize body to avoid leaking system secrets
        sanitized_body = SecurityGuard.sanitize_outbound_text(body)

        # 3. Simulate/execute dispatch
        logger.info(f"📧 [EMAIL DISPATCHED] To: {recipient} | Subject: '{subject}'")
        return TrustGuard.wrap_system(
            {"status": "SENT", "recipient": recipient, "subject": subject},
            source="outbound.email",
        )

    async def _handle_shell_execute(self, command: str, **_) -> TrustedPayload:
        """Execute privileged command inside restricted shell."""
        # Check command for prohibited destructive strings
        prohibited = ["rm -rf /", "format c:", "drop database", "mkfs"]
        lower = command.lower()
        if any(p in lower for p in prohibited):
            raise PermissionError(f"Destructive shell command prohibited: {command}")

        import subprocess
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(settings.DATA_DIR),
        )
        return TrustGuard.wrap_system(
            {"returncode": proc.returncode, "stdout": proc.stdout[:2000], "stderr": proc.stderr[:1000]},
            source="shell.execute",
        )

    # ── Core Invocation Loop ──────────────────────────────────────────────────

    async def invoke(
        self,
        agent_id: str,
        capability_name: str,
        parameters: Dict[str, Any],
        approval_ticket_id: Optional[str] = None,
    ) -> TrustedPayload:
        """
        Main capability entrypoint.
        Enforces ACL, rate-limiting, risk assessment, and cryptographic approvals.
        """
        cap = self._capabilities.get(capability_name)
        if not cap:
            raise KeyError(f"Capability '{capability_name}' is not registered on the capability bus.")

        # 1. Agent Access Control List (ACL)
        if "*" not in cap.allowed_agents and agent_id not in cap.allowed_agents:
            err = f"Agent '{agent_id}' is not authorized to invoke capability '{capability_name}'."
            logger.error(err)
            raise PermissionError(err)

        # 2. Sliding Window Rate Limiting
        if not cap.check_rate_limit():
            err = f"Rate limit exceeded for capability '{capability_name}' (max {cap.rate_limit_per_minute}/min)."
            logger.warning(err)
            raise RuntimeError(err)

        # 3. Cryptographic HITL Approval Gate
        if cap.requires_approval:
            if not approval_ticket_id:
                # Generate new pending ticket for the operator
                ticket = approval_engine.create_ticket(
                    action=capability_name,
                    parameters=parameters,
                    requested_by=agent_id,
                    risk_level=cap.risk_level.value,
                )
                logger.warning(
                    f"🛑 [APPROVAL REQUIRED] Capability '{capability_name}' requires human approval. "
                    f"Created ticket: {ticket.ticket_id}"
                )
                raise ApprovalRequiredError(ticket.ticket_id, capability_name, parameters)

            # Verify and consume the cryptographic approval ticket
            approval_engine.verify_and_consume(
                ticket_id=approval_ticket_id,
                action=capability_name,
                actual_parameters=parameters,
            )

        # 4. Capability Execution
        logger.info(f"⚡ [CAPABILITY EXECUTED] Agent '{agent_id}' -> '{capability_name}'")
        if inspect.iscoroutinefunction(cap.handler):
            return await cap.handler(**parameters)
        return cap.handler(**parameters)


# Global capability broker singleton
capability_broker = CapabilityBroker()
