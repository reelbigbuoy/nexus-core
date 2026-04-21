# ============================================================================
#
#
# Copyright (c) 2026 Reel Big Buoy Company
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Nexus Core
# File: events.py
# Description: Defines the event bus and utilities for publishing and subscribing to application events.
#============================================================================

from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, List, Optional


class EventBus:
    """Simple in-process publish/subscribe event bus for Nexus platform services."""

    def __init__(self, data_store=None, max_history: int = 200):
        self._subscribers: DefaultDict[str, List[Callable]] = defaultdict(list)
        self._global_subscribers: List[Callable] = []
        self._data_store = data_store
        self._max_history = max(10, int(max_history or 200))
        self._recent_events: List[Dict] = []

    def set_data_store(self, data_store):
        self._data_store = data_store
        self._publish_diagnostics()

    def subscribe(self, event_type: str, callback: Callable):
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
        self._publish_diagnostics()
        return callback

    def unsubscribe(self, event_type: str, callback: Callable):
        callbacks = self._subscribers.get(event_type, [])
        if callback in callbacks:
            callbacks.remove(callback)
        if not callbacks and event_type in self._subscribers:
            self._subscribers.pop(event_type, None)
        self._publish_diagnostics()

    def subscribe_all(self, callback: Callable):
        if callback not in self._global_subscribers:
            self._global_subscribers.append(callback)
        self._publish_diagnostics()
        return callback

    def unsubscribe_all(self, callback: Callable):
        if callback in self._global_subscribers:
            self._global_subscribers.remove(callback)
        self._publish_diagnostics()

    def publish(self, event_type: str, payload: Optional[Dict] = None):
        payload = payload or {}
        envelope = {
            'event_type': event_type,
            'payload': payload,
        }
        for callback in list(self._subscribers.get(event_type, [])):
            callback(payload)
        for callback in list(self._global_subscribers):
            callback(envelope)
        self._append_event(event_type, payload)

    def recent_events(self) -> List[Dict]:
        return list(self._recent_events)

    def _safe_value(self, value: Any, *, depth: int = 0, max_depth: int = 4, seen=None):
        if seen is None:
            seen = set()
        if id(value) in seen:
            return '<circular>'
        if depth > max_depth:
            return '<max_depth>'
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        seen.add(id(value))
        try:
            if isinstance(value, dict):
                items = list(value.items())
                limited = items[:25]
                safe = {str(key): self._safe_value(item, depth=depth + 1, max_depth=max_depth, seen=seen) for key, item in limited}
                if len(items) > len(limited):
                    safe['<truncated>'] = f'{len(items) - len(limited)} more entries'
                return safe
            if isinstance(value, (list, tuple, set)):
                items = list(value)
                limited = items[:25]
                safe = [self._safe_value(item, depth=depth + 1, max_depth=max_depth, seen=seen) for item in limited]
                if len(items) > len(limited):
                    safe.append(f'<truncated {len(items) - len(limited)} more items>')
                return safe
        finally:
            seen.discard(id(value))

        return f'<{type(value).__name__}>'

    def _diagnostic_payload(self, event_type: str, payload: Optional[Dict]) -> Dict:
        payload = payload or {}
        if event_type == 'data.changed' and isinstance(payload, dict):
            value = payload.get('value')
            return {
                'key': payload.get('key'),
                'removed': bool(payload.get('removed', False)),
                'value_type': type(value).__name__,
                'value_preview': self._safe_value(value, max_depth=2),
            }
        return self._safe_value(payload)


    def diagnostics_snapshot(self) -> Dict:
        subscriber_counts = {event_type: len(callbacks) for event_type, callbacks in self._subscribers.items()}
        return {
            'contract': 'platform.event_bus.v1',
            'subscriber_counts': dict(sorted(subscriber_counts.items())),
            'global_subscriber_count': len(self._global_subscribers),
            'recent_events': self.recent_events(),
        }

    def _append_event(self, event_type: str, payload: Optional[Dict]):
        self._recent_events.append({
            'event_type': event_type,
            'payload': self._diagnostic_payload(event_type, payload),
        })
        if len(self._recent_events) > self._max_history:
            self._recent_events = self._recent_events[-self._max_history:]
        self._publish_diagnostics()

    def _publish_diagnostics(self):
        if self._data_store is None:
            return
        try:
            snapshot = self.diagnostics_snapshot()
            self._data_store.set('platform.event_bus', snapshot, publish_event=False)
            self._data_store.set('platform.events.recent', snapshot.get('recent_events', []), publish_event=False)
        except Exception:
            pass