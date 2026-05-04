# ============================================================================
#
# Copyright (c) 2026 Reel Big Buoy Company
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Nexus Core
# File: authoring.py
# Description: Shared graph authoring helpers for commands, palette state, and selection.
#
# ============================================================================

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from nexus_workspace.framework.qt import QtCore


@dataclass(frozen=True)
class GraphCommandDescriptor:
    """Generic authoring command metadata.

    This is intentionally domain-neutral. Tools such as STAT may register
    domain commands elsewhere, but the shared graph framework only stores and
    resolves generic command descriptors.
    """

    command_id: str
    label: str
    category: str = "Graph"
    shortcut: str = ""
    description: str = ""
    handler: Optional[Callable] = None


class GraphCommandRegistry:
    """Small command registry used by graph authoring UI."""

    def __init__(self):
        self._commands: Dict[str, GraphCommandDescriptor] = {}

    def clear(self):
        self._commands.clear()

    def register(self, descriptor: GraphCommandDescriptor):
        if not descriptor.command_id:
            raise ValueError("Graph command is missing command_id")
        self._commands[descriptor.command_id] = descriptor
        return descriptor

    def get(self, command_id: str) -> Optional[GraphCommandDescriptor]:
        return self._commands.get(command_id)

    def all_commands(self) -> List[GraphCommandDescriptor]:
        return sorted(self._commands.values(), key=lambda item: (item.category.lower(), item.label.lower()))

    def search(self, query: str) -> List[GraphCommandDescriptor]:
        needle = (query or "").strip().lower()
        if not needle:
            return self.all_commands()
        return [
            command for command in self.all_commands()
            if needle in " ".join([
                command.command_id,
                command.label,
                command.category,
                command.shortcut,
                command.description,
            ]).lower()
        ]


GRAPH_COMMAND_REGISTRY = GraphCommandRegistry()


class PaletteUsageStore:
    """Persist generic node palette preferences without domain coupling."""

    FAVORITES_KEY = "graph_editor/node_palette/favorites"
    RECENTS_KEY = "graph_editor/node_palette/recents"
    MAX_RECENTS = 8

    @classmethod
    def _settings(cls):
        return QtCore.QSettings("Reel Big Buoy Company", "Nexus Core")

    @classmethod
    def favorites(cls) -> List[str]:
        value = cls._settings().value(cls.FAVORITES_KEY, [])
        if isinstance(value, str):
            value = [item for item in value.split(";") if item]
        return list(value or [])

    @classmethod
    def recents(cls) -> List[str]:
        value = cls._settings().value(cls.RECENTS_KEY, [])
        if isinstance(value, str):
            value = [item for item in value.split(";") if item]
        return list(value or [])

    @classmethod
    def set_favorites(cls, type_ids: Sequence[str]):
        clean = []
        for type_id in type_ids or []:
            type_id = str(type_id or "").strip()
            if type_id and type_id not in clean:
                clean.append(type_id)
        cls._settings().setValue(cls.FAVORITES_KEY, clean)

    @classmethod
    def toggle_favorite(cls, type_id: str) -> bool:
        type_id = str(type_id or "").strip()
        if not type_id:
            return False
        favorites = cls.favorites()
        if type_id in favorites:
            favorites.remove(type_id)
            cls.set_favorites(favorites)
            return False
        favorites.insert(0, type_id)
        cls.set_favorites(favorites)
        return True

    @classmethod
    def record_recent(cls, type_id: str):
        type_id = str(type_id or "").strip()
        if not type_id:
            return
        recents = [item for item in cls.recents() if item != type_id]
        recents.insert(0, type_id)
        cls._settings().setValue(cls.RECENTS_KEY, recents[:cls.MAX_RECENTS])


class SelectionManager(QtCore.QObject):
    """Domain-neutral selected item helper for graph authoring commands."""

    selectionChanged = QtCore.pyqtSignal()

    def __init__(self, scene=None, node_cls=None, connection_cls=None, parent=None):
        super().__init__(parent)
        self._scene = None
        self._node_cls = node_cls
        self._connection_cls = connection_cls
        self.set_scene(scene)

    def set_scene(self, scene):
        if self._scene is scene:
            return
        if self._scene is not None:
            try:
                self._scene.selectionChanged.disconnect(self.selectionChanged.emit)
            except Exception:
                pass
        self._scene = scene
        if self._scene is not None:
            self._scene.selectionChanged.connect(self.selectionChanged.emit)

    def selected_nodes(self):
        if self._scene is None or self._node_cls is None:
            return []
        return [item for item in self._scene.selectedItems() if isinstance(item, self._node_cls) and item.isVisible()]

    def selected_connections(self):
        if self._scene is None or self._connection_cls is None:
            return []
        return [item for item in self._scene.selectedItems() if isinstance(item, self._connection_cls) and item.isVisible()]

    def selection_bounds(self):
        nodes = self.selected_nodes()
        if not nodes:
            return QtCore.QRectF()
        bounds = QtCore.QRectF()
        for node in nodes:
            bounds = bounds.united(node.sceneBoundingRect())
        return bounds
