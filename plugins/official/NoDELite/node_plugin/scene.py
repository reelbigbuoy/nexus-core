# ============================================================================
# Nexus
# File: plugins/owner/NoDE/node_plugin/scene.py
# Description: Scene management and graph interaction logic for NoDE Plugin.
# Part of: NoDE Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================

import math
from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets
from nexus_workspace.core.themes import THEMES
from .constants import GRID_SIZE
from .definitions import TestNodeData, node_definition_for_type, create_node_entry
from .graphics_items import NodeItem, PortItem, ConnectionItem, InlineSubgraphBoundaryItem
from .commands import AddConnectionCommand, MoveNodeCommand, UpdateConnectionCommand, SetConnectionRoutePointsCommand
from .models import GraphConnectionData


class GraphScene(QtWidgets.QGraphicsScene):
    SNAP_DISTANCE = 24.0

    def __init__(self, theme_name="Midnight", parent=None):
        super().__init__(parent)
        self.drag_connection = None
        self.drag_source_port = None
        self.drag_target_port = None
        self.reconnect_connection = None
        self.reconnect_endpoint = None
        self.reconnect_original_data = None
        self.reconnect_target_port = None
        self.theme_name = theme_name
        self.theme = THEMES[self.theme_name]
        self.undo_stack = None
        self._suspend_undo = False
        self._highlighted_ports = set()
        self._scene_margin = 2000.0
        self.setItemIndexMethod(QtWidgets.QGraphicsScene.BspTreeIndex)
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def ensure_logical_scene_rect(self, extra_rect=None):
        current = self.sceneRect()
        if extra_rect is not None and extra_rect.isValid() and not extra_rect.isNull():
            padded_extra = QtCore.QRectF(extra_rect).adjusted(
                -self._scene_margin,
                -self._scene_margin,
                self._scene_margin,
                self._scene_margin,
            )
            if current.isValid() and not current.isNull() and current.contains(padded_extra):
                return

        bounds = QtCore.QRectF()
        has_bounds = False

        for item in self.items():
            if isinstance(item, (NodeItem, ConnectionItem, InlineSubgraphBoundaryItem)):
                item_rect = item.sceneBoundingRect()
                if item_rect.isValid() and not item_rect.isNull():
                    bounds = item_rect if not has_bounds else bounds.united(item_rect)
                    has_bounds = True

        if extra_rect is not None and extra_rect.isValid() and not extra_rect.isNull():
            bounds = extra_rect if not has_bounds else bounds.united(extra_rect)
            has_bounds = True

        if not has_bounds:
            bounds = QtCore.QRectF(-5000, -5000, 10000, 10000)

        bounds = bounds.adjusted(
            -self._scene_margin,
            -self._scene_margin,
            self._scene_margin,
            self._scene_margin,
        )

        if current.isValid() and not current.isNull() and current.contains(bounds):
            return

        expanded = current.united(bounds) if current.isValid() and not current.isNull() else bounds
        self.setSceneRect(expanded)

    def set_theme(self, theme_name):
        self.theme_name = theme_name
        self.theme = THEMES[theme_name]
        for item in self.items():
            if isinstance(item, ConnectionItem):
                item.refresh_style()
            item.update()
        self.update()

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        painter.fillRect(rect, QtGui.QColor(self.theme["grid_bg"]))

        left = int(math.floor(rect.left() / GRID_SIZE) * GRID_SIZE)
        top = int(math.floor(rect.top() / GRID_SIZE) * GRID_SIZE)

        lines = []
        painter.setPen(QtGui.QPen(QtGui.QColor(self.theme["grid_line"]), 1))

        x = left
        while x < rect.right():
            lines.append(QtCore.QLineF(x, rect.top(), x, rect.bottom()))
            x += GRID_SIZE

        y = top
        while y < rect.bottom():
            lines.append(QtCore.QLineF(rect.left(), y, rect.right(), y))
            y += GRID_SIZE

        painter.drawLines(lines)

    def add_node(self, title="Node", pos=QtCore.QPointF(0, 0), inputs=None, outputs=None, node_type="generic", node_id=None, properties=None):
        node_entry = create_node_entry(
            node_type=node_type,
            pos=pos,
            node_id=node_id,
            title=title,
            properties=properties,
            inputs=inputs,
            outputs=outputs,
        )
        return self.add_node_from_entry(node_entry)

    def add_node_from_data(self, node_data: TestNodeData, inputs=None, outputs=None):
        node = NodeItem(node_data=node_data, inputs=inputs, outputs=outputs)
        self.addItem(node)
        node.setPos(QtCore.QPointF(node_data.x, node_data.y))
        self.ensure_logical_scene_rect(node.sceneBoundingRect())
        return node

    def add_node_from_entry(self, node_entry, select_new=False):
        node_data = TestNodeData.from_dict(node_entry.get("node_data", {}))
        definition = node_definition_for_type(node_data.node_type)
        if definition is not None:
            merged_properties = definition.default_properties()
            merged_properties.update(node_data.properties or {})
            node_data.properties = merged_properties
            inputs = node_entry.get("inputs") if "inputs" in node_entry else [port.name for port in definition.inputs]
            outputs = node_entry.get("outputs") if "outputs" in node_entry else [port.name for port in definition.outputs]
            metadata = getattr(definition, "metadata", {}) or {}
            if metadata.get("dynamic_output_ports_from") == "columns":
                columns = list((node_data.properties or {}).get("columns", []))
                outputs = [str(column.get("name") or f"column_{index + 1}") for index, column in enumerate(columns)]
            if not node_data.title or node_data.title == "Node":
                node_data.title = definition.display_name
        else:
            inputs = node_entry.get("inputs", ["In"])
            outputs = node_entry.get("outputs", ["Out"])

        existing = self.find_node_by_id(node_data.node_id)
        if existing is not None:
            if select_new:
                self.clearSelection()
                existing.setSelected(True)
            return existing

        node = self.add_node_from_data(node_data, inputs=inputs, outputs=outputs)
        if select_new:
            self.clearSelection()
            node.setSelected(True)
        return node

    def create_connection(self, source_port, target_port, route_points=None):
        conn = ConnectionItem(source_port=source_port, target_port=target_port, route_points=route_points or [])
        self.addItem(conn)
        # ConnectionItem builds its path before it belongs to a scene. Route-point pin
        # handles therefore need a second sync pass after the item has actually been
        # inserted into the scene so restored/undone connections re-create their bend
        # points visually as well as logically.
        conn.update_path()
        conn.sync_pin_items()
        conn.refresh_style()
        self.ensure_logical_scene_rect(conn.sceneBoundingRect())
        return conn

    def add_connection_from_dict(self, conn_entry):
        conn_data = GraphConnectionData.from_dict(conn_entry).to_dict()
        source_node = self.find_node_by_id(conn_data.get("source_node_id"))
        target_node = self.find_node_by_id(conn_data.get("target_node_id"))

        if not source_node or not target_node:
            return None

        source_port = self.find_output_port(source_node, conn_data.get("source_port_name"))
        target_port = self.find_input_port(target_node, conn_data.get("target_port_name"))

        if not source_port or not target_port:
            return None

        existing = self.find_connection(conn_data)
        if existing is not None:
            return existing

        route_points = [QtCore.QPointF(x, y) for x, y in conn_data.get("route_points", [])]
        return self.create_connection(source_port, target_port, route_points=route_points)

    def _set_port_highlight(self, port, state):
        if port is None:
            return
        port.set_visual_state(state)
        self._highlighted_ports.add(port)

    def clear_port_feedback(self):
        for port in list(self._highlighted_ports):
            port.set_visual_state(PortItem.STATE_NORMAL)
        self._highlighted_ports.clear()

    def _ports_in_scene(self):
        for item in self.items():
            if isinstance(item, PortItem):
                yield item

    def _editor_allows_connection(self, source_port, target_port, connection_to_ignore=None):
        views = self.views()
        if not views:
            return True
        editor = getattr(views[0], "editor", None)
        if editor is None or not hasattr(editor, "allows_connection_between_ports"):
            return True
        return bool(editor.allows_connection_between_ports(source_port, target_port, connection_to_ignore=connection_to_ignore))

    def _is_valid_connection_target(self, source_port, target_port):
        return (
            source_port is not None and target_port is not None and
            source_port.port_type == PortItem.OUTPUT and
            target_port.port_type == PortItem.INPUT and
            self._editor_allows_connection(source_port, target_port)
        )

    def _is_valid_reconnect_target(self, connection, endpoint, port):
        if connection is None or port is None:
            return False
        if endpoint == ConnectionItem.ENDPOINT_TARGET:
            return (
                port.port_type == PortItem.INPUT and
                connection.source_port is not None and
                self._editor_allows_connection(connection.source_port, port, connection_to_ignore=connection)
            )
        return (
            port.port_type == PortItem.OUTPUT and
            connection.target_port is not None and
            self._editor_allows_connection(port, connection.target_port, connection_to_ignore=connection)
        )

    def _find_best_port_candidate(self, scene_pos, predicate):
        best_port = None
        best_distance = None
        for port in self._ports_in_scene():
            if not predicate(port):
                continue
            distance = QtCore.QLineF(scene_pos, port.scene_center()).length()
            if distance <= self.SNAP_DISTANCE and (best_distance is None or distance < best_distance):
                best_distance = distance
                best_port = port
        return best_port

    def begin_connection_drag(self, source_port: PortItem):
        if source_port.port_type != PortItem.OUTPUT:
            return
        self.cancel_endpoint_reconnect()
        self.clear_port_feedback()
        self.drag_source_port = source_port
        self.drag_target_port = None
        self.drag_connection = ConnectionItem(
            source_port=source_port,
            temp_end_pos=source_port.scene_center(),
            preview_mode=True,
        )
        self.addItem(self.drag_connection)
        self.drag_connection.refresh_style()

    def update_connection_drag(self, scene_pos: QtCore.QPointF, hovered_item=None):
        if not self.drag_connection or not self.drag_source_port:
            return
        self.clear_port_feedback()
        hovered_port = hovered_item if isinstance(hovered_item, PortItem) else None
        snap_port = self._find_best_port_candidate(
            scene_pos,
            lambda port: self._is_valid_connection_target(self.drag_source_port, port)
        )
        chosen_port = snap_port
        if hovered_port is not None:
            if self._is_valid_connection_target(self.drag_source_port, hovered_port):
                self._set_port_highlight(hovered_port, PortItem.STATE_VALID)
                chosen_port = hovered_port
            else:
                self._set_port_highlight(hovered_port, PortItem.STATE_INVALID)
        if snap_port is not None:
            self._set_port_highlight(snap_port, PortItem.STATE_SNAP if snap_port is chosen_port else PortItem.STATE_VALID)
        self.drag_target_port = chosen_port
        drag_pos = chosen_port.scene_center() if chosen_port is not None else scene_pos
        self.drag_connection.preview_valid = chosen_port is not None
        self.drag_connection.setVisible(True)
        self.drag_connection.set_route_points([])
        self.drag_connection.setSelected(False)
        self.drag_connection.temp_end_pos = QtCore.QPointF(drag_pos)
        self.drag_connection.refresh_style()
        self.drag_connection.update_path()

    def end_connection_drag(self, target_item=None):
        if not self.drag_connection or not self.drag_source_port:
            return

        chosen_target = self.drag_target_port
        if chosen_target is None and isinstance(target_item, PortItem) and self._is_valid_connection_target(self.drag_source_port, target_item):
            chosen_target = target_item

        drag_conn = self.drag_connection
        self.drag_connection = None
        self.drag_target_port = None
        self.clear_port_feedback()

        connection_data = None
        if chosen_target is not None:
            connection_data = GraphConnectionData(
                self.drag_source_port.parent_node.node_data.node_id,
                self.drag_source_port.name,
                chosen_target.parent_node.node_data.node_id,
                chosen_target.name,
                [],
            ).to_dict()

        drag_conn.remove_from_ports()
        self.removeItem(drag_conn)

        if connection_data:
            if self.undo_stack is not None and not self._suspend_undo:
                self.undo_stack.push(AddConnectionCommand(self, connection_data))
            else:
                self.add_connection_from_dict(connection_data)

        self.drag_source_port = None

    def cancel_connection_drag(self):
        self.clear_port_feedback()
        if self.drag_connection:
            self.drag_connection.remove_from_ports()
            self.removeItem(self.drag_connection)
        self.drag_connection = None
        self.drag_source_port = None
        self.drag_target_port = None

    def begin_endpoint_reconnect(self, connection, endpoint, scene_pos):
        if connection is None:
            return
        self.cancel_connection_drag()
        self.clear_port_feedback()
        self.reconnect_connection = connection
        self.reconnect_endpoint = endpoint
        self.reconnect_original_data = connection.to_dict()
        self.reconnect_target_port = None
        connection.begin_endpoint_drag(endpoint, scene_pos)

    def update_endpoint_reconnect(self, scene_pos, hovered_item=None):
        connection = self.reconnect_connection
        endpoint = self.reconnect_endpoint
        if connection is None or endpoint is None:
            return
        self.clear_port_feedback()
        hovered_port = hovered_item if isinstance(hovered_item, PortItem) else None
        snap_port = self._find_best_port_candidate(
            scene_pos,
            lambda port: self._is_valid_reconnect_target(connection, endpoint, port)
        )
        chosen_port = snap_port
        if hovered_port is not None:
            if self._is_valid_reconnect_target(connection, endpoint, hovered_port):
                self._set_port_highlight(hovered_port, PortItem.STATE_VALID)
                chosen_port = hovered_port
            else:
                self._set_port_highlight(hovered_port, PortItem.STATE_INVALID)
        if snap_port is not None:
            self._set_port_highlight(snap_port, PortItem.STATE_SNAP if snap_port is chosen_port else PortItem.STATE_VALID)
        self.reconnect_target_port = chosen_port
        drag_pos = chosen_port.scene_center() if chosen_port is not None else scene_pos
        connection.update_endpoint_drag(drag_pos, valid=chosen_port is not None)

    def end_endpoint_reconnect(self, target_item=None):
        connection = self.reconnect_connection
        endpoint = self.reconnect_endpoint
        old_data = self.reconnect_original_data
        chosen_port = self.reconnect_target_port
        if connection is None or endpoint is None or old_data is None:
            return
        if chosen_port is None and isinstance(target_item, PortItem) and self._is_valid_reconnect_target(connection, endpoint, target_item):
            chosen_port = target_item

        connection.restore_attached_state()
        self.clear_port_feedback()

        was_selected = connection.isSelected()
        if chosen_port is not None:
            new_data = GraphConnectionData.from_dict(old_data).to_dict()
            if endpoint == ConnectionItem.ENDPOINT_SOURCE:
                new_data["source_node_id"] = chosen_port.parent_node.node_data.node_id
                new_data["source_port_name"] = chosen_port.name
            else:
                new_data["target_node_id"] = chosen_port.parent_node.node_data.node_id
                new_data["target_port_name"] = chosen_port.name
            if self.undo_stack is not None and not self._suspend_undo:
                self.undo_stack.push(UpdateConnectionCommand(self, old_data, new_data, text="Reconnect Connection"))
            else:
                self.remove_connection_by_dict(old_data)
                self.add_connection_from_dict(new_data)
            if was_selected:
                self._select_connection_by_data(new_data)

        self.reconnect_connection = None
        self.reconnect_endpoint = None
        self.reconnect_original_data = None
        self.reconnect_target_port = None

    def cancel_endpoint_reconnect(self):
        self.clear_port_feedback()
        if self.reconnect_connection is not None:
            self.reconnect_connection.restore_attached_state()
        self.reconnect_connection = None
        self.reconnect_endpoint = None
        self.reconnect_original_data = None
        self.reconnect_target_port = None

    
    def _route_points_command_payload(self, connection, route_points):
        data = connection.connection_data()
        if data is None:
            return None
        payload = data.to_dict()
        payload["route_points"] = [
            (float(point.x()), float(point.y())) if isinstance(point, QtCore.QPointF) else tuple(point)
            for point in route_points
        ]
        return payload

    def add_connection_pin(self, connection, scene_pos):
        if connection is None:
            return None
        if connection.endpoint_hit(scene_pos, tolerance=12.0) is not None:
            return None
        segment_index, _ = connection.nearest_segment_index(scene_pos)
        if segment_index is None:
            return None
        insert_index = connection.insert_pin_index_for_segment(segment_index)
        old_route_points = [QtCore.QPointF(p) for p in connection.route_points]
        new_route_points = old_route_points[:]
        new_route_points.insert(insert_index, QtCore.QPointF(scene_pos))
        before = self._route_points_command_payload(connection, old_route_points)
        after = self._route_points_command_payload(connection, new_route_points)
        if before is None or after is None:
            return None
        if self.undo_stack is not None and not self._suspend_undo:
            self.undo_stack.push(SetConnectionRoutePointsCommand(self, before, after, text="Add Connection Pin"))
            target_connection = self.find_connection(after)
        else:
            connection.set_route_points(new_route_points)
            target_connection = connection

        if target_connection is None:
            return None

        target_connection.sync_pin_items()
        if not (0 <= insert_index < len(target_connection.pin_items)):
            return None

        pin_item = target_connection.pin_items[insert_index]
        self.clearSelection()
        pin_item.setSelected(True)
        target_connection.update()
        if self.focusItem() is not pin_item:
            self.setFocusItem(pin_item)
        return pin_item

    def remove_connection_pin(self, connection, index):
        if connection is None:
            return
        old_route_points = [QtCore.QPointF(p) for p in connection.route_points]
        if not (0 <= index < len(old_route_points)):
            return
        new_route_points = old_route_points[:index] + old_route_points[index + 1:]
        before = self._route_points_command_payload(connection, old_route_points)
        after = self._route_points_command_payload(connection, new_route_points)
        if before is None or after is None:
            return
        if self.undo_stack is not None and not self._suspend_undo:
            self.undo_stack.push(SetConnectionRoutePointsCommand(self, before, after, text="Remove Connection Pin"))
        else:
            connection.set_route_points(new_route_points)
            connection.setSelected(True)

    def handle_pin_moved(self, connection, index, old_pos, new_pos):
        if connection is None:
            return
        current_route_points = [QtCore.QPointF(p) for p in connection.route_points]
        if not (0 <= index < len(current_route_points)):
            return

        old_route_points = current_route_points[:]
        old_route_points[index] = QtCore.QPointF(old_pos)

        new_route_points = current_route_points[:]
        new_route_points[index] = QtCore.QPointF(new_pos)

        if old_route_points == new_route_points:
            return

        before = self._route_points_command_payload(connection, old_route_points)
        after = self._route_points_command_payload(connection, new_route_points)
        if before is None or after is None:
            return

        if self.undo_stack is not None and not self._suspend_undo:
            self.undo_stack.push(
                SetConnectionRoutePointsCommand(
                    self,
                    before,
                    after,
                    text="Move Connection Pin",
                )
            )
        else:
            connection.set_route_points(new_route_points)
            connection.setSelected(True)

    def _select_connection_by_data(self, conn_entry):
        connection = self.find_connection(conn_entry)
        if connection is not None:
            self.clearSelection()
            connection.setSelected(True)
        return connection

    def reconnect_candidate_for_port(self, port):
        if port is None or not getattr(port, "connections", None):
            return None, None
        if port.port_type == PortItem.INPUT:
            return port.connections[-1], ConnectionItem.ENDPOINT_TARGET
        if port.port_type == PortItem.OUTPUT and len(port.connections) == 1:
            return port.connections[0], ConnectionItem.ENDPOINT_SOURCE
        return None, None
    def find_node_by_id(self, node_id):
        for item in self.items():
            if isinstance(item, NodeItem) and item.node_data.node_id == node_id:
                return item
        return None

    def find_output_port(self, node_item, port_name):
        for port in node_item.outputs:
            if port.name == port_name:
                return port
        return None

    def find_input_port(self, node_item, port_name):
        for port in node_item.inputs:
            if port.name == port_name:
                return port
        return None

    def _connection_identity_key(self, conn_entry):
        data = GraphConnectionData.from_dict(conn_entry).to_dict()
        return (
            data.get("source_node_id"),
            data.get("source_port_name"),
            data.get("target_node_id"),
            data.get("target_port_name"),
            data.get("connection_kind"),
        )

    def find_connection(self, conn_entry, ignore_route_points=False):
        conn_entry = GraphConnectionData.from_dict(conn_entry).to_dict()
        identity_key = self._connection_identity_key(conn_entry)
        identity_matches = []
        for item in self.items():
            if not isinstance(item, ConnectionItem):
                continue
            data = item.to_dict()
            if data == conn_entry:
                return item
            if ignore_route_points and self._connection_identity_key(data) == identity_key:
                identity_matches.append(item)
        if ignore_route_points and len(identity_matches) == 1:
            return identity_matches[0]
        return None

    def remove_connection_by_dict(self, conn_entry):
        conn = self.find_connection(conn_entry, ignore_route_points=True)
        if conn is not None:
            conn.remove_from_ports()
            for pin in list(conn.pin_items):
                self.removeItem(pin)
            self.removeItem(conn)

    def remove_node_by_id(self, node_id):
        node = self.find_node_by_id(node_id)
        if node is None:
            return

        all_ports = node.inputs + node.outputs
        connections = []
        for port in all_ports:
            connections.extend(port.connections)

        for conn in list(set(connections)):
            conn.remove_from_ports()
            for pin in list(conn.pin_items):
                self.removeItem(pin)
            self.removeItem(conn)

        self.removeItem(node)

    def snapshot_items_for_delete(self, selected_items):
        node_items = {item for item in selected_items if isinstance(item, NodeItem)}
        connection_items = {item for item in selected_items if isinstance(item, ConnectionItem)}

        for node in node_items:
            for port in node.inputs + node.outputs:
                connection_items.update(port.connections)

        nodes = []
        connections = []

        for node in node_items:
            nodes.append(node.to_dict())

        for conn in connection_items:
            conn_data = conn.to_dict()
            if conn_data:
                connections.append(conn_data)

        connections.sort(key=lambda entry: (
            entry["source_node_id"],
            entry["source_port_name"],
            entry["target_node_id"],
            entry["target_port_name"],
        ))
        nodes.sort(key=lambda entry: entry.get("node_data", {}).get("node_id", ""))

        return {
            "nodes": nodes,
            "connections": connections,
        }


    def clear_execution_feedback(self):
        for item in self.items():
            if isinstance(item, NodeItem):
                item.set_execution_state('normal', '')
            elif isinstance(item, ConnectionItem):
                item.set_execution_state('normal')

    def apply_execution_feedback(self, payload):
        payload = payload or {}
        self.clear_execution_feedback()
        current_node_id = payload.get('current_node_id')
        node_runtime_lookup = payload.get('node_runtime_data') or {}
        if current_node_id:
            node = self.find_node_by_id(current_node_id)
            if node is not None:
                current_runtime = node_runtime_lookup.get(current_node_id) or {}
                notes = current_runtime.get('notes') or []
                note = '\n'.join(str(n) for n in notes) if notes else ''
                node.set_execution_state('current', note)
        for node_id in payload.get('evaluated_node_ids', []) or []:
            if node_id == current_node_id:
                continue
            node = self.find_node_by_id(node_id)
            if node is not None:
                current_runtime = node_runtime_lookup.get(node_id) or {}
                notes = current_runtime.get('notes') or []
                note = '\n'.join(str(n) for n in notes) if notes else ''
                node.set_execution_state('evaluated', note)
        conn_data = payload.get('last_connection_data')
        if conn_data:
            connection = self.find_connection(conn_data, ignore_route_points=True)
            if connection is not None:
                connection.set_execution_state('active')
        if payload.get('status') == 'error' and current_node_id:
            node = self.find_node_by_id(current_node_id)
            if node is not None:
                node.set_execution_state('error', payload.get('last_error', 'Execution error'))
        if payload.get('status') == 'halted' and current_node_id:
            node = self.find_node_by_id(current_node_id)
            if node is not None:
                node.set_execution_state('halted', 'Execution halted')

    def clear_graph(self):
        self.clear_execution_feedback()
        self.clear()
        self.drag_connection = None
        self.drag_source_port = None
        self.drag_target_port = None
        self.reconnect_connection = None
        self.reconnect_endpoint = None
        self.reconnect_original_data = None
        self.reconnect_target_port = None
        self._highlighted_ports = set()
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def serialize_graph(self):
        nodes = []
        connections = []

        for item in self.items():
            if getattr(item, '_inline_subgraph_display', False):
                continue
            if isinstance(item, NodeItem):
                nodes.append(item.to_dict())
            elif isinstance(item, ConnectionItem):
                conn_data = item.to_dict()
                if conn_data:
                    connections.append(conn_data)

        nodes.sort(key=lambda entry: entry.get("node_data", {}).get("node_id", ""))
        connections.sort(key=lambda entry: (
            entry["source_node_id"],
            entry["source_port_name"],
            entry["target_node_id"],
            entry["target_port_name"],
        ))

        return {
            "nodes": nodes,
            "connections": connections,
        }

    def load_graph(self, graph_data):
        self.clear_graph()

        for node_entry in graph_data.get("nodes", []):
            self.add_node_from_entry(node_entry)

        for conn_entry in graph_data.get("connections", []):
            self.add_connection_from_dict(conn_entry)

    def handle_node_moved(self, node_item, old_pos, new_pos):
        if old_pos == new_pos or self.undo_stack is None:
            return
        self.undo_stack.push(MoveNodeCommand(node_item, old_pos, new_pos))
