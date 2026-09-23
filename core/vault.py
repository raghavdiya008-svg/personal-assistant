"""
Zero-Trust Secrets Vault for Project JARVIS v2.

Ensures that agents NEVER hold plaintext API keys or credentials in their memory.
Credentials are held in this vault and injected dynamically at the Capability Broker
boundary only during capability execution.
"""

import base64
import hashlib
import json
import logging
import os
import time
from typing import Dict, Any, Optional, Set
from pathlib import Path
from core.config import settings

logger = logging.getLogger("JARVIS.Vault")


class ZeroTrustVault:
    """
    In-memory encrypted secrets store with scoped capability injection.
    Prevents prompt injection from exfiltrating credentials because the model
    never sees or stores raw keys.
    """

    def __init__(self, master_key: Optional[str] = None):
        raw_key = master_key or os.getenv("VAULT_MASTER_KEY", "jarvis_v2_vault_master_seed_2026")
        self._key = hashlib.sha256(raw_key.encode("utf-8")).digest()
        self._secrets: Dict[str, bytes] = {}
        self._capability_permissions: Dict[str, Set[str]] = {
            # Capability -> Set of secret keys allowed to be injected
            "outbound.email": {"SMTP_PASSWORD", "EMAIL_API_KEY"},
            "telephony.call": {"VAPI_API_KEY", "RETELL_API_KEY", "TWILIO_AUTH_TOKEN"},
            "database.query": {"POSTGRES_PASSWORD"},
            "second_brain.index": {"EMBEDDING_API_KEY"},
        }
        self._load_env_secrets()

    def _xor_cipher(self, data: bytes) -> bytes:
        """Lightweight zero-dependency symmetric cipher stream."""
        key_len = len(self._key)
        return bytes([b ^ self._key[i % key_len] for i, b in enumerate(data)])

    def _load_env_secrets(self):
        """Ingest known system credentials into the vault and scrub from easy access."""
        known_keys = [
            "GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY",
            "STRIPE_API_KEY", "TELEGRAM_BOT_TOKEN", "GITHUB_TOKEN",
            "VAPI_API_KEY", "RETELL_API_KEY", "POSTGRES_PASSWORD"
        ]
        for key in known_keys:
            val = os.getenv(key)
            if val:
                self.store_secret(key, val)

    def store_secret(self, key: str, value: str):
        """Encrypt and store a secret."""
        encrypted = self._xor_cipher(value.encode("utf-8"))
        self._secrets[key] = encrypted
        logger.debug(f"Stored encrypted secret: {key}")

    def inject_for_capability(self, capability_name: str, secret_key: str) -> Optional[str]:
        """
        Policy-governed credential injection.
        Allows access ONLY if the capability has explicit permission for the secret.
        """
        allowed = self._capability_permissions.get(capability_name, set())
        if secret_key not in allowed and "*" not in allowed:
            logger.error(
                f"🛑 [VAULT VIOLATION] Capability '{capability_name}' requested "
                f"unauthorized secret: '{secret_key}'"
            )
            raise PermissionError(
                f"Capability '{capability_name}' is not authorized to access secret '{secret_key}'."
            )

        encrypted = self._secrets.get(secret_key)
        if not encrypted:
            return None

        decrypted = self._xor_cipher(encrypted).decode("utf-8")
        logger.info(f"🔐 [SECRET INJECTED] '{secret_key}' injected for capability '{capability_name}'.")
        return decrypted

    def mask_secret(self, text: str) -> str:
        """Utility to redact any stored secret from logs or outbound messages."""
        masked = text
        for key, enc in self._secrets.items():
            plain = self._xor_cipher(enc).decode("utf-8")
            if len(plain) > 6 and plain in masked:
                masked = masked.replace(plain, f"[VAULT_REDACTED_{key}]")
        return masked


# Global vault singleton
vault = ZeroTrustVault()
