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
# File: action_requests.py
# Description: Provides helpers for creating and publishing standardized action requests.
#============================================================================

from __future__ import annotations

from typing import Any, Dict, Optional

from .action_contract import PROPERTY_EDIT_REQUEST, build_action_request

ACTION_REQUEST_EVENT = "action.requested"


def build_property_edit_request(*, target_selection: Optional[Dict[str, Any]], field_path: str, value: Any, source: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    selection = target_selection or {}
    selection_source = selection.get("source") if isinstance(selection, dict) else {}
    return build_action_request(
        action_type=PROPERTY_EDIT_REQUEST,
        target={
            "selection_id": selection.get("id") if isinstance(selection, dict) else None,
            "selection_kind": selection.get("kind") if isinstance(selection, dict) else None,
            "selection_contract": selection.get("contract") if isinstance(selection, dict) else None,
            "source_plugin": (selection_source or {}).get("plugin_id") if isinstance(selection_source, dict) else None,
            "source_tool_id": (selection_source or {}).get("tool_id") if isinstance(selection_source, dict) else None,
            "field_path": str(field_path or ""),
        },
        payload={
            "value": value,
        },
        source=dict(source or {}),
    )


class ActionRequestPublisher:
    """Publish user-intent requests onto the shared EventBus.

    This is the first step toward an enterprise mutation pipeline: widgets and
    platform tools can request a change without directly mutating another
    plugin's domain objects.
    """

    def __init__(self, plugin_context=None, source_tool=None, source_plugin_id: Optional[str] = None):
        self.plugin_context = plugin_context
        self.source_tool = source_tool
        self.source_plugin_id = source_plugin_id

    def request_property_edit(self, *, target_selection: Optional[Dict[str, Any]], field_path: str, value: Any) -> Dict[str, Any]:
        payload = build_property_edit_request(
            target_selection=target_selection,
            field_path=field_path,
            value=value,
            source=self._build_source(),
        )
        if self.plugin_context is not None and hasattr(self.plugin_context, 'publish_action_request'):
            self.plugin_context.publish_action_request(payload)
        else:
            event_bus = getattr(self.plugin_context, "event_bus", None) if self.plugin_context is not None else None
            if event_bus is not None:
                event_bus.publish(ACTION_REQUEST_EVENT, payload)
        return payload

    def _build_source(self) -> Dict[str, Any]:
        tool = self.source_tool
        tool_title = None
        tool_id = None
        if tool is not None:
            if hasattr(tool, "editor_title"):
                try:
                    tool_title = tool.editor_title()
                except Exception:
                    tool_title = None
            if not tool_title and hasattr(tool, "windowTitle"):
                try:
                    tool_title = tool.windowTitle()
                except Exception:
                    tool_title = None
            if hasattr(tool, "objectName"):
                try:
                    tool_id = tool.objectName() or None
                except Exception:
                    tool_id = None
            if not tool_id:
                tool_id = f"{tool.__class__.__name__}:{id(tool)}"
        return {
            "plugin_id": self.source_plugin_id,
            "tool_id": tool_id,
            "tool_title": tool_title,
        }