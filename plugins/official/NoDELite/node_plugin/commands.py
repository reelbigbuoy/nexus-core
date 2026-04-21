# ============================================================================
# Nexus
# File: plugins/owner/NoDE/node_plugin/commands.py
# Description: Source module for node plugin functionality.
# Part of: NoDE Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================

from PyQt5 import QtCore, QtWidgets
from .definitions import node_definition_for_type, create_node_entry
from .models import GraphConnectionData


class MoveNodeCommand(QtWidgets.QUndoCommand):
    def __init__(self, node_item, old_pos, new_pos):
        super().__init__(f"Move {node_item.node_data.title}")
        self.node_item = node_item
        self.old_pos = QtCore.QPointF(old_pos)
        self.new_pos = QtCore.QPointF(new_pos)

    def _apply_pos(self, pos):
        scene = self.node_item.scene()
        if scene is None:
            return
        scene._suspend_undo = True
        try:
            self.node_item.setPos(pos)
        finally:
            scene._suspend_undo = False

    def redo(self):
        self._apply_pos(self.new_pos)

    def undo(self):
        self._apply_pos(self.old_pos)


class RenameNodeCommand(QtWidgets.QUndoCommand):
    def __init__(self, node_item, old_title, new_title):
        super().__init__(f"Rename {old_title}")
        self.node_item = node_item
        self.old_title = old_title
        self.new_title = new_title

    def _apply_title(self, title):
        self.node_item.title = title
        editor = self._resolve_editor()
        if editor is not None:
            editor._updating_property_panel = True
            editor.editNodeTitle.setText(title)
            editor._updating_property_panel = False
            editor._property_title_before_edit = title
            editor.on_node_mutated(self.node_item, update_editor_title=True)

    def _resolve_editor(self):
        scene = self.node_item.scene()
        if scene is not None and scene.views():
            view = scene.views()[0]
            return getattr(view, "editor", None)
        return None

    def redo(self):
        self._apply_title(self.new_title)

    def undo(self):
        self._apply_title(self.old_title)


class SetNodePropertyCommand(QtWidgets.QUndoCommand):
    def __init__(self, node_item, property_name, old_value, new_value):
        title = getattr(node_item.node_data, 'title', 'Node')
        super().__init__(f"Edit {property_name} on {title}")
        self.node_item = node_item
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value

    def _apply_value(self, value):
        self.node_item.node_data.properties[self.property_name] = value
        editor = self._resolve_editor()
        if editor is not None:
            editor.on_node_mutated(self.node_item)

    def _resolve_editor(self):
        scene = self.node_item.scene()
        if scene is not None and scene.views():
            view = scene.views()[0]
            return getattr(view, "editor", None)
        return None

    def redo(self):
        self._apply_value(self.new_value)

    def undo(self):
        self._apply_value(self.old_value)


class AddNodeCommand(QtWidgets.QUndoCommand):
    def __init__(self, scene, title="Node", pos=QtCore.QPointF(0, 0), inputs=None, outputs=None, node_type="generic", node_id=None, properties=None):
        effective_title = title
        definition = node_definition_for_type(node_type)
        if definition is not None and (not effective_title or effective_title == "Node"):
            effective_title = definition.display_name
        super().__init__(f"Add {effective_title}")
        self.scene = scene
        self.node_entry = create_node_entry(
            node_type=node_type,
            pos=pos,
            node_id=node_id,
            title=effective_title,
            properties=properties,
            inputs=inputs,
            outputs=outputs,
        )

    def redo(self):
        self.scene.add_node_from_entry(self.node_entry, select_new=False)

    def undo(self):
        node_id = self.node_entry["node_data"]["node_id"]
        self.scene.remove_node_by_id(node_id)


class AddConnectionCommand(QtWidgets.QUndoCommand):
    def __init__(self, scene, connection_data):
        super().__init__("Add Connection")
        self.scene = scene
        self.connection_data = GraphConnectionData.from_dict(connection_data).to_dict()

    def redo(self):
        if self.scene.find_connection(self.connection_data) is None:
            self.scene.add_connection_from_dict(self.connection_data)

    def undo(self):
        self.scene.remove_connection_by_dict(self.connection_data)


