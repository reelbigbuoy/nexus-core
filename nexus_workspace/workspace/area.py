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
# File: area.py
# Description: Defines the workspace area widget that hosts rendered panes and docking layouts.
#============================================================================

from nexus_workspace.framework.qt import QtCore, QtWidgets

from ..plugins.base import reset_tool_theme
from .pane import WorkspacePane


class WorkspaceArea(QtWidgets.QWidget):
    activeToolChanged = QtCore.pyqtSignal(object)

    def __init__(self, manager, window, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.window = window
        self.window_id = window.window_id
        self.setObjectName("WorkspaceArea")

        self._root_widget = None
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def _set_root_widget(self, widget):
        if self._root_widget is widget:
            return

        old_root = self._root_widget
        self._root_widget = widget

        if widget is not None and self._layout.indexOf(widget) < 0:
            self._layout.addWidget(widget)

        # Important: if the previous root has been reused as a child somewhere
        # inside the new root (for example, the old root pane becoming one side
        # of a new splitter), do not detach it here or the newly rendered tree
        # will lose that live branch immediately.
        if old_root is not None and old_root is not widget and not self._is_widget_in_subtree(old_root, widget):
            old_root.setParent(None)

    def _is_widget_in_subtree(self, candidate, root):
        current = candidate
        while current is not None:
            if current is root:
                return True
            current = current.parentWidget()
        return False

    def add_tool(self, tool, title, target_pane=None, tool_id=None, plugin_id="", tool_type_id=""):
        existing = self.manager.model.tools.get(tool_id) if tool_id is not None else None
        if existing is None:
            tool_id = self.manager.register_tool(tool, title, plugin_id=plugin_id, tool_type_id=tool_type_id, tool_id=tool_id)
        else:
            existing.widget = tool
            existing.title = title
            existing.plugin_id = plugin_id or existing.plugin_id
            existing.tool_type_id = tool_type_id or existing.tool_type_id
        target_pane_id = None
        if isinstance(target_pane, WorkspacePane):
            target_pane_id = target_pane.pane_id
        elif isinstance(target_pane, str):
            target_pane_id = target_pane
        pane_id = self.manager.add_tool_to_window(self.window, tool_id, target_pane_id=target_pane_id)
        reset_tool_theme(tool, getattr(self.window, 'current_theme_name', 'Midnight'))
        return self.pane_by_id(pane_id)

    def preferred_pane(self):
        pane_id = self.manager.preferred_pane_id(self.window_id)
        return self.pane_by_id(pane_id)

    def pane_by_id(self, pane_id):
        if not pane_id:
            return None
        for pane in self.findChildren(WorkspacePane):
            if pane.pane_id == pane_id:
                return pane
        return None

    def root_pane(self):
        return self.preferred_pane()

    def all_tools(self):
        return self.manager.tools_for_window(self.window_id)