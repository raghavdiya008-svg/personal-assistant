"""
Cryptographic Human-In-The-Loop (HITL) Approval Engine for Project JARVIS v2.

Guarantees that human approvals are cryptographically bound to the EXACT action
and parameter payload. Rejects parameter tampering, replay attacks, and clock expiration.
"""

import hmac
import hashlib
import json
import time
import uuid
import logging
from typing import Dict, Any, Optional
from core.config import settings

logger = logging.getLogger("JARVIS.Approvals")


class ApprovalTicket:
    """Tamper-evident approval record."""

    def __init__(
        self,
        ticket_id: str,
        action: str,
        parameters: Dict[str, Any],
        params_hash: str,
        nonce: str,
        requested_by: str,
        risk_level: str = "HIGH",
        ttl_seconds: int = 600,
    ):
        self.ticket_id = ticket_id
        self.action = action
        self.parameters = parameters
        self.params_hash = params_hash
        self.nonce = nonce
        self.requested_by = requested_by
        self.risk_level = risk_level
        self.issued_at = time.time()
        self.expires_at = self.issued_at + ttl_seconds
        self.status = "PENDING"
        self.signature: Optional[str] = None
        self.decided_by: Optional[str] = None
        self.executed_at: Optional[float] = None

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "action": self.action,
            "risk_level": self.risk_level,
            "parameters": self.parameters,
            "params_hash": self.params_hash,
            "nonce": self.nonce,
            "requested_by": self.requested_by,
            "status": self.status,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "decided_by": self.decided_by,
            "signature": self.signature,
            "executed_at": self.executed_at,
        }


class CryptographicApprovalEngine:
    """
    Manages the lifecycle of typed, signed approvals.
    Uses HMAC-SHA256 to cryptographically seal approval tokens.
    """

    def __init__(self, secret_key: Optional[str] = None):
        # Derive or load secret key
        raw_key = secret_key or getattr(settings, "APPROVAL_SECRET_KEY", "") or "jarvis_v2_sovereign_secret_key"
        self._secret_key = raw_key.encode("utf-8")
        self._tickets: Dict[str, ApprovalTicket] = {}
        self._used_nonces: set = set()
        self._storage_path = settings.DATA_DIR / "approval_tickets.json"
        self._load_persisted_tickets()

    def _load_persisted_tickets(self):
        """Restore unexpired pending tickets from disk on startup."""
        if not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            now = time.time()
            for tid, t_dict in data.items():
                if t_dict.get("status") == "PENDING" and t_dict.get("expires_at", 0) > now:
                    ticket = ApprovalTicket(
                        ticket_id=t_dict["ticket_id"],
                        action=t_dict["action"],
                        parameters=t_dict["parameters"],
                        params_hash=t_dict["params_hash"],
                        nonce=t_dict["nonce"],
                        requested_by=t_dict["requested_by"],
                        risk_level=t_dict.get("risk_level", "HIGH"),
                        ttl_seconds=int(t_dict["expires_at"] - t_dict["issued_at"]),
                    )
                    ticket.issued_at = t_dict["issued_at"]
                    ticket.expires_at = t_dict["expires_at"]
                    ticket.status = t_dict["status"]
                    ticket.signature = t_dict.get("signature")
                    ticket.decided_by = t_dict.get("decided_by")
                    self._tickets[tid] = ticket
            logger.info(f"Loaded {len(self._tickets)} active approval ticket(s) from persistence.")
        except Exception as e:
            logger.warning(f"Could not load persisted approval tickets: {e}")

    def _persist_tickets(self):
        """Save ticket state to disk."""
        try:
            data = {tid: t.to_dict() for tid, t in self._tickets.items()}
            self._storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to persist approval tickets: {e}")

    def _purge_stale_tickets(self):
        """Clean up expired tickets to prevent memory leaks."""
        now = time.time()
        expired_ids = [
            tid for tid, t in self._tickets.items()
            if (t.is_expired() and t.status == "PENDING") or (t.status in ("EXECUTED", "REJECTED") and now - t.expires_at > 3600)
        ]
        for tid in expired_ids:
            del self._tickets[tid]

    @staticmethod
    def compute_params_hash(parameters: Dict[str, Any]) -> str:
        """Deterministic canonical JSON SHA-256 hash of parameter dictionary."""
        canonical_json = json.dumps(parameters, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def create_ticket(
        self,
        action: str,
        parameters: Dict[str, Any],
        requested_by: str = "agent",
        risk_level: str = "HIGH",
        ttl_seconds: int = 600,
    ) -> ApprovalTicket:
        """Create a new pending approval ticket for a sensitive capability."""
        self._purge_stale_tickets()
        ticket_id = f"appr_{uuid.uuid4().hex[:12]}"
        nonce = f"nonce_{uuid.uuid4().hex[:16]}"
        params_hash = self.compute_params_hash(parameters)

        ticket = ApprovalTicket(
            ticket_id=ticket_id,
            action=action,
            parameters=parameters,
            params_hash=params_hash,
            nonce=nonce,
            requested_by=requested_by,
            risk_level=risk_level,
            ttl_seconds=ttl_seconds,
        )

        self._tickets[ticket_id] = ticket
        self._persist_tickets()
        logger.info(
            f"📋 [APPROVAL CREATED] Ticket '{ticket_id}' for action '{action}' (hash: {params_hash[:10]}...)"
        )
        return ticket

    def _generate_signature(self, ticket: ApprovalTicket, decision: str) -> str:
        """Create cryptographic HMAC signature for approved ticket."""
        message = f"{ticket.ticket_id}:{ticket.action}:{ticket.params_hash}:{ticket.nonce}:{decision}:{ticket.expires_at}"
        return hmac.new(self._secret_key, message.encode("utf-8"), hashlib.sha256).hexdigest()

    def approve_ticket(
        self, ticket_id: str, operator_id: str = "human_operator"
    ) -> ApprovalTicket:
        """Cryptographically sign and grant approval for a ticket."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            raise KeyError(f"Approval ticket '{ticket_id}' not found.")

        if ticket.is_expired():
            ticket.status = "EXPIRED"
            self._persist_tickets()
            raise ValueError(f"Approval ticket '{ticket_id}' has expired.")

        if ticket.status != "PENDING":
            raise ValueError(f"Ticket '{ticket_id}' is not in PENDING state (current: {ticket.status}).")

        ticket.status = "APPROVED"
        ticket.decided_by = operator_id
        ticket.signature = self._generate_signature(ticket, "APPROVED")
        self._persist_tickets()
        logger.info(f"✅ [APPROVAL GRANTED] Ticket '{ticket_id}' signed by {operator_id}")
        return ticket

    def reject_ticket(
        self, ticket_id: str, operator_id: str = "human_operator"
    ) -> ApprovalTicket:
        """Reject and invalidate an approval ticket."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            raise KeyError(f"Approval ticket '{ticket_id}' not found.")

        ticket.status = "REJECTED"
        ticket.decided_by = operator_id
        self._persist_tickets()
        logger.info(f"❌ [APPROVAL REJECTED] Ticket '{ticket_id}' rejected by {operator_id}")
        return ticket

    def verify_and_consume(
        self,
        ticket_id: str,
        action: str,
        actual_parameters: Dict[str, Any],
    ) -> bool:
        """
        Capability Broker pre-execution gate.
        Validates:
          1. Ticket existence & APPROVED status.
          2. Non-expired TTL.
          3. Single-use nonce (anti-replay).
          4. Cryptographic HMAC signature integrity.
          5. Parameter Hash Exact Match (detects payload tampering).
        Marks ticket as EXECUTED upon success.
        """
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            raise SecurityError(f"Verification failed: Ticket '{ticket_id}' does not exist.")

        if ticket.status != "APPROVED":
            raise SecurityError(f"Verification failed: Ticket '{ticket_id}' is not APPROVED (status: {ticket.status}).")

        if ticket.is_expired():
            ticket.status = "EXPIRED"
            raise SecurityError(f"Verification failed: Ticket '{ticket_id}' has expired.")

        if ticket.nonce in self._used_nonces:
            raise SecurityError(f"Verification failed: Replay attack detected for nonce '{ticket.nonce}'.")

        # Check action match
        if ticket.action != action:
            raise SecurityError(f"Action mismatch: Ticket authorized '{ticket.action}', attempted '{action}'.")

        # Check cryptographic signature
        expected_sig = self._generate_signature(ticket, "APPROVED")
        if not hmac.compare_digest(ticket.signature or "", expected_sig):
            raise SecurityError(f"Cryptographic signature check failed for ticket '{ticket_id}'.")

        # PARAMETER TAMPER CHECK: Recompute hash from the actual runtime parameters
        actual_hash = self.compute_params_hash(actual_parameters)
        if actual_hash != ticket.params_hash:
            logger.error(
                f"🚨 [PARAM TAMPER DETECTED] Authorized hash: {ticket.params_hash}, "
                f"Attempted execution hash: {actual_hash}"
            )
            raise SecurityError(
                f"Parameter tampering detected! The runtime parameters do not match "
                f"the cryptographically approved parameters for ticket '{ticket_id}'."
            )

        # Mark consumed
        self._used_nonces.add(ticket.nonce)
        ticket.status = "EXECUTED"
        ticket.executed_at = time.time()
        self._persist_tickets()
        logger.info(f"🛡️ [APPROVAL CONSUMED] Ticket '{ticket_id}' validated and consumed.")
        return True

    def get_pending_tickets(self) -> Dict[str, Dict[str, Any]]:
        self._purge_stale_tickets()
        return {
            tid: t.to_dict()
            for tid, t in self._tickets.items()
            if t.status == "PENDING" and not t.is_expired()
        }


class SecurityError(Exception):
    """Raised on security boundary or verification failure."""
    pass


# Global approval engine instance
approval_engine = CryptographicApprovalEngine()