class UpdateConnectionCommand(QtWidgets.QUndoCommand):
    def __init__(self, scene, old_connection_data, new_connection_data, text="Update Connection"):
        super().__init__(text)
        self.scene = scene
        self.old_connection_data = GraphConnectionData.from_dict(old_connection_data).to_dict()
        self.new_connection_data = GraphConnectionData.from_dict(new_connection_data).to_dict()

    def redo(self):
        self.scene.remove_connection_by_dict(self.old_connection_data)
        self.scene.add_connection_from_dict(self.new_connection_data)

    def undo(self):
        self.scene.remove_connection_by_dict(self.new_connection_data)
        self.scene.add_connection_from_dict(self.old_connection_data)


class SetConnectionRoutePointsCommand(QtWidgets.QUndoCommand):
    def __init__(self, scene, connection_data_before, connection_data_after, text="Update Connection Route"):
        super().__init__(text)
        self.scene = scene
        self.connection_data_before = GraphConnectionData.from_dict(connection_data_before).to_dict()
        self.connection_data_after = GraphConnectionData.from_dict(connection_data_after).to_dict()

    def _apply(self, old_data, new_data):
        self.scene.remove_connection_by_dict(old_data)
        if self.scene.find_connection(new_data) is None:
            self.scene.add_connection_from_dict(new_data)
        connection = self.scene.find_connection(new_data)
        if connection is not None:
            self.scene.clearSelection()
            connection.setSelected(True)
            connection.sync_pin_items()

    def redo(self):
        self._apply(self.connection_data_before, self.connection_data_after)

    def undo(self):
        self._apply(self.connection_data_after, self.connection_data_before)


class DeleteItemsCommand(QtWidgets.QUndoCommand):
    def __init__(self, scene, snapshot):
        super().__init__("Delete Selection")
        self.scene = scene
        self.snapshot = snapshot

    def redo(self):
        for conn_entry in self.snapshot["connections"]:
            self.scene.remove_connection_by_dict(conn_entry)

        for node_entry in self.snapshot["nodes"]:
            node_id = node_entry.get("node_data", {}).get("node_id")
            if node_id:
                self.scene.remove_node_by_id(node_id)

    def undo(self):
        for node_entry in self.snapshot["nodes"]:
            node_id = node_entry.get("node_data", {}).get("node_id")
            if node_id and self.scene.find_node_by_id(node_id) is None:
                self.scene.add_node_from_entry(node_entry)

        for conn_entry in self.snapshot["connections"]:
            if self.scene.find_connection(conn_entry) is None:
                self.scene.add_connection_from_dict(conn_entry)


class PasteItemsCommand(QtWidgets.QUndoCommand):
    def __init__(self, scene, snapshot):
        super().__init__("Paste Selection")
        self.scene = scene
        self.snapshot = snapshot

    def redo(self):
        self.scene.clearSelection()
        for node_entry in self.snapshot.get("nodes", []):
            self.scene.add_node_from_entry(node_entry, select_new=True)
        for conn_entry in self.snapshot.get("connections", []):
            if self.scene.find_connection(conn_entry) is None:
                self.scene.add_connection_from_dict(conn_entry)

    def undo(self):
        for conn_entry in self.snapshot.get("connections", []):
            self.scene.remove_connection_by_dict(conn_entry)

        for node_entry in self.snapshot.get("nodes", []):
            node_id = node_entry.get("node_data", {}).get("node_id")
            if node_id:
                self.scene.remove_node_by_id(node_id)


class ToggleNodeBreakpointCommand(QtWidgets.QUndoCommand):
    def __init__(self, node_item, enabled):
        title = getattr(node_item.node_data, 'title', 'Node')
        super().__init__(f"{'Enable' if enabled else 'Disable'} Breakpoint on {title}")
        self.node_item = node_item
        self.enabled = bool(enabled)
        self.old_enabled = bool((node_item.node_data.properties or {}).get('__runtime_breakpoint', False))

    def _apply(self, enabled):
        self.node_item.node_data.properties['__runtime_breakpoint'] = bool(enabled)
        self.node_item.breakpoint_enabled = bool(enabled)
        self.node_item.update()
        editor = self._resolve_editor()
        if editor is not None:
            editor.on_node_mutated(self.node_item)

    def _resolve_editor(self):
        scene = self.node_item.scene()
        if scene is not None and scene.views():
            view = scene.views()[0]
            return getattr(view, 'editor', None)
        return None

    def redo(self):
        self._apply(self.enabled)

    def undo(self):
        self._apply(self.old_enabled)
