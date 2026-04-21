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
# File: layout_model.py
# Description: Defines the data model for windows, panes, splits, and workspace layout state.
#============================================================================

from dataclasses import dataclass, field
from typing import List, Optional
import uuid


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class LayoutNode:
    def __init__(self, node_id: Optional[str] = None):
        self.node_id = node_id or _id("node")
        self.parent = None


class PaneNode(LayoutNode):
    def __init__(self, pane_id: Optional[str] = None, tool_ids=None, active_tool_id=None):
        super().__init__(pane_id or _id("pane"))
        self.pane_id = self.node_id
        self.tool_ids: List[str] = list(tool_ids or [])
        self.active_tool_id = active_tool_id


class SplitNode(LayoutNode):
    def __init__(self, orientation: str, children=None, sizes=None, split_id: Optional[str] = None):
        super().__init__(split_id or _id("split"))
        self.orientation = orientation  # horizontal / vertical
        self.children: List[LayoutNode] = []
        self.sizes: List[int] = list(sizes or [])
        for child in children or []:
            self.add_child(child)

    def add_child(self, child):
        child.parent = self
        self.children.append(child)

    def insert_child(self, index: int, child):
        child.parent = self
        self.children.insert(index, child)

    def replace_child(self, old_child, new_child):
        idx = self.children.index(old_child)
        new_child.parent = self
        old_child.parent = None
        self.children[idx] = new_child

    def remove_child(self, child):
        if child in self.children:
            self.children.remove(child)
            child.parent = None


@dataclass
class WindowNode:
    window_id: str = field(default_factory=lambda: _id("window"))
    root_node: LayoutNode = field(default_factory=PaneNode)
    geometry: object = None
    is_primary: bool = False


@dataclass
class ToolRecord:
    tool_id: str
    widget: object
    title: str
    plugin_id: str = ""
    tool_type_id: str = ""


class WorkspaceModel:
    def __init__(self):
        self.windows = {}
        self.tools = {}

    def register_window(self, window_id: str, root_node: Optional[LayoutNode] = None, is_primary: bool = False):
        node = WindowNode(window_id=window_id, root_node=root_node or PaneNode(), is_primary=is_primary)
        self.windows[window_id] = node
        return node

    def unregister_window(self, window_id: str):
        self.windows.pop(window_id, None)

    def register_tool(self, widget, title: str, plugin_id: str = "", tool_type_id: str = "", tool_id: Optional[str] = None):
        tool_id = tool_id or _id("tool")
        self.tools[tool_id] = ToolRecord(tool_id=tool_id, widget=widget, title=title, plugin_id=plugin_id, tool_type_id=tool_type_id)
        return tool_id

    def update_tool_title(self, tool_id: str, title: str):
        record = self.tools.get(tool_id)
        if record:
            record.title = title

    def find_pane(self, pane_id: str):
        for window in self.windows.values():
            found = self._find_pane_in_node(window.root_node, pane_id)
            if found is not None:
                return found
        return None

    def find_window_for_pane(self, pane_id: str):
        for window in self.windows.values():
            if self._find_pane_in_node(window.root_node, pane_id) is not None:
                return window
        return None

    def _find_pane_in_node(self, node, pane_id: str):
        if isinstance(node, PaneNode):
            return node if node.pane_id == pane_id else None
        if isinstance(node, SplitNode):
            for child in node.children:
                found = self._find_pane_in_node(child, pane_id)
                if found is not None:
                    return found
        return None

    def iter_panes(self, node):
        if isinstance(node, PaneNode):
            yield node
        elif isinstance(node, SplitNode):
            for child in node.children:
                yield from self.iter_panes(child)

    def remove_tool_from_pane(self, pane: PaneNode, tool_id: str):
        if tool_id in pane.tool_ids:
            pane.tool_ids.remove(tool_id)
            if pane.active_tool_id == tool_id:
                pane.active_tool_id = pane.tool_ids[-1] if pane.tool_ids else None

    def insert_tool_into_pane(self, pane: PaneNode, tool_id: str, index: Optional[int] = None, make_active: bool = True):
        if tool_id in pane.tool_ids:
            pane.tool_ids.remove(tool_id)
        if index is None or index < 0 or index > len(pane.tool_ids):
            pane.tool_ids.append(tool_id)
        else:
            pane.tool_ids.insert(index, tool_id)
        if make_active:
            pane.active_tool_id = tool_id

    def replace_node_in_window(self, window_node: WindowNode, old_node: LayoutNode, new_node: LayoutNode):
        parent = old_node.parent
        if parent is None:
            window_node.root_node = new_node
            new_node.parent = None
            return
        if isinstance(parent, SplitNode):
            parent.replace_child(old_node, new_node)

    def normalize_window(self, window_node: WindowNode):
        root = self._normalize_node(window_node.root_node)
        if root is None:
            root = PaneNode()
        root.parent = None
        window_node.root_node = root

    def _normalize_node(self, node):
        if isinstance(node, PaneNode):
            live_tool_ids = [tool_id for tool_id in node.tool_ids if tool_id in self.tools]
            if live_tool_ids != node.tool_ids:
                node.tool_ids = live_tool_ids
            if node.active_tool_id not in node.tool_ids:
                node.active_tool_id = node.tool_ids[-1] if node.tool_ids else None
            return node if node.tool_ids else None
        if isinstance(node, SplitNode):
            normalized_children = []
            for child in node.children:
                nchild = self._normalize_node(child)
                if nchild is None:
                    continue
                if isinstance(nchild, SplitNode) and nchild.orientation == node.orientation:
                    for grand in nchild.children:
                        grand.parent = node
                        normalized_children.append(grand)
                else:
                    nchild.parent = node
                    normalized_children.append(nchild)
            node.children = normalized_children
            if not node.children:
                return None
            if len(node.children) == 1:
                only = node.children[0]
                only.parent = node.parent
                return only
            if node.sizes and len(node.sizes) != len(node.children):
                node.sizes = []
            return node
        return None
