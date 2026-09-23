"""
Tests for Free API Multiplexer & Burst Compute Pool in Project JARVIS v2.
"""

import pytest
from core.freellmapi import FreeAPIMultiplexer, FreeProviderEndpoint


@pytest.fixture
def pool():
    p = FreeAPIMultiplexer()
    p.endpoints = [
        FreeProviderEndpoint("test_groq", "qwen-27b", "dummy_groq_key"),
        FreeProviderEndpoint("test_gemini", "gemini-flash", "dummy_gemini_key"),
    ]
    return p


def test_provider_availability_and_selection(pool):
    provider = pool.get_available_provider()
    assert provider is not None
    assert provider.name in ("test_groq", "test_gemini")


def test_rate_limit_cooldown_rotation(pool):
    # Mark first provider as rate limited
    pool.endpoints[0].mark_rate_limited(cooldown_seconds=30.0)
    assert pool.endpoints[0].is_available is False

    # Multiplexer should rotate to second provider
    next_provider = pool.get_available_provider()
    assert next_provider.name == "test_gemini"
    assert next_provider.is_available is True
