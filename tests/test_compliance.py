"""Unit tests for compliance gates and system safety."""

import pytest
from agents.meet_operator import JARVIS_DISCLOSURE_TEXT, DEAL_AUTO_APPROVE_THRESHOLD_USD
from audio.tts import TextToSpeech


def test_ai_disclosure_compliance():
    """Verify that mandatory AI disclosure clearly announces AI identity and recording."""
    assert "AI assistant" in JARVIS_DISCLOSURE_TEXT or "AI" in JARVIS_DISCLOSURE_TEXT
    assert "recorded" in JARVIS_DISCLOSURE_TEXT.lower()
    assert "consent" in JARVIS_DISCLOSURE_TEXT.lower()


def test_financial_threshold_configuration():
    """Ensure auto-approve threshold has a safe positive numeric ceiling."""
    assert isinstance(DEAL_AUTO_APPROVE_THRESHOLD_USD, float)
    assert DEAL_AUTO_APPROVE_THRESHOLD_USD > 0
    assert DEAL_AUTO_APPROVE_THRESHOLD_USD <= 1000.0


def test_tts_cache_cleanup():
    """Verify cache cleanup runs without error."""
    purged = TextToSpeech.cleanup_cache(max_age_hours=0)
    assert isinstance(purged, int)
