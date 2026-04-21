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
# File: state_contract.py
# Description: Defines normalized contracts for persisted workspace and window state payloads.
#============================================================================

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

PERSISTED_STATE_CONTRACT = "platform.persisted_state.v2"
WORKSPACE_WINDOW_STATE_CONTRACT = "workspace.window_state.v1"
PLUGIN_TOOL_STATE_CONTRACT = "plugin.tool_state.v1"
STATE_TAXONOMY_CONTRACT = "platform.state_taxonomy.v1"


@dataclass(frozen=True)
class PluginToolStateEnvelope:
    plugin_id: str
    tool_type_id: str
    tool_id: str
    title: str
    pane_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    contract: str = PLUGIN_TOOL_STATE_CONTRACT
    scope: str = "plugin.instance"
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            'contract': self.contract,
            'scope': self.scope,
            'version': self.version,
            'plugin_id': self.plugin_id,
            'tool_type_id': self.tool_type_id,
            'tool_id': self.tool_id,
            'title': self.title,
            'pane_id': self.pane_id,
            'state': dict(self.state or {}),
        }


@dataclass(frozen=True)
class WorkspaceWindowStateEnvelope:
    window_id: str
    is_primary: bool
    geometry: Dict[str, Any]
    theme_name: str
    root_node: Dict[str, Any]
    tools: List[PluginToolStateEnvelope] = field(default_factory=list)
    contract: str = WORKSPACE_WINDOW_STATE_CONTRACT
    scope: str = "workspace.session"
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            'contract': self.contract,
            'scope': self.scope,
            'version': self.version,
            'window_id': self.window_id,
            'is_primary': self.is_primary,
            'geometry': dict(self.geometry or {}),
            'theme_name': self.theme_name,
            'root_node': dict(self.root_node or {}),
            'tools': [tool.to_dict() if hasattr(tool, 'to_dict') else dict(tool) for tool in self.tools],
        }


def build_plugin_tool_state(*, plugin_id: str, tool_type_id: str, tool_id: str, title: str, pane_id: str, state: Optional[Dict[str, Any]] = None, version: int = 1) -> PluginToolStateEnvelope:
    return PluginToolStateEnvelope(
        plugin_id=plugin_id,
        tool_type_id=tool_type_id,
        tool_id=tool_id,
        title=title,
        pane_id=pane_id,
        state=dict(state or {}),
        version=version,
    )


def build_workspace_window_state(*, window_id: str, is_primary: bool, geometry: Optional[Dict[str, Any]] = None, theme_name: str = 'Midnight', root_node: Optional[Dict[str, Any]] = None, tools: Optional[List[PluginToolStateEnvelope]] = None, version: int = 1) -> WorkspaceWindowStateEnvelope:
    return WorkspaceWindowStateEnvelope(
        window_id=window_id,
        is_primary=bool(is_primary),
        geometry=dict(geometry or {}),
        theme_name=theme_name,
        root_node=dict(root_node or {}),
        tools=list(tools or []),
        version=version,
    )


def build_state_taxonomy() -> Dict[str, Any]:
    return {
        'contract': STATE_TAXONOMY_CONTRACT,
        'categories': [
            {
                'name': 'platform.preferences',
                'scope': 'application.persisted',
                'description': 'User-facing preferences that should survive across launches, such as theme selection.',
                'examples': ['platform.preferences.theme.current'],
            },
            {
                'name': 'platform.runtime',
                'scope': 'application.runtime',
                'description': 'Live runtime metadata published by the platform for diagnostics and discovery.',
                'examples': ['platform.plugin_registry', 'platform.state_taxonomy'],
            },
            {
                'name': 'session',
                'scope': 'session.persisted',
                'description': 'State for the current Nexus session, including open workspaces and layout composition.',
                'examples': ['session.windows', 'session.next_tool_number'],
            },
            {
                'name': 'workspace',
                'scope': 'workspace.persisted',
                'description': 'Per-workspace window geometry, theme shell state, and dock layout.',
                'examples': ['workspace.window_state.v1'],
            },
            {
                'name': 'plugin.instance',
                'scope': 'plugin.persisted',
                'description': 'Per-tool-instance serialized state owned by a plugin and restored by that plugin.',
                'examples': ['plugin.tool_state.v1'],
            },
            {
                'name': 'shared.read_model',
                'scope': 'runtime.shared',
                'description': 'Canonical shared read-side data published into the DataStore for cross-plugin coordination.',
                'examples': ['selection.current', 'platform.plugins'],
            },
            {
                'name': 'plugin.private.runtime',
                'scope': 'runtime.private',
                'description': 'Ephemeral plugin-local state that should stay inside plugin objects and not be persisted in the shared store.',
                'examples': ['transient selections, drag operations, temporary UI state'],
            },
        ],
    }


def normalize_persisted_state(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = dict(payload or {})
    if payload.get('contract') == PERSISTED_STATE_CONTRACT:
        return payload
    # Backward compatibility for the older flat workspace_state.json structure.
    windows = []
    for item in payload.get('windows', []) or []:
        normalized_item = dict(item)
        if 'theme_name' not in normalized_item and 'current_theme_name' in normalized_item:
            normalized_item['theme_name'] = normalized_item.get('current_theme_name')
        tool_payloads = []
        for tool in normalized_item.get('tools', []) or []:
            wrapped = dict(tool)
            wrapped.setdefault('contract', PLUGIN_TOOL_STATE_CONTRACT)
            wrapped.setdefault('scope', 'plugin.instance')
            wrapped.setdefault('version', 1)
            tool_payloads.append(wrapped)
        normalized_item['tools'] = tool_payloads
        normalized_item.setdefault('contract', WORKSPACE_WINDOW_STATE_CONTRACT)
        normalized_item.setdefault('scope', 'workspace.session')
        normalized_item.setdefault('version', 1)
        windows.append(normalized_item)
    platform_in = payload.get('platform') or {}
    prefs_in = platform_in.get('preferences') or {}
    shortcut_bindings = (((prefs_in.get('shortcuts') or {}).get('bindings') or {}) if isinstance(prefs_in, dict) else {})
    preferences = {
        'theme': {
            'current': ((prefs_in.get('theme') or {}).get('current') if isinstance(prefs_in.get('theme') or {}, dict) else None) or (windows[0].get('theme_name') if windows else None) or 'Midnight',
        },
        'shortcuts': {
            'bindings': dict(shortcut_bindings or {}),
        },
        'plugins': {
            'enabled': dict((((prefs_in.get('plugins') or {}).get('enabled') or {}) if isinstance(prefs_in.get('plugins') or {}, dict) else {}) or {}),
        },
    }
    return {
        'contract': PERSISTED_STATE_CONTRACT,
        'version': 2,
        'platform': {
            'preferences': preferences,
        },
        'session': {
            'next_tool_number': payload.get('next_tool_number', 1),
            'windows': windows,
        },
    }
