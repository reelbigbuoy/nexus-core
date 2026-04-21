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
# File: context_service.py
# Description: Stores and resolves shared application context for tools, panes, and services.
#============================================================================

from __future__ import annotations

from typing import Any

from .context_contract import (
    CONTEXT_ACTIVE_TOOL_KEY,
    CONTEXT_INSPECTABLE_TARGET_KEY,
    CONTEXT_REGISTRY_KEY,
    build_active_tool_context,
    build_context_registry,
    build_inspectable_target_context,
)
from .selection_contract import SELECTION_CURRENT_KEY


class ContextResolver:
    """Derives normalized platform context from active runtime state."""

    def __init__(self, data_store=None, event_bus=None):
        self.data_store = data_store
        self.event_bus = event_bus
        self._selection_subscription = None
        self._active_tool_subscription = None
        self._connect()
        self._publish_registry()
        self._recompute_inspectable_target()

    def _connect(self):
        if self.data_store is None:
            return
        if self._selection_subscription is None:
            self._selection_subscription = self.data_store.subscribe(SELECTION_CURRENT_KEY, self._on_selection_changed)
        if self._active_tool_subscription is None:
            self._active_tool_subscription = self.data_store.subscribe(CONTEXT_ACTIVE_TOOL_KEY, self._on_active_tool_changed)

    def publish_active_tool(self, tool: Any, *, window=None):
        if self.data_store is None:
            return None
        if tool is None:
            self.data_store.set(CONTEXT_ACTIVE_TOOL_KEY, None, publish_event=False)
            self._recompute_inspectable_target()
            return None
        payload = build_active_tool_context(
            tool_id=getattr(tool, '_nexus_tool_id', None),
            tool_type_id=getattr(tool, '_nexus_tool_type_id', None),
            tool_title=getattr(tool, '_nexus_instance_name', None) or getattr(tool, 'windowTitle', lambda: None)(),
            plugin_id=getattr(tool, '_nexus_plugin_id', None),
            plugin_display_name=getattr(tool, '_nexus_plugin_display_name', None),
            window_id=getattr(window, 'window_id', None),
            workspace_id=getattr(window, 'window_id', None),
        )
        self.data_store.set(CONTEXT_ACTIVE_TOOL_KEY, payload, publish_event=False)
        self._recompute_inspectable_target()
        return payload

    def clear_active_tool(self):
        if self.data_store is None:
            return
        self.data_store.set(CONTEXT_ACTIVE_TOOL_KEY, None, publish_event=False)
        self._recompute_inspectable_target()

    def _on_selection_changed(self, _payload):
        self._recompute_inspectable_target()

    def _on_active_tool_changed(self, _payload):
        self._recompute_inspectable_target()

    def _recompute_inspectable_target(self):
        if self.data_store is None:
            return None
        payload = build_inspectable_target_context(
            selection=self.data_store.get(SELECTION_CURRENT_KEY),
            active_tool=self.data_store.get(CONTEXT_ACTIVE_TOOL_KEY),
        )
        self.data_store.set(CONTEXT_INSPECTABLE_TARGET_KEY, payload, publish_event=False)
        return payload

    def _publish_registry(self):
        if self.data_store is None:
            return
        self.data_store.set(CONTEXT_REGISTRY_KEY, build_context_registry(), publish_event=False)