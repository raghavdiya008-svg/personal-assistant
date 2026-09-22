"""Unit tests for Cognitive Cascade Brain."""

import pytest
from core.brain import CognitiveBrain


@pytest.mark.asyncio
async def test_brain_reflex():
    brain = CognitiveBrain()
    reply = await brain.reflex("Test greeting")
    assert isinstance(reply, str)
    assert len(reply) > 0


@pytest.mark.asyncio
async def test_brain_reason():
    brain = CognitiveBrain()
    reply = await brain.reason("Provide a 1-sentence sales pitch for an AI software.")
    assert isinstance(reply, str)
    assert len(reply) > 0


def test_brain_classify_task():
    brain = CognitiveBrain()
    assert brain.classify_task("hello, what is the price?") == "FAST"
    assert brain.classify_task("analyze this client contract and plan our negotiation strategy") == "DEEP"
    assert brain.classify_task("extract json parameters from this message") == "DEEP"


@pytest.mark.asyncio
async def test_brain_auto_routing():
    brain = CognitiveBrain()
    reply = await brain.auto("What is your price?")
    assert isinstance(reply, str)
    assert len(reply) > 0

