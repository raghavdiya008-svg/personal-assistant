"""
Security, Privacy & Sandboxing Shield for Project JARVIS.

Protects against:
1. Prompt Injections & Jailbreak Attempts (audio & text).
2. Owner Impersonation & Social Engineering on calls.
3. Outbound Data Exfiltration (PII, Local PC Paths, API Keys).
4. Filesystem Traversal (strictly jails file access to data/ directory).
"""

import re
import logging
from pathlib import Path
from typing import Tuple, Optional
from core.config import settings

logger = logging.getLogger("JARVIS.Security")


class SecurityGuard:
    """Zero-Trust boundary protecting system memory, files, and identity."""

    # Patterns indicating prompt injection or jailbreak attempts
    INJECTION_PATTERNS = [
        r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+instructions\b",
        r"(?i)\bdisregard\s+(all\s+)?(previous|prior|above)\b",
        r"(?i)\bdeveloper\s+mode\b",
        r"(?i)\bjailbreak\b",
        r"(?i)\byou\s+are\s+now\s+(in\s+)?(dan|root|god|admin|unrestricted)\b",
        r"(?i)\bprint\s+(your\s+)?(system\s+prompt|instructions|rules)\b",
        r"(?i)\breveal\s+(your\s+)?(system\s+prompt|api\s*key|secret|password)\b",
        r"(?i)\bwhat\s+(is|are)\s+your\s+(initial\s+)?(instructions|prompt|rules)\b",
        r"(?i)\bdrop\s+table\b",
        r"(?i)\bselect\s+\*\s+from\b",
        r"(?i)\brm\s+-rf\b",
        r"(?i)\bformat\s+[a-z]:(?:\s|$)",
        r"(?i)\bos\.system\b",
        r"(?i)\bsubprocess\b",
        r"(?i)\bexec\(",
        r"(?i)\beval\(",
    ]

    # Patterns indicating caller is attempting to claim owner/admin authority
    IMPERSONATION_PATTERNS = [
        r"(?i)\bi\s+am\s+(your\s+)?(owner|founder|boss|admin|creator|developer)\b",
        r"(?i)\bthis\s+is\s+(your\s+)?(owner|founder|boss|admin|creator)\b",
        r"(?i)\bi\s+built\s+you\b",
        r"(?i)\bgive\s+me\s+admin\b",
        r"(?i)\boverride\s+code\b",
        r"(?i)\bmaintenance\s+mode\b",
        r"(?i)\bemergency\s+protocol\b",
    ]

    # Secret and PII redaction patterns for outbound text
    REDACTION_PATTERNS = [
        (r"gsk_[a-zA-Z0-9]{30,}", "[REDACTED_GROQ_KEY]"),
        (r"sk-[a-zA-Z0-9_-]{20,}", "[REDACTED_API_KEY]"),
        (r"ghp_[a-zA-Z0-9]{30,}", "[REDACTED_GITHUB_TOKEN]"),
        (r"AQ\.[a-zA-Z0-9_-]{30,}", "[REDACTED_GEMINI_KEY]"),
        (r"(?i)[a-z]:\\[Users|Windows|Program][^ \n\r\t\"']+", "[LOCAL_PATH_REDACTED]"),
        (r"/home/[^ \n\r\t\"']+", "[LOCAL_PATH_REDACTED]"),
        (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED_PAYMENT_CARD]"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
    ]

    @classmethod
    def inspect_client_input(cls, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Inspect client speech or input before sending to brain.
        Returns: (is_safe: bool, threat_type: Optional[str], safe_deflection: Optional[str])
        """
        if not text:
            return True, None, None

        # 1. Check for prompt injection / jailbreak
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, text):
                logger.warning(f"🚨 [SECURITY ALERT] Prompt injection detected matching: {pattern}")
                return (
                    False,
                    "PROMPT_INJECTION",
                    "I am programmed to strictly discuss our enterprise software capabilities "
                    "and schedule discovery meetings. How can I help with your project goals?"
                )

        # 2. Check for caller attempting to claim owner/admin authority
        for pattern in cls.IMPERSONATION_PATTERNS:
            if re.search(pattern, text):
                logger.warning(f"🚨 [SECURITY ALERT] Impersonation attempt detected matching: {pattern}")
                return (
                    False,
                    "IMPERSONATION",
                    "All administrative and system controls are restricted exclusively to our "
                    "cryptographically authenticated Telegram cockpit. On Google Meet calls, I only "
                    "serve as a discovery and sales assistant. How can I assist with your business requirements?"
                )

        return True, None, None

    @classmethod
    def sanitize_outbound_text(cls, text: str) -> str:
        """
        Scrub system secrets, API keys, local PC directory paths, and PII from
        any text before it is spoken on a call or sent over email.
        """
        if not text:
            return ""

        sanitized = text
        for pattern, replacement in cls.REDACTION_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized

    @classmethod
    def validate_safe_path(cls, target_path: str) -> bool:
        """
        Filesystem Sandbox: Enforce that all file read/writes remain strictly
        confined within the application's data directory. Blocks path traversal.
        """
        try:
            resolved_target = Path(target_path).resolve()
            resolved_data = settings.DATA_DIR.resolve()
            
            # Target must be within DATA_DIR
            resolved_target.relative_to(resolved_data)
            return True
        except (ValueError, Exception):
            logger.error(f"🛑 [SANDBOX VIOLATION] Attempted file access outside data dir: {target_path}")
            return False


security_guard = SecurityGuard()
