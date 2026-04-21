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
# File: data_store.py
# Description: Provides lightweight in-memory storage primitives for shared application data.
#============================================================================

from .selection_contract import SELECTION_CURRENT_KEY
from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, List


class DataStore:
    """Shared observable key/value store for cross-plugin coordination."""

    def __init__(self, event_bus=None):
        self._values: Dict[str, Any] = {}
        self._subscribers: DefaultDict[str, List[Callable]] = defaultdict(list)
        self._global_subscribers: List[Callable] = []
        self._event_bus = event_bus

    def set(self, key: str, value: Any, publish_event: bool = True):
        self._values[key] = value
        self._notify(key, value, publish_event=publish_event)

    def get(self, key: str, default=None):
        return self._values.get(key, default)


    def set_selection_current(self, payload: Any):
        """Set the canonical shared selection payload."""
        self.set(SELECTION_CURRENT_KEY, payload)

    def get_selection_current(self, default=None):
        """Get the canonical shared selection payload."""
        return self.get(SELECTION_CURRENT_KEY, default)

    def remove(self, key: str):
        if key in self._values:
            self._values.pop(key, None)
            self._notify(key, None, removed=True)

    def clear(self):
        keys = list(self._values.keys())
        self._values.clear()
        for key in keys:
            self._notify(key, None, removed=True)

    def subscribe(self, key: str, callback: Callable):
        if callback not in self._subscribers[key]:
            self._subscribers[key].append(callback)
        return callback

    def unsubscribe(self, key: str, callback: Callable):
        callbacks = self._subscribers.get(key, [])
        if callback in callbacks:
            callbacks.remove(callback)
        if not callbacks and key in self._subscribers:
            self._subscribers.pop(key, None)

    def subscribe_all(self, callback: Callable):
        if callback not in self._global_subscribers:
            self._global_subscribers.append(callback)
        return callback

    def unsubscribe_all(self, callback: Callable):
        if callback in self._global_subscribers:
            self._global_subscribers.remove(callback)

    def keys(self):
        return list(self._values.keys())

    def items(self):
        return list(self._values.items())

    def snapshot(self) -> Dict[str, Any]:
        return dict(self._values)

    def _notify(self, key: str, value: Any, removed: bool = False, publish_event: bool = True):
        payload = {
            'key': key,
            'value': value,
            'removed': removed,
            'snapshot': self.snapshot(),
        }
        for callback in list(self._subscribers.get(key, [])):
            callback(value)
        for callback in list(self._global_subscribers):
            callback(payload)
        if publish_event and self._event_bus is not None:
            try:
                self._event_bus.publish('data.changed', payload)
            except Exception:
                pass