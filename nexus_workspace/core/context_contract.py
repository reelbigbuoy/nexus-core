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
# File: context_contract.py
# Description: Defines workspace context payloads and helpers for normalized context objects.
#============================================================================

from __future__ import annotations

from typing import Any, Dict, Optional

from .inspectable_contract import normalize_inspectable_object
from .data_model import data_model_to_inspectable
from .selection_contract import normalize_selection_payload

CONTEXT_ACTIVE_TOOL_KEY = 'context.active_tool'
CONTEXT_INSPECTABLE_TARGET_KEY = 'context.inspectable_target'
CONTEXT_REGISTRY_KEY = 'platform.context_registry'

CONTEXT_ACTIVE_TOOL_CONTRACT = 'context.active_tool.v1'
CONTEXT_INSPECTABLE_TARGET_CONTRACT = 'context.inspectable_target.v1'
CONTEXT_REGISTRY_CONTRACT = 'platform.context_registry.v1'


def _string_or_none(value: Any) -> Optional[str]:
    if value in (None, ''):
        return None
    return str(value)


def build_active_tool_context(*, tool_id: Any = None, tool_type_id: Any = None, tool_title: Any = None, plugin_id: Any = None, plugin_display_name: Any = None, window_id: Any = None, workspace_id: Any = None) -> Dict[str, Any]:
    return {
        'contract': CONTEXT_ACTIVE_TOOL_CONTRACT,
        'tool_id': _string_or_none(tool_id),
        'tool_type_id': _string_or_none(tool_type_id),
        'tool_title': _string_or_none(tool_title),
        'plugin_id': _string_or_none(plugin_id),
        'plugin_display_name': _string_or_none(plugin_display_name),
        'window_id': _string_or_none(window_id),
        'workspace_id': _string_or_none(workspace_id) or _string_or_none(window_id),
    }


def normalize_active_tool_context(payload: Any):
    if payload in (None, False):
        return None
    if not isinstance(payload, dict):
        return None
    return build_active_tool_context(
        tool_id=payload.get('tool_id'),
        tool_type_id=payload.get('tool_type_id'),
        tool_title=payload.get('tool_title'),
        plugin_id=payload.get('plugin_id'),
        plugin_display_name=payload.get('plugin_display_name'),
        window_id=payload.get('window_id'),
        workspace_id=payload.get('workspace_id'),
    )


def build_inspectable_target_context(*, selection: Any = None, active_tool: Any = None) -> Optional[Dict[str, Any]]:
    normalized_selection = normalize_selection_payload(selection)
    normalized_active_tool = normalize_active_tool_context(active_tool)
    if normalized_selection is None:
        return None
    metadata = normalized_selection.get('metadata') or {}
    inspectable = normalize_inspectable_object(metadata.get('inspectable'))
    if inspectable is None:
        inspectable = data_model_to_inspectable(metadata.get('data_model'))
    return {
        'contract': CONTEXT_INSPECTABLE_TARGET_CONTRACT,
        'selection': normalized_selection,
        'inspectable': inspectable,
        'active_tool': normalized_active_tool,
        'target_id': normalized_selection.get('id'),
        'target_kind': normalized_selection.get('kind'),
        'display_name': normalized_selection.get('display_name'),
        'source': dict(normalized_selection.get('source') or {}),
    }


def build_context_registry() -> Dict[str, Any]:
    return {
        'contract': CONTEXT_REGISTRY_CONTRACT,
        'contexts': [
            {
                'key': CONTEXT_ACTIVE_TOOL_KEY,
                'contract': CONTEXT_ACTIVE_TOOL_CONTRACT,
                'description': 'Current active tool context for the focused workspace tool.',
                'derived_from': ['workspace.activeToolChanged', 'window focus'],
            },
            {
                'key': CONTEXT_INSPECTABLE_TARGET_KEY,
                'contract': CONTEXT_INSPECTABLE_TARGET_CONTRACT,
                'description': 'Derived inspectable target context composed from canonical selection and active tool state.',
                'derived_from': ['selection.current', CONTEXT_ACTIVE_TOOL_KEY],
            },
        ],
    }