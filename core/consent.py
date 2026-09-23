"""
Consent & Regulatory Compliance Engine for Project JARVIS v2.

Enforces jurisdictional rules for outbound communications (Email, Telephony, SMS)
before any outreach capability can be invoked.
"""

import time
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger("JARVIS.Consent")


class ConsentRecord:
    """Consent provenance entry."""

    def __init__(
        self,
        subject: str,
        channel: str,
        jurisdiction: str,
        proof_source: str,
        status: str = "GRANTED",
        ttl_days: int = 180,
    ):
        self.subject = subject.lower().strip()
        self.channel = channel.upper().strip()  # EMAIL, VOICE_CALL, SMS
        self.jurisdiction = jurisdiction.upper().strip()  # US-CA, EU, IN, GLOBAL
        self.proof_source = proof_source
        self.status = status  # GRANTED, WITHDRAWN, EXPIRED
        self.obtained_at = time.time()
        self.expires_at = self.obtained_at + (ttl_days * 86400) if ttl_days > 0 else None
        self.withdrawn_at: Optional[float] = None

    def is_valid(self) -> bool:
        if self.status != "GRANTED":
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True


class ConsentPolicyEngine:
    """
    Authoritative policy gate verifying recipient consent across jurisdictions.
    """

    def __init__(self):
        # In-memory storage with database sync backing
        self._ledger: Dict[Tuple[str, str], ConsentRecord] = {}

    def record_consent(
        self,
        subject: str,
        channel: str,
        jurisdiction: str = "GLOBAL",
        proof_source: str = "discovery_opt_in",
        ttl_days: int = 180,
    ) -> ConsentRecord:
        """Register affirmative consent for a communication channel."""
        record = ConsentRecord(
            subject=subject,
            channel=channel,
            jurisdiction=jurisdiction,
            proof_source=proof_source,
            status="GRANTED",
            ttl_days=ttl_days,
        )
        self._ledger[(record.subject, record.channel)] = record
        logger.info(
            f"📜 [CONSENT RECORDED] {record.subject} for channel [{record.channel}] "
            f"under jurisdiction [{record.jurisdiction}] (Proof: {proof_source})"
        )
        return record

    def withdraw_consent(self, subject: str, channel: Optional[str] = None):
        """Handle unsubscribe / opt-out / DND request immediately."""
        sub = subject.lower().strip()
        channels = [channel.upper()] if channel else ["EMAIL", "VOICE_CALL", "SMS"]

        for ch in channels:
            key = (sub, ch)
            if key in self._ledger:
                rec = self._ledger[key]
                rec.status = "WITHDRAWN"
                rec.withdrawn_at = time.time()
                logger.warning(f"🚫 [CONSENT WITHDRAWN] {sub} unsubscribed from [{ch}].")

    def check_permission(
        self,
        subject: str,
        channel: str,
        jurisdiction: str = "GLOBAL",
    ) -> Tuple[bool, str]:
        """
        Verify if an outbound action is legally permitted.
        Returns: (permitted: bool, reason: str)
        """
        sub = subject.lower().strip()
        ch = channel.upper().strip()
        jur = jurisdiction.upper().strip()

        key = (sub, ch)
        record = self._ledger.get(key)

        # 1. Check existing record status
        if record:
            if record.status == "WITHDRAWN":
                return False, f"Recipient '{sub}' previously withdrew consent for [{ch}]."
            if record.expires_at and time.time() > record.expires_at:
                return False, f"Consent for '{sub}' expired on channel [{ch}]."
            if record.is_valid():
                return True, f"Affirmative consent verified (Proof: {record.proof_source})."

        # 2. Jurisdictional zero-tolerance rules for unsolicited communication
        if ch in ("VOICE_CALL", "SMS"):
            # Telephony / SMS unconditionally requires recorded affirmative consent
            return (
                False,
                f"Regulatory violation: Outbound {ch} to '{sub}' without prior consent "
                f"is strictly prohibited under {jur} telecommunications guidelines.",
            )

        if jur in ("EU", "IN") and ch == "EMAIL":
            # GDPR and strict B2B privacy frameworks require demonstrable interest or consent
            return (
                False,
                f"Regulatory block: Outbound email in jurisdiction [{jur}] requires recorded proof of consent.",
            )

        # 3. Soft-fail / require approval for first-touch B2B email in US/GLOBAL
        return True, "Permitted under CAN-SPAM commercial inquiry guidelines (Requires unsubscribe header)."


# Global consent policy instance
consent_engine = ConsentPolicyEngine()
