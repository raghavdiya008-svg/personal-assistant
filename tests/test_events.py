"""Unit tests for EventBus."""

import pytest
import asyncio
from core.state import EventBus


@pytest.mark.asyncio
async def test_event_bus_sync_and_async_handlers():
    bus = EventBus()
    received_sync = []
    received_async = []

    def sync_handler(data):
        received_sync.append(data)

    async def async_handler(data):
        await asyncio.sleep(0.01)
        received_async.append(data)

    bus.subscribe("test:event", sync_handler)
    bus.subscribe("test:event", async_handler)

    await bus.emit("test:event", {"msg": "hello"})

    assert len(received_sync) == 1
    assert received_sync[0]["msg"] == "hello"
    assert len(received_async) == 1
    assert received_async[0]["msg"] == "hello"


@pytest.mark.asyncio
async def test_event_bus_handles_exception_gracefully():
    bus = EventBus()
    recovered = []

    def broken_handler(data):
        raise ValueError("Handler explosion!")

    def good_handler(data):
        recovered.append(data)

    bus.subscribe("test:fail", broken_handler)
    bus.subscribe("test:fail", good_handler)

    # Should not raise exception to the caller
    await bus.emit("test:fail", {"status": "ok"})
    assert len(recovered) == 1
