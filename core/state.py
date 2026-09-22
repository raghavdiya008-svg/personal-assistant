"""
Deterministic State Machine & Event Bus for Project JARVIS.
Handles asynchronous agent triggers, priority task queues, and state transitions.
"""

import asyncio
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger("JARVIS.State")


class EventBus:
    """Asynchronous publish-subscribe event bus."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, handler: Callable):
        """Register a callback for an event."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(handler)
        logger.debug(f"Subscribed handler to event '{event_name}'")

    async def emit(self, event_name: str, data: Any = None):
        """Trigger all handlers subscribed to an event."""
        logger.info(f"Event Emitted: [{event_name}]")
        if event_name in self._subscribers:
            tasks = []
            for handler in self._subscribers[event_name]:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(asyncio.create_task(handler(data)))
                else:
                    try:
                        handler(data)
                    except Exception as e:
                        logger.error(f"Sync handler for '{event_name}' failed: {e}", exc_info=True)
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(
                            f"Async handler #{i} for '{event_name}' failed: {result}",
                            exc_info=result
                        )



# Global Event Bus Instance
event_bus = EventBus()

# Standard System Events
EVENT_NEW_LEAD = "lead:new"
EVENT_MEETING_SCHEDULED = "meeting:scheduled"
EVENT_MEETING_WAKEUP = "meeting:wakeup"
EVENT_MEETING_COMPLETED = "meeting:completed"
EVENT_DEAL_WON = "deal:won"
EVENT_TELEGRAM_NOTIFY = "telegram:notify"
EVENT_CONTENT_TRIGGER = "content:trigger"
