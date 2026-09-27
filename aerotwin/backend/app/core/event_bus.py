"""
Event Bus
Simple publish-subscribe event system for decoupling modules.
"""
from typing import Callable
from collections import defaultdict


class EventBus:
    """Simple in-process pub/sub event bus."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable):
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: str, data: dict = None):
        for callback in self._subscribers.get(event_type, []):
            try:
                callback(data or {})
            except Exception as e:
                print(f"[EventBus] Error in handler for {event_type}: {e}")

    def clear(self):
        self._subscribers.clear()
