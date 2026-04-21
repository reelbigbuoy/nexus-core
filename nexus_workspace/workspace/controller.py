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
# File: controller.py
# Description: Coordinates user actions against the workspace model and layout operations.
#============================================================================

from .layout_model import PaneNode, SplitNode


class WorkspaceController:
    def __init__(self, manager):
        self.manager = manager
        self.model = manager.model

    def add_tool_to_window(self, window_id: str, tool_id: str, target_pane_id=None):
        window = self.model.windows[window_id]
        pane = self.model.find_pane(target_pane_id) if target_pane_id else self._preferred_pane(window.root_node)
        if pane is None:
            pane = PaneNode()
            window.root_node = pane
        self.model.insert_tool_into_pane(pane, tool_id)
        self.model.normalize_window(window)
        return pane.pane_id

    def move_tool(self, source_pane_id: str, tool_id: str, target_pane_id: str, zone: str):
        source_window = self.model.find_window_for_pane(source_pane_id)
        target_window = self.model.find_window_for_pane(target_pane_id)
        if source_window is None or target_window is None:
            return None
        source_pane = self.model.find_pane(source_pane_id)
        target_pane = self.model.find_pane(target_pane_id)
        if source_pane is None or target_pane is None or tool_id not in source_pane.tool_ids:
            return None

        # Same-pane center drop is just activation.
        if source_pane_id == target_pane_id and zone == "center":
            source_pane.active_tool_id = tool_id
            return target_pane_id

        # Splitting a pane against itself only makes sense when another tab remains behind.
        if source_pane_id == target_pane_id and zone != "center" and len(source_pane.tool_ids) <= 1:
            source_pane.active_tool_id = tool_id
            return target_pane_id

        self.model.remove_tool_from_pane(source_pane, tool_id)

        if zone == "center":
            self.model.insert_tool_into_pane(target_pane, tool_id)
            target_id = target_pane.pane_id
        else:
            # Important: do not construct the new SplitNode with target_pane as an
            # initial child before replacing target_pane in the window tree.
            # Doing so reparents target_pane too early, which makes the replacement
            # act against the wrong parent and can drop the moved tool from both the
            # source and destination during the first split.
            new_pane = PaneNode(tool_ids=[tool_id], active_tool_id=tool_id)
            orientation = "horizontal" if zone in ("left", "right") else "vertical"
            split = SplitNode(orientation=orientation, children=[])
            self.model.replace_node_in_window(target_window, target_pane, split)
            if zone in ("left", "top"):
                split.add_child(new_pane)
                split.add_child(target_pane)
            else:
                split.add_child(target_pane)
                split.add_child(new_pane)
            target_id = new_pane.pane_id

        self.model.normalize_window(source_window)
        if target_window is not source_window:
            self.model.normalize_window(target_window)
        return target_id

    def detach_tool_to_new_window(self, source_pane_id: str, tool_id: str, new_window_id: str):
        source_window = self.model.find_window_for_pane(source_pane_id)
        if source_window is None:
            return None
        source_pane = self.model.find_pane(source_pane_id)
        target_window = self.model.windows[new_window_id]
        if source_pane is None or tool_id not in source_pane.tool_ids:
            return None
        self.model.remove_tool_from_pane(source_pane, tool_id)
        target_pane = self._preferred_pane(target_window.root_node)
        self.model.insert_tool_into_pane(target_pane, tool_id)
        self.model.normalize_window(source_window)
        self.model.normalize_window(target_window)
        return target_pane.pane_id

    def close_tool(self, pane_id: str, tool_id: str):
        window = self.model.find_window_for_pane(pane_id)
        pane = self.model.find_pane(pane_id)
        if window is None or pane is None:
            return False
        self.model.remove_tool_from_pane(pane, tool_id)
        self.model.tools.pop(tool_id, None)
        self.model.normalize_window(window)
        return True

    def _preferred_pane(self, node):
        for pane in self.model.iter_panes(node):
            if pane.tool_ids:
                return pane
        panes = list(self.model.iter_panes(node))
        return panes[0] if panes else None
