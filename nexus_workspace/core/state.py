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
# File: state.py
# Description: Coordinates persistence and restoration of workspace state and application layout data.
#============================================================================

import json
from pathlib import Path
from typing import Any, Dict, Optional

from nexus_workspace.framework.qt import QtCore

from .serialization import NexusSerializable
from .state_contract import build_plugin_tool_state, build_workspace_window_state, normalize_persisted_state
from ..workspace.layout_model import PaneNode, SplitNode


class StateManager(NexusSerializable):
    """Coordinates application and workspace persistence for Nexus."""

    STATE_VERSION = 2

    def __init__(self, app_name: str = 'Nexus'):
        self.app_name = app_name

    def state_file_path(self) -> Path:
        root = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.AppConfigLocation))
        if not root:
            root = Path.home() / '.nexus'
        root.mkdir(parents=True, exist_ok=True)
        return root / 'workspace_state.json'

    def save_to_disk(self, main_window) -> Path:
        state = self.save_workspace_state(main_window)
        path = self.state_file_path()
        path.write_text(json.dumps(state, indent=2), encoding='utf-8')
        return path

    def load_from_disk(self) -> Optional[Dict[str, Any]]:
        path = self.state_file_path()
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
            return normalize_persisted_state(raw)
        except Exception:
            return None

    def save_workspace_state(self, main_window) -> Dict[str, Any]:
        workspace_manager = main_window.workspace_manager
        workspace_manager.capture_live_layout()
        windows = []
        for window in list(workspace_manager._windows):
            window_node = workspace_manager.model.windows.get(window.window_id)
            if window_node is None:
                continue
            windows.append(build_workspace_window_state(
                window_id=window.window_id,
                is_primary=bool(window.is_primary),
                geometry=self._serialize_geometry(window),
                theme_name=getattr(window, 'current_theme_name', 'Midnight'),
                root_node=self._serialize_layout_node(window_node.root_node),
                tools=self._serialize_tools_for_window(workspace_manager, window),
            ).to_dict())
        primary_theme = getattr(main_window, 'current_theme_name', 'Midnight')
        command_service = getattr(main_window, 'command_service', None)
        shortcut_bindings = command_service.shortcut_bindings() if command_service is not None else {}
        return {
            'contract': 'platform.persisted_state.v2',
            'version': self.STATE_VERSION,
            'platform': {
                'preferences': {
                    'theme': {
                        'current': primary_theme,
                    },
                    'shortcuts': {
                        'bindings': dict(shortcut_bindings or {}),
                    },
                    'recent': {
                        'entries': list(getattr(main_window, '_recent_entries', []) or []),
                    },
                    'plugins': {
                        'enabled': dict(getattr(main_window, '_plugin_enablement_overrides', {}) or {}),
                    },
                },
            },
            'session': {
                'next_tool_number': getattr(workspace_manager, '_next_tool_number', 1),
                'windows': windows,
            },
        }

    def restore_workspace_state(self, main_window, state: Dict[str, Any]) -> bool:
        normalized = normalize_persisted_state(state)
        session = normalized.get('session') or {}
        if not normalized or not session.get('windows'):
            return False
        workspace_manager = main_window.workspace_manager
        workspace_manager.restore_from_state(main_window, normalized, self)
        return True

    def _serialize_geometry(self, window) -> Dict[str, Any]:
        geom = window.geometry()
        return {
            'x': geom.x(),
            'y': geom.y(),
            'width': geom.width(),
            'height': geom.height(),
            'maximized': bool(window.isMaximized()),
        }

    def _serialize_tools_for_window(self, workspace_manager, window):
        tools = []
        window_node = workspace_manager.model.windows.get(window.window_id)
        if window_node is None:
            return tools
        for pane in workspace_manager.model.iter_panes(window_node.root_node):
            for tool_id in pane.tool_ids:
                record = workspace_manager.model.tools.get(tool_id)
                if record is None:
                    continue
                widget = record.widget
                widget_state = widget.save_state() if hasattr(widget, 'save_state') else {}
                tools.append(build_plugin_tool_state(
                    plugin_id=record.plugin_id,
                    tool_type_id=record.tool_type_id,
                    tool_id=tool_id,
                    title=record.title,
                    pane_id=pane.pane_id,
                    state=widget_state or {},
                ))
        return tools

    def _serialize_layout_node(self, node):
        if isinstance(node, PaneNode):
            return {
                'type': 'pane',
                'pane_id': node.pane_id,
                'tool_ids': list(node.tool_ids),
                'active_tool_id': node.active_tool_id,
            }
        if isinstance(node, SplitNode):
            return {
                'type': 'split',
                'split_id': node.node_id,
                'orientation': node.orientation,
                'sizes': list(node.sizes or []),
                'children': [self._serialize_layout_node(child) for child in node.children],
            }
        return {'type': 'pane', 'pane_id': 'pane_fallback', 'tool_ids': [], 'active_tool_id': None}

    def deserialize_layout_node(self, payload):
        if not payload:
            return PaneNode()
        if payload.get('type') == 'split':
            node = SplitNode(payload.get('orientation', 'horizontal'), sizes=payload.get('sizes', []), split_id=payload.get('split_id'))
            for child_payload in payload.get('children', []):
                node.add_child(self.deserialize_layout_node(child_payload))
            return node
        return PaneNode(
            pane_id=payload.get('pane_id'),
            tool_ids=list(payload.get('tool_ids', [])),
            active_tool_id=payload.get('active_tool_id'),
        )
