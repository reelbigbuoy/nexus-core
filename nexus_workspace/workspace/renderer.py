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
# File: renderer.py
# Description: Renders workspace layout models into live pane, tab, and splitter widgets.
#============================================================================

from nexus_workspace.framework.qt import QtCore, QtWidgets

from .layout_model import PaneNode, SplitNode
from .pane import WorkspacePane


class WorkspaceRenderer:
    def __init__(self, manager):
        self.manager = manager
        self._pane_views = {}

    def render_window(self, workspace_window):
        area = workspace_window.workspace_area
        window_node = self.manager.model.windows.get(area.window_id)
        if window_node is None:
            return

        old_root = area._root_widget
        live_pane_ids = set()
        new_root = self._build_widget_for_node(area, window_node.root_node, live_pane_ids)
        area._set_root_widget(new_root)

        # Only dispose of the previous root when it is not still participating
        # in the new rendered tree. This happens frequently when a root pane is
        # reused as a child of a newly created splitter after a split.
        if old_root is not None and old_root is not new_root and not self._is_widget_in_subtree(old_root, new_root):
            old_root.deleteLater()

    def cleanup_stale_panes(self):
        live_pane_ids = set()
        for window in self.manager.model.windows.values():
            for pane in self.manager.model.iter_panes(window.root_node):
                live_pane_ids.add(pane.pane_id)

        stale_ids = [pane_id for pane_id in list(self._pane_views.keys()) if pane_id not in live_pane_ids]
        for pane_id in stale_ids:
            pane = self._pane_views.pop(pane_id, None)
            if pane is not None:
                pane.setParent(None)
                pane.deleteLater()

    def _build_widget_for_node(self, area, node, live_pane_ids):
        if isinstance(node, PaneNode):
            return self._build_pane_widget(area, node, live_pane_ids)
        if isinstance(node, SplitNode):
            splitter = QtWidgets.QSplitter(
                QtCore.Qt.Horizontal if node.orientation == "horizontal" else QtCore.Qt.Vertical,
                area,
            )
            splitter.setChildrenCollapsible(False)
            splitter.setHandleWidth(6)
            for child in node.children:
                splitter.addWidget(self._build_widget_for_node(area, child, live_pane_ids))
            if node.sizes and len(node.sizes) == splitter.count():
                splitter.setSizes(node.sizes)
            else:
                splitter.setSizes([1] * max(1, splitter.count()))
            return splitter
        fallback = WorkspacePane(self.manager, area, area)
        return fallback

    def _build_pane_widget(self, area, pane_node, live_pane_ids):
        live_pane_ids.add(pane_node.pane_id)
        pane = self._pane_views.get(pane_node.pane_id)
        if pane is None:
            pane = WorkspacePane(self.manager, area, area)
            self._pane_views[pane_node.pane_id] = pane
        elif pane.area is not area:
            pane.area = area

        pane.bind_pane_id(pane_node.pane_id)
        self._sync_pane_contents(pane, pane_node)
        return pane

    def _sync_pane_contents(self, pane, pane_node):
        desired_ids = list(pane_node.tool_ids)
        current_ids = list(pane._tool_ids)

        pane.tab_widget.blockSignals(True)
        try:
            # Remove tabs that no longer belong in this pane.
            for index in range(len(current_ids) - 1, -1, -1):
                tool_id = current_ids[index]
                if tool_id not in desired_ids:
                    widget = pane.tab_widget.widget(index)
                    pane.tab_widget.removeTab(index)
                    if widget is not None:
                        widget.setParent(None)
                    del pane._tool_ids[index]

            # Rebuild order to match the model exactly.
            ordered_widgets = []
            for tool_id in desired_ids:
                record = self.manager.model.tools.get(tool_id)
                if record is None:
                    continue
                ordered_widgets.append((tool_id, record.widget, record.title))

            while pane.tab_widget.count():
                widget = pane.tab_widget.widget(0)
                pane.tab_widget.removeTab(0)
                if widget is not None:
                    widget.setParent(None)
            pane._tool_ids = []

            for tool_id, widget, title in ordered_widgets:
                pane.add_tool(widget, title, tool_id=tool_id)

            active_tool_id = pane_node.active_tool_id
            if active_tool_id:
                index = pane.index_of_tool_id(active_tool_id)
                if index >= 0:
                    pane.tab_widget.setCurrentIndex(index)
            elif pane.tab_widget.count() > 0:
                pane.tab_widget.setCurrentIndex(0)
        finally:
            pane.tab_widget.blockSignals(False)

        pane.currentToolChanged.emit(pane.current_tool())
        pane.area.activeToolChanged.emit(pane.current_tool())


    def _is_widget_in_subtree(self, candidate, root):
        current = candidate
        while current is not None:
            if current is root:
                return True
            current = current.parentWidget()
        return False
