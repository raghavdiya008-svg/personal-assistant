"""
Data Trust Taxonomy & Boundary Enforcement for Project JARVIS v2.

Every piece of data entering the system carries an immutable trust tag.
Untrusted external data (scraped web pages, inbound emails, PDFs, voice transcripts)
can NEVER be automatically promoted to executable instructions or bypass security checks.
"""

from enum import IntEnum
import hashlib
import json
import time
import uuid
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger("JARVIS.Trust")


class TrustLevel(IntEnum):
    """
    Explicit Trust Hierarchy. Higher values denote strictly higher trust.
    Strict rule: Only payloads with TrustLevel >= OPERATOR_COMMAND can directly
    trigger privileged capability execution without additional validation.
    """
    UNTRUSTED_EXTERNAL = 0   # Web scrapes, inbound emails, PDFs, audio transcripts
    MODEL_REASONING = 1      # LLM generated text/proposals (untrusted until policy-verified)
    DATABASE_STATE = 2       # Validated records from authoritative Postgres store
    OPERATOR_COMMAND = 3     # Cryptographically authenticated owner (Telegram/Cockpit)
    TRUSTED_SYSTEM_POLICY = 4 # Hardcoded system rules, immutable safety constraints


class TrustedPayload:
    """
    Structured envelope encapsulating content with provenance, cryptographic hash,
    and trust boundaries.
    """

    def __init__(
        self,
        content: Any,
        trust_level: TrustLevel,
        source: str,
        origin: Optional[str] = None,
        sanitized: bool = False,
        payload_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.payload_id = payload_id or f"pay_{uuid.uuid4().hex[:12]}"
        self.trace_id = trace_id or f"tr_{uuid.uuid4().hex[:10]}"
        self.content = content
        self.trust_level = trust_level
        self.source = source
        self.origin = origin or "system"
        self.sanitized = sanitized
        self.created_at = time.time()
        self.metadata = metadata or {}
        
        # Calculate SHA-256 content hash
        self.content_hash = self._compute_hash(content)

    @staticmethod
    def _compute_hash(data: Any) -> str:
        """Produce deterministic SHA-256 fingerprint of content."""
        if isinstance(data, (dict, list)):
            canonical_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        elif isinstance(data, str):
            canonical_bytes = data.encode("utf-8")
        elif isinstance(data, bytes):
            canonical_bytes = data
        else:
            canonical_bytes = str(data).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    @property
    def may_execute(self) -> bool:
        """Executable actions strictly require OPERATOR_COMMAND or higher trust."""
        return self.trust_level >= TrustLevel.OPERATOR_COMMAND

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payload_id": self.payload_id,
            "trace_id": self.trace_id,
            "trust_level": self.trust_level.name,
            "source": self.source,
            "origin": self.origin,
            "content_hash": self.content_hash,
            "sanitized": self.sanitized,
            "may_execute": self.may_execute,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"<TrustedPayload id={self.payload_id} trust={self.trust_level.name} src={self.source}>"


class TrustGuard:
    """Zero-trust policy evaluator for payload transitions."""

    @classmethod
    def wrap_untrusted(
        cls, content: Any, source: str = "external_web", origin: Optional[str] = None
    ) -> TrustedPayload:
        """Wrap external, untrusted content (e.g. from browser-use or email)."""
        return TrustedPayload(
            content=content,
            trust_level=TrustLevel.UNTRUSTED_EXTERNAL,
            source=source,
            origin=origin,
            sanitized=False,
        )

    @classmethod
    def wrap_model(cls, content: str, source: str = "llm_completion") -> TrustedPayload:
        """Wrap model reasoning output."""
        return TrustedPayload(
            content=content,
            trust_level=TrustLevel.MODEL_REASONING,
            source=source,
            origin="llm_gateway",
            sanitized=False,
        )

    @classmethod
    def wrap_operator(
        cls, content: str, source: str = "telegram_cockpit"
    ) -> TrustedPayload:
        """Wrap authenticated operator command."""
        return TrustedPayload(
            content=content,
            trust_level=TrustLevel.OPERATOR_COMMAND,
            source=source,
            origin="human_operator",
            sanitized=True,
        )

    @classmethod
    def wrap_system(cls, content: Any, source: str = "system_policy") -> TrustedPayload:
        """Wrap internal authoritative policy."""
        return TrustedPayload(
            content=content,
            trust_level=TrustLevel.TRUSTED_SYSTEM_POLICY,
            source=source,
            origin="kernel",
            sanitized=True,
        )

    @classmethod
    def assert_capability_authorization(
        cls, payload: TrustedPayload, required_trust: TrustLevel = TrustLevel.OPERATOR_COMMAND
    ) -> bool:
        """
        Verify that a payload meets or exceeds the required trust boundary before
        allowing it to trigger a capability.
        Raises PermissionError if trust level is insufficient.
        """
        if payload.trust_level < required_trust:
            err_msg = (
                f"🛑 [TRUST BOUNDARY VIOLATION] Payload '{payload.payload_id}' "
                f"with trust level [{payload.trust_level.name}] attempted to execute "
                f"an operation requiring [{required_trust.name}]."
            )
            logger.error(err_msg)
            raise PermissionError(err_msg)
        return True
