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
# File: manager_workspace.py
# Description: Coordinates workspace model management, rendering, and persistence integration.
#============================================================================

from dataclasses import dataclass

from .controller import WorkspaceController
from .layout_model import PaneNode, SplitNode, WorkspaceModel
from .renderer import WorkspaceRenderer


@dataclass
class TabDragTransaction:
    source_pane_id: str
    source_window_id: str
    tool_id: str


class WorkspaceManager:
    def __init__(self, parent=None):
        self._windows = []
        self._drag_tx = None
        self._next_tool_number = 1
        self._default_plugin_manager = None
        self.model = WorkspaceModel()
        self.session_manager = None
        self.controller = WorkspaceController(self)
        self.renderer = WorkspaceRenderer(self)

    def register_window(self, window):
        if window not in self._windows:
            self._windows.append(window)
        if getattr(window, 'plugin_manager', None) is not None and self._default_plugin_manager is None:
            self._default_plugin_manager = window.plugin_manager
        self.model.register_window(window.window_id, is_primary=window.is_primary)

    def windows(self):
        return list(self._windows)

    def primary_window(self):
        for window in self._windows:
            if getattr(window, 'is_primary', False):
                return window
        return self._windows[0] if self._windows else None

    def promote_primary_window(self):
        if not self._windows:
            return None
        if any(getattr(window, 'is_primary', False) for window in self._windows):
            return self.primary_window()
        new_primary = self._windows[0]
        new_primary.is_primary = True
        return new_primary

    def unregister_window(self, window):
        if window in self._windows:
            self._windows.remove(window)
        self.model.unregister_window(window.window_id)

    def register_tool(self, widget, title, plugin_id="", tool_type_id="", tool_id=None):
        return self.model.register_tool(widget, title, plugin_id=plugin_id, tool_type_id=tool_type_id, tool_id=tool_id)

    def render_window(self, window):
        window_node = self.model.windows.get(window.window_id)
        if window_node is not None:
            self.model.normalize_window(window_node)
        self.renderer.render_window(window)
        self.renderer.cleanup_stale_panes()
        window.refresh_window_title()

    def render_all(self):
        for window in list(self._windows):
            window_node = self.model.windows.get(window.window_id)
            if window_node is not None:
                self.model.normalize_window(window_node)
            self.renderer.render_window(window)
        self.renderer.cleanup_stale_panes()
        for window in list(self._windows):
            window.refresh_window_title()
        self._cleanup_empty_detached_windows()

    def begin_drag(self, source_pane, index):
        tool = source_pane.widget_at(index)
        if tool is None:
            return None
        tool_id = source_pane.tool_id_at(index)
        if tool_id is None:
            return None
        self._drag_tx = TabDragTransaction(
            source_pane_id=source_pane.pane_id,
            source_window_id=source_pane.area.window_id,
            tool_id=tool_id,
        )
        return f"pane:{source_pane.pane_id}:tool:{tool_id}"

    def end_drag(self):
        self._drag_tx = None

    def add_tool_to_window(self, window, tool_id, target_pane_id=None):
        pane_id = self.controller.add_tool_to_window(window.window_id, tool_id, target_pane_id=target_pane_id)
        self.render_window(window)
        return pane_id

    def detach_drag_to_new_window(self, global_pos):
        if not self._drag_tx:
            return None
        source_window = self.window_by_id(self._drag_tx.source_window_id)
        if source_window is None:
            return None
        window = self.create_workspace_window(
            plugin_manager=getattr(source_window, 'plugin_manager', None),
            theme_name=getattr(source_window, 'current_theme_name', None),
            is_primary=False,
        )
        self.controller.detach_tool_to_new_window(
            self._drag_tx.source_pane_id,
            self._drag_tx.tool_id,
            window.window_id,
        )
        self.render_all()
        window.move(global_pos - window.rect().center())
        window.show()
        window.raise_()
        return window

    def drop_drag_on_pane(self, target_pane, zone):
        if not self._drag_tx:
            return None
        pane_id = self.controller.move_tool(
            self._drag_tx.source_pane_id,
            self._drag_tx.tool_id,
            target_pane.pane_id,
            zone,
        )
        self.render_all()
        return pane_id

    def close_tool_in_pane(self, pane_id, tool_id):
        window = self.model.find_window_for_pane(pane_id)
        ok = self.controller.close_tool(pane_id, tool_id)
        if ok and window:
            ui_window = self.window_by_id(window.window_id)
            if ui_window:
                self.render_window(ui_window)
            self._cleanup_empty_detached_windows()
        return ok

    def update_tool_title(self, tool_id, title):
        self.model.update_tool_title(tool_id, title)

    def tools_for_window(self, window_id):
        window = self.model.windows.get(window_id)
        if window is None:
            return []
        tools = []
        for pane in self.model.iter_panes(window.root_node):
            for tool_id in pane.tool_ids:
                record = self.model.tools.get(tool_id)
                if record is not None:
                    tools.append(record.widget)
        return tools

    def current_tool_for_window(self, window_id):
        window = self.model.windows.get(window_id)
        if window is None:
            return None
        for pane in self.model.iter_panes(window.root_node):
            if pane.active_tool_id:
                record = self.model.tools.get(pane.active_tool_id)
                if record is not None:
                    return record.widget
        return None

    def preferred_pane_id(self, window_id):
        window = self.model.windows.get(window_id)
        if window is None:
            return None
        for pane in self.model.iter_panes(window.root_node):
            if pane.tool_ids:
                return pane.pane_id
        for pane in self.model.iter_panes(window.root_node):
            return pane.pane_id
        return None

    def window_by_id(self, window_id):
        for window in self._windows:
            if window.window_id == window_id:
                return window
        return None

    def create_workspace_window(self, plugin_manager=None, theme_name=None, is_primary=False):
        from nexus_workspace.workspace.workspace_window import WorkspaceWindow

        plugin_manager = plugin_manager or self._default_plugin_manager
        window = WorkspaceWindow(self, plugin_manager=plugin_manager, session_manager=self.session_manager, is_primary=is_primary)
        if theme_name:
            window.apply_theme(theme_name)
        window.resize(1200, 800)
        return window

    def _cleanup_empty_detached_windows(self):
        open_windows = list(self._windows)
        if len(open_windows) <= 1:
            return
        empty_windows = [window for window in open_windows if not self.tools_for_window(window.window_id)]
        windows_to_keep = 1 if len(empty_windows) >= len(open_windows) else 0
        for window in empty_windows:
            if windows_to_keep > 0:
                windows_to_keep -= 1
                continue
            window.close()



    def capture_live_layout(self):
        for window in list(self._windows):
            window_node = self.model.windows.get(window.window_id)
            if window_node is None:
                continue
            if hasattr(window, 'isMaximized') and not window.isMaximized():
                window_node.geometry = window.geometry()
            root_widget = getattr(getattr(window, 'workspace_area', None), '_root_widget', None)
            if root_widget is not None:
                self._capture_splitter_sizes(window_node.root_node, root_widget)

    def _capture_splitter_sizes(self, model_node, widget):
        if isinstance(model_node, SplitNode) and hasattr(widget, 'sizes'):
            try:
                model_node.sizes = list(widget.sizes())
            except Exception:
                model_node.sizes = []
            for child_node, child_widget in zip(model_node.children, [widget.widget(i) for i in range(widget.count())]):
                self._capture_splitter_sizes(child_node, child_widget)

    def reset_model(self):
        self.model = WorkspaceModel()
        self.session_manager = None
        self.controller.model = self.model

    def restore_from_state(self, primary_window, state, state_manager):
        for window in list(self._windows):
            if window is not primary_window:
                window.close()
        self._windows = [primary_window]
        self.reset_model()
        self.register_window(primary_window)

        session_state = state.get('session') or {}
        self._next_tool_number = session_state.get('next_tool_number', 1)
        platform_state = state.get('platform') or {}
        theme_pref = (((platform_state.get('preferences') or {}).get('theme') or {}).get('current'))
        window_states = session_state.get('windows', [])
        primary_state = next((item for item in window_states if item.get('is_primary')), window_states[0] if window_states else None)
        detached_states = [item for item in window_states if item is not primary_state]

        if primary_state is not None:
            self._restore_window(primary_window, primary_state, state_manager)

        for window_state in detached_states:
            window = self.create_workspace_window(
                plugin_manager=getattr(primary_window, 'plugin_manager', None),
                theme_name=window_state.get('theme_name', window_state.get('current_theme_name', theme_pref or getattr(primary_window, 'current_theme_name', 'Midnight'))),
                is_primary=False,
            )
            self._restore_window(window, window_state, state_manager)
            window.show()

        self.render_all()

    def _restore_window(self, window, window_state, state_manager):
        root_node = state_manager.deserialize_layout_node(window_state.get('root_node'))
        self.model.windows[window.window_id].root_node = root_node
        self.model.normalize_window(self.model.windows[window.window_id])
        theme_name = window_state.get('theme_name', window_state.get('current_theme_name'))
        if theme_name:
            window.apply_theme(theme_name)
        for tool_state in window_state.get('tools', []):
            descriptor = getattr(window, 'plugin_manager', None).descriptor_for_tool(tool_state.get('tool_type_id')) if getattr(window, 'plugin_manager', None) else None
            if descriptor is None:
                continue
            title = tool_state.get('title') or descriptor.display_name
            plugin_context = getattr(getattr(window, 'plugin_manager', None), 'context', None)
            tool = descriptor.create_instance(parent=window, theme_name=getattr(window, 'current_theme_name', 'Midnight'), editor_title=title, plugin_context=plugin_context)
            tool._nexus_plugin_display_name = descriptor.display_name
            tool._nexus_instance_name = title
            tool._nexus_tool_type_id = descriptor.tool_type_id
            tool._nexus_plugin_id = descriptor.plugin_id
            if hasattr(tool, 'setWindowTitle'):
                tool.setWindowTitle(title)
            if hasattr(tool, 'load_state'):
                try:
                    tool.load_state(tool_state.get('state') or {})
                except Exception:
                    pass
            window.workspace_area.add_tool(
                tool,
                title,
                target_pane=tool_state.get('pane_id'),
                tool_id=tool_state.get('tool_id'),
                plugin_id=descriptor.plugin_id,
                tool_type_id=descriptor.tool_type_id,
            )
        geometry = window_state.get('geometry') or {}
        if geometry:
            window.setGeometry(geometry.get('x', window.x()), geometry.get('y', window.y()), geometry.get('width', window.width()), geometry.get('height', window.height()))
            if geometry.get('maximized'):
                window.showMaximized()

    def make_next_tool_title(self, base_name="Tool"):
        title = "%s %s" % (base_name, self._next_tool_number)
        self._next_tool_number += 1
        return title
