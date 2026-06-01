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
from .graphics_items import NodeItem, PortItem, ConnectionItem, InlineSubgraphBoundaryItem, ZoneBoundaryItem
from .commands import AddConnectionCommand, MoveNodeCommand, UpdateConnectionCommand, SetConnectionRoutePointsCommand
from .models import GraphConnectionData


class GraphScene(QtWidgets.QGraphicsScene):
    SNAP_DISTANCE = 24.0

    def __init__(self, theme_name="Midnight", parent=None):
        super().__init__(parent)
        self.drag_connection = None
        self.drag_source_port = None
        self.drag_target_port = None
        self.drag_visible_target_port = None
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
        self._selection_order = []
        self.selectionChanged.connect(self._track_selection_order)
        self.setItemIndexMethod(QtWidgets.QGraphicsScene.BspTreeIndex)
        self.setSceneRect(-5000, -5000, 10000, 10000)

    def _track_selection_order(self):
        selected = [item for item in self.selectedItems() if item.isVisible()]
        self._selection_order = [item for item in self._selection_order if item in selected]
        for item in selected:
            if item not in self._selection_order:
                self._selection_order.append(item)

    def ordered_selected_items(self):
        selected = [item for item in self.selectedItems() if item.isVisible()]
        ordered = [item for item in self._selection_order if item in selected]
        for item in selected:
            if item not in ordered:
                ordered.append(item)
        return ordered

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


    def _editor(self):
        try:
            return getattr(self.views()[0], 'editor', None) if self.views() else None
        except Exception:
            return None

    def _notify_graph_changed(self):
        editor = self._editor()
        if editor is not None and hasattr(editor, 'schedule_validation_update'):
            editor.schedule_validation_update()

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
        props = getattr(node_data, "properties", {}) or {}
        if isinstance(props, dict) and props.get("__zone_id"):
            try:
                node._zone_id = props.get("__zone_id")
            except Exception:
                pass
        self.addItem(node)
        node.setPos(QtCore.QPointF(node_data.x, node_data.y))
        self.ensure_logical_scene_rect(node.sceneBoundingRect())
        self._notify_graph_changed()
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
            dynamic_specs = (node_data.properties or {}).get("__dynamic_ports", [])
            if isinstance(dynamic_specs, list):
                dynamic_inputs = [str(spec.get("name") or "Data") for spec in dynamic_specs if isinstance(spec, dict) and spec.get("direction") == "input"]
                dynamic_outputs = [str(spec.get("name") or "Data") for spec in dynamic_specs if isinstance(spec, dict) and spec.get("direction") == "output"]
                if dynamic_inputs and "inputs" not in node_entry:
                    inputs = list(inputs or []) + dynamic_inputs
                if dynamic_outputs and "outputs" not in node_entry:
                    outputs = list(outputs or []) + dynamic_outputs
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
        props = getattr(node_data, "properties", {}) or {}
        if isinstance(props, dict) and props.get("__zone_id"):
            try:
                node._zone_id = props.get("__zone_id")
            except Exception:
                pass
        if select_new:
            self.clearSelection()
            node.setSelected(True)
        return node

    def create_connection(self, source_port, target_port, route_points=None, connection_kind=None):
        if connection_kind is None:
            try:
                editor = getattr(self.views()[0], "editor", None) if self.views() else None
                if editor is not None and hasattr(editor, "_connection_kind_for_ports"):
                    connection_kind = editor._connection_kind_for_ports(source_port, target_port)
            except Exception:
                connection_kind = None
        conn = ConnectionItem(source_port=source_port, target_port=target_port, route_points=route_points or [], connection_kind=connection_kind)
        self.addItem(conn)
        # ConnectionItem builds its path before it belongs to a scene. Route-point pin
        # handles therefore need a second sync pass after the item has actually been
        # inserted into the scene so restored/undone connections re-create their bend
        # points visually as well as logically.
        conn.update_path()
        conn.sync_pin_items()
        conn.refresh_style()
        source_parent = getattr(getattr(source_port, 'parent_node', None), '_inline_subgraph_parent_id', None)
        target_parent = getattr(getattr(target_port, 'parent_node', None), '_inline_subgraph_parent_id', None)
        if source_parent and source_parent == target_parent:
            conn._inline_subgraph_display = True
            conn._inline_subgraph_parent_id = source_parent
        self.ensure_logical_scene_rect(conn.sceneBoundingRect())
        self._notify_graph_changed()
        return conn


    def create_projection_connection(self, source_port, target_port, route_points=None, connection_kind=None):
        """Create a render-only connection used by inline expanded subgraphs.

        Projection wires are not graph-model connections. They do not register
        with port connection lists, are not selectable, are skipped by
        serialization, and bypass single-input connection limits so the hidden
        real parent/container wire can coexist with the visual bridge.
        """
        if source_port is None or target_port is None:
            return None
        if connection_kind is None:
            try:
                editor = getattr(self.views()[0], "editor", None) if self.views() else None
                if editor is not None and hasattr(editor, "_connection_kind_for_ports"):
                    connection_kind = editor._connection_kind_for_ports(source_port, target_port)
            except Exception:
                connection_kind = None
        conn = ConnectionItem(
            source_port=source_port,
            target_port=target_port,
            route_points=route_points or [],
            connection_kind=connection_kind,
            register_with_ports=False,
            projection_mode=True,
        )
        conn._inline_subgraph_display = True
        self.addItem(conn)
        conn.update_path()
        conn.sync_pin_items()
        conn.refresh_style()
        source_parent = getattr(getattr(source_port, 'parent_node', None), '_inline_subgraph_parent_id', None)
        target_parent = getattr(getattr(target_port, 'parent_node', None), '_inline_subgraph_parent_id', None)
        if source_parent and source_parent == target_parent:
            conn._inline_subgraph_display = True
            conn._inline_subgraph_parent_id = source_parent
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

        if not self._editor_allows_connection(source_port, target_port):
            return None

        route_points = [QtCore.QPointF(x, y) for x, y in conn_data.get("route_points", [])]
        return self.create_connection(source_port, target_port, route_points=route_points, connection_kind=conn_data.get("connection_kind"))

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

    def _port_connection_kind(self, port):
        definition_port = getattr(port, "definition_port", None)
        if definition_port is None:
            return "data"
        resolver = getattr(definition_port, "resolved_connection_kind", None)
        if callable(resolver):
            try:
                return str(resolver() or "data").strip().lower() or "data"
            except Exception:
                pass
        explicit = getattr(definition_port, "connection_kind", None)
        if explicit:
            return str(explicit).strip().lower() or "data"
        data_type = str(getattr(definition_port, "data_type", "any") or "any").strip().lower()
        if data_type == "exec":
            return "exec"
        if data_type == "requirement":
            return "requirement"
        return "data"

    def _port_data_type(self, port):
        definition_port = getattr(port, "definition_port", None)
        if definition_port is None:
            return "any"
        return str(getattr(definition_port, "data_type", "any") or "any").strip() or "any"


    @staticmethod
    def _normal_data_type_token(value):
        value = str(value or "any").strip()
        aliases = {"string": "str", "boolean": "bool", "integer": "int", "double": "float", "none": "NoneType", "object": "complex"}
        return aliases.get(value.lower(), value).lower()

    def _local_data_ports_compatible(self, source_port, target_port):
        source_kind = self._port_connection_kind(source_port)
        target_kind = self._port_connection_kind(target_port)
        if source_kind != target_kind:
            return False
        if source_kind != "data":
            return True
        source_type = self._normal_data_type_token(self._port_data_type(source_port))
        target_type = self._normal_data_type_token(self._port_data_type(target_port))
        if source_type in ("", "any", "*") or target_type in ("", "any", "*"):
            return True
        return source_type == target_type

    def _input_port_allows_another_connection(self, target_port, connection_to_ignore=None):
        if target_port is None or target_port.port_type != PortItem.INPUT:
            return True
        definition_port = getattr(target_port, "definition_port", None)
        if bool(getattr(definition_port, "multi_connection", False)):
            return True
        for connection in list(getattr(target_port, "connections", []) or []):
            if connection_to_ignore is not None and connection is connection_to_ignore:
                continue
            return False
        return True

    def _port_belongs_to_inline_projection(self, port):
        node = getattr(port, 'parent_node', None)
        return bool(getattr(node, '_inline_subgraph_display', False))

    def _is_inline_boundary_port(self, port):
        node = getattr(port, 'parent_node', None)
        return bool(getattr(node, '_inline_boundary_interface', False))

    def _editor_allows_connection(self, source_port, target_port, connection_to_ignore=None):
        # Inline-expanded subgraphs are editable child scopes.  Real user
        # connections are allowed only when both endpoints belong to the same
        # expanded container. Projection/bridge wires created by the editor are
        # still permitted while the preview flag is active.
        source_inline = self._port_belongs_to_inline_projection(source_port)
        target_inline = self._port_belongs_to_inline_projection(target_port)
        if source_inline or target_inline:
            if bool(getattr(self, '_allow_inline_preview_connections', False)):
                pass
            else:
                source_parent = getattr(getattr(source_port, 'parent_node', None), '_inline_subgraph_parent_id', None)
                target_parent = getattr(getattr(target_port, 'parent_node', None), '_inline_subgraph_parent_id', None)
                boundary_external = (self._is_inline_boundary_port(source_port) != self._is_inline_boundary_port(target_port))
                same_child_scope = bool(source_parent and target_parent and source_parent == target_parent)
                if not (same_child_scope or boundary_external):
                    return False
        # Boundary-interface ports in an expanded subgraph are visual adapters.
        # Validate them through their real backing model ports so graph/view rules
        # do not reject the proxy node type or proxy scope.
        source_boundary = self._is_inline_boundary_port(source_port)
        target_boundary = self._is_inline_boundary_port(target_port)

        validation_source, validation_target = source_port, target_port
        views = self.views()
        editor = getattr(views[0], "editor", None) if views else None
        if editor is not None and hasattr(editor, 'normalize_inline_boundary_connection_ports'):
            try:
                validation_source, validation_target = editor.normalize_inline_boundary_connection_ports(source_port, target_port)
            except Exception:
                validation_source, validation_target = source_port, target_port

        # Expanded boundary-interface ports are adapter endpoints.  Let the
        # adapter path validate them by direction/cardinality and resolve the
        # persisted model endpoint on release.  Do not require proxy ports to
        # have a perfect definition_port match here; when that lookup fails the
        # normal data/exec comparison treats exec proxies as generic data ports
        # and incorrectly turns the preview red.
        if source_boundary or target_boundary:
            normalized_source, normalized_target = self._normalized_connection_ports(source_port, target_port)
            if normalized_source is None or normalized_target is None:
                return False
            # Resolve the visible target when possible for single-input
            # cardinality, but tolerate missing backing definitions because the
            # boundary adapter creates the actual graph/subgraph connection.
            check_target = validation_target if validation_target is not None else normalized_target
            if not self._input_port_allows_another_connection(check_target, connection_to_ignore=connection_to_ignore):
                return False
            return True

        if not self._local_data_ports_compatible(validation_source, validation_target):
            return False
        if not self._input_port_allows_another_connection(validation_target, connection_to_ignore=connection_to_ignore):
            return False

        if not views:
            return True
        if editor is None or not hasattr(editor, "allows_connection_between_ports"):
            return True
        return bool(editor.allows_connection_between_ports(validation_source, validation_target, connection_to_ignore=connection_to_ignore))

    def _normalized_connection_ports(self, first_port, second_port):
        """Return (source_output_port, target_input_port) for either drag direction.

        Users can start a wire from an input or an output. The persisted graph
        model still stores canonical output -> input connections.
        """
        if first_port is None or second_port is None:
            return None, None
        if first_port.port_type == PortItem.OUTPUT and second_port.port_type == PortItem.INPUT:
            return first_port, second_port
        if first_port.port_type == PortItem.INPUT and second_port.port_type == PortItem.OUTPUT:
            return second_port, first_port
        return None, None

    def _boundary_port_alternates(self, port):
        """Return co-located boundary adapter ports for the same logical interface."""
        node = getattr(port, 'parent_node', None)
        if node is None or not getattr(node, '_inline_boundary_interface', False):
            return []
        name = str(getattr(port, 'name', '') or '')
        alternates = []
        for candidate in list(getattr(node, 'inputs', []) or []) + list(getattr(node, 'outputs', []) or []):
            if candidate is port:
                continue
            if str(getattr(candidate, 'name', '') or '') == name:
                alternates.append(candidate)
        return alternates

    def _best_boundary_port_for_connection(self, source_port, target_port):
        """Resolve an overlapped expanded-boundary hit to a valid sibling port."""
        if target_port is None:
            return None
        candidates = [target_port] + self._boundary_port_alternates(target_port)
        for candidate in candidates:
            normalized_source, normalized_target = self._normalized_connection_ports(source_port, candidate)
            if normalized_source is None or normalized_target is None:
                continue
            if self._editor_allows_connection(normalized_source, normalized_target):
                return candidate
        return None

    def _connection_candidate_ports(self, port):
        if port is None:
            return []
        return [port] + self._boundary_port_alternates(port)

    def _boundary_adapter_connection_data_exists(self, source_port, target_port):
        source_boundary = self._is_inline_boundary_port(source_port)
        target_boundary = self._is_inline_boundary_port(target_port)
        if not (source_boundary or target_boundary):
            return True
        views = self.views()
        editor = getattr(views[0], "editor", None) if views else None
        if editor is None or not hasattr(editor, 'inline_boundary_connection_data_for_ports'):
            return False
        normalized_source, normalized_target = self._normalized_connection_ports(source_port, target_port)
        if normalized_source is None or normalized_target is None:
            return False
        try:
            data = editor.inline_boundary_connection_data_for_ports(normalized_source, normalized_target, None)
        except Exception:
            data = None
        return bool(data)

    def _best_connection_ports_for_drag(self, first_port, second_port):
        """Resolve overlapped expanded-boundary ports on both drag ends.

        Boundary interface labels intentionally expose parent-facing and
        child-facing adapter endpoints at the same visual location.  The correct
        adapter cannot be known until both endpoints are available, so evaluate
        source and target alternates together and keep only pairs that can
        actually produce model connection data.
        """
        for candidate_first in self._connection_candidate_ports(first_port):
            for candidate_second in self._connection_candidate_ports(second_port):
                normalized_source, normalized_target = self._normalized_connection_ports(candidate_first, candidate_second)
                if normalized_source is None or normalized_target is None:
                    continue
                if not self._boundary_adapter_connection_data_exists(normalized_source, normalized_target):
                    continue
                if self._editor_allows_connection(normalized_source, normalized_target):
                    return normalized_source, normalized_target
        return None, None

    def _is_valid_connection_target(self, source_port, target_port):
        normalized_source, normalized_target = self._best_connection_ports_for_drag(source_port, target_port)
        return (
            normalized_source is not None and normalized_target is not None and
            self._editor_allows_connection(normalized_source, normalized_target)
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
        if source_port is None or source_port.port_type not in (PortItem.INPUT, PortItem.OUTPUT):
            return
        # Do not coerce expanded-boundary proxy ports to OUTPUT at drag start.
        # A boundary label represents two adapter endpoints: the parent-facing
        # endpoint and the child-facing endpoint.  The correct one depends on
        # the port the user releases on, so source/target alternates are resolved
        # together during drag/update/end.
        self.cancel_endpoint_reconnect()
        self.clear_port_feedback()
        self.drag_source_port = source_port
        self.drag_target_port = None
        self.drag_visible_target_port = None
        self.drag_resolved_source_port = None
        self.drag_resolved_target_port = None
        preview_kwargs = {
            'temp_end_pos': source_port.scene_center(),
            'preview_mode': True,
            # Preview wires must not register with ports. When a drag starts
            # from an input port, registering the preview on that input makes
            # single-input cardinality validation think the port is already
            # occupied, so input -> output drags incorrectly fail.
            'register_with_ports': False,
        }
        if source_port.port_type == PortItem.OUTPUT:
            preview_kwargs['source_port'] = source_port
        else:
            preview_kwargs['target_port'] = source_port
        self.drag_connection = ConnectionItem(**preview_kwargs)
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
        chosen_source = self.drag_source_port
        resolved_pair_source = None
        resolved_pair_target = None
        if hovered_port is not None:
            resolved_source, resolved_hovered = self._best_connection_ports_for_drag(self.drag_source_port, hovered_port)
            if resolved_source is not None and resolved_hovered is not None:
                self._set_port_highlight(resolved_hovered, PortItem.STATE_VALID)
                if resolved_hovered is not hovered_port:
                    self._set_port_highlight(hovered_port, PortItem.STATE_VALID)
                chosen_source = resolved_source
                chosen_port = resolved_hovered
                resolved_pair_source = resolved_source
                resolved_pair_target = resolved_hovered
            else:
                self._set_port_highlight(hovered_port, PortItem.STATE_INVALID)
        if snap_port is not None:
            resolved_source, resolved_snap = self._best_connection_ports_for_drag(self.drag_source_port, snap_port)
            if resolved_source is not None and resolved_snap is not None:
                chosen_source = resolved_source
                chosen_port = resolved_snap
                resolved_pair_source = resolved_source
                resolved_pair_target = resolved_snap
                self._set_port_highlight(resolved_snap, PortItem.STATE_SNAP if resolved_snap is chosen_port else PortItem.STATE_VALID)
        self.drag_target_port = chosen_port
        # Preserve the concrete port under the cursor separately from the
        # resolved model pair.  Expanded boundary adapters can resolve a
        # boundary->internal drag into an internal->boundary model connection,
        # so chosen_port may become the boundary sibling while the user's actual
        # release target remains the internal node port.
        self.drag_visible_target_port = hovered_port or snap_port or chosen_port
        self.drag_resolved_source_port = resolved_pair_source
        self.drag_resolved_target_port = resolved_pair_target

        # Boundary adapter ports are dual-natured: the same visible dot can
        # represent the parent-facing container port or the child-facing
        # Start/End adapter.  The logical resolved pair may therefore reverse
        # direction relative to the user's drag.  Keep the *preview* anchored
        # to the port the user actually grabbed so boundary -> internal drags
        # draw toward the cursor/internal node instead of snapping back through
        # the resolved internal -> boundary model pair.  The resolved pair is
        # still stored above and used by end_connection_drag() for persistence.
        preview_anchor = self.drag_source_port
        preview_target_pos = scene_pos
        if hovered_port is not None:
            preview_target_pos = hovered_port.scene_center()
        elif chosen_port is not None and not self._is_inline_boundary_port(preview_anchor):
            preview_target_pos = chosen_port.scene_center()

        self.drag_connection.preview_valid = chosen_port is not None
        self.drag_connection.setVisible(True)
        self.drag_connection.set_route_points([])
        self.drag_connection.setSelected(False)
        if preview_anchor is not None and preview_anchor.port_type == PortItem.OUTPUT:
            self.drag_connection.source_port = preview_anchor
            self.drag_connection.target_port = None
        else:
            self.drag_connection.source_port = None
            self.drag_connection.target_port = preview_anchor
        self.drag_connection.temp_end_pos = QtCore.QPointF(preview_target_pos)
        self.drag_connection.refresh_style()
        self.drag_connection.update_path()

    def end_connection_drag(self, target_item=None):
        if not self.drag_connection or not self.drag_source_port:
            return

        chosen_target = self.drag_resolved_target_port or self.drag_target_port
        resolved_source_for_end = self.drag_resolved_source_port or self.drag_source_port
        visible_target_for_end = getattr(self, 'drag_visible_target_port', None)

        # If the user released over a concrete port, resolve against that raw
        # release port first.  This is especially important for boundary ->
        # internal drags: the live preview stores the resolved model pair as
        # internal -> boundary, but the visible target under the cursor is the
        # internal node.  Re-resolving with the raw release port keeps the final
        # connection symmetric with internal -> boundary drags.
        if isinstance(target_item, PortItem):
            visible_target_for_end = target_item
            pair_source, pair_target = self._best_connection_ports_for_drag(self.drag_source_port, target_item)
            if pair_source is not None and pair_target is not None:
                resolved_source_for_end = pair_source
                chosen_target = pair_target
        if chosen_target is None and isinstance(target_item, PortItem):
            pair_source, pair_target = self._best_connection_ports_for_drag(self.drag_source_port, target_item)
            if pair_source is not None and pair_target is not None:
                resolved_source_for_end = pair_source
                chosen_target = pair_target
        elif chosen_target is not None:
            pair_source, pair_target = self._best_connection_ports_for_drag(self.drag_source_port, chosen_target)
            if pair_source is not None and pair_target is not None:
                resolved_source_for_end = pair_source
                chosen_target = pair_target

        drag_conn = self.drag_connection
        self.drag_connection = None
        self.drag_target_port = None
        self.drag_visible_target_port = None
        self.drag_resolved_source_port = None
        self.drag_resolved_target_port = None
        self.clear_port_feedback()

        connection_data = None
        raw_release_target = target_item if isinstance(target_item, PortItem) else (visible_target_for_end or chosen_target)

        # Fast-path direct expanded-boundary drags against child-scope ports.
        # This avoids the dual-port adapter ambiguity where the visible boundary
        # dot resolves to its sibling model endpoint and the final release path
        # loses the actual internal port under the cursor.
        if isinstance(raw_release_target, PortItem):
            try:
                editor = getattr(self.views()[0], "editor", None) if self.views() else None
            except Exception:
                editor = None
            if editor is not None and hasattr(editor, 'consume_inline_boundary_direct_drag'):
                try:
                    if editor.consume_inline_boundary_direct_drag(self.drag_source_port, raw_release_target):
                        drag_conn.remove_from_ports()
                        self.removeItem(drag_conn)
                        self.drag_source_port = None
                        return
                except Exception:
                    pass
        if chosen_target is not None and self._is_valid_connection_target(resolved_source_for_end, chosen_target):
            connection_kind = None
            try:
                editor = getattr(self.views()[0], "editor", None) if self.views() else None
                if editor is not None and hasattr(editor, "_connection_kind_for_ports"):
                    connection_kind = editor._connection_kind_for_ports(resolved_source_for_end, chosen_target)
            except Exception:
                connection_kind = None
            normalized_source, normalized_target = self._normalized_connection_ports(resolved_source_for_end, chosen_target)
            if normalized_source is None or normalized_target is None:
                connection_data = None
            else:
                # Boundary ports are adapters.  Ask the editor for their model
                # connection using the raw visible boundary endpoint before
                # normalizing it to a hidden container/Start/End port; otherwise
                # the boundary identity is lost and child/parent adapter writes
                # can fall back to the wrong generic connection path.
                try:
                    editor = getattr(self.views()[0], "editor", None) if self.views() else None
                    if editor is not None and hasattr(editor, 'inline_boundary_connection_data_for_ports'):
                        connection_data = editor.inline_boundary_connection_data_for_ports(normalized_source, normalized_target, connection_kind)
                except Exception:
                    connection_data = None
                try:
                    editor = getattr(self.views()[0], "editor", None) if self.views() else None
                    if editor is not None and hasattr(editor, 'normalize_inline_boundary_connection_ports'):
                        normalized_source, normalized_target = editor.normalize_inline_boundary_connection_ports(normalized_source, normalized_target)
                except Exception:
                    pass
                if not connection_kind:
                    try:
                        source_def = getattr(normalized_source, "definition_port", None)
                        target_def = getattr(normalized_target, "definition_port", None)
                        source_kind = source_def.resolved_connection_kind() if source_def and hasattr(source_def, "resolved_connection_kind") else None
                        target_kind = target_def.resolved_connection_kind() if target_def and hasattr(target_def, "resolved_connection_kind") else None
                        connection_kind = source_kind if source_kind == target_kind else None
                    except Exception:
                        connection_kind = None
                if connection_data is None:
                    try:
                        editor = getattr(self.views()[0], "editor", None) if self.views() else None
                        if editor is not None and hasattr(editor, 'inline_boundary_connection_data_for_ports'):
                            connection_data = editor.inline_boundary_connection_data_for_ports(normalized_source, normalized_target, connection_kind)
                    except Exception:
                        connection_data = None
                if connection_data is None:
                    connection_data = GraphConnectionData(
                        normalized_source.parent_node.node_data.node_id,
                        normalized_source.name,
                        normalized_target.parent_node.node_data.node_id,
                        normalized_target.name,
                        [],
                        connection_kind=connection_kind,
                    ).to_dict()

        # Fallback for expanded-boundary drags that start from the visible
        # boundary adapter and release on the child/internal source port.  In
        # that direction Qt can preserve the originally pressed boundary port
        # as the drag source, while the normal target validation path never
        # fully resolves the sibling child-facing adapter endpoint.  Evaluate
        # all co-located boundary alternates at release and ask the editor for
        # an adapter-backed model connection directly.  This keeps boundary ->
        # internal drags symmetric with internal -> boundary drags without
        # weakening ordinary graph validation.
        if connection_data is None and isinstance(raw_release_target, PortItem):
            try:
                editor = getattr(self.views()[0], "editor", None) if self.views() else None
            except Exception:
                editor = None
            if editor is not None and hasattr(editor, 'inline_boundary_connection_data_for_ports'):
                for first_candidate in self._connection_candidate_ports(self.drag_source_port):
                    for second_candidate in self._connection_candidate_ports(raw_release_target):
                        normalized_source, normalized_target = self._normalized_connection_ports(first_candidate, second_candidate)
                        if normalized_source is None or normalized_target is None:
                            continue
                        if not (self._is_inline_boundary_port(normalized_source) or self._is_inline_boundary_port(normalized_target)):
                            continue
                        try:
                            fallback_kind = None
                            if hasattr(editor, '_connection_kind_for_ports'):
                                fallback_kind = editor._connection_kind_for_ports(normalized_source, normalized_target)
                        except Exception:
                            fallback_kind = None
                        try:
                            fallback_data = editor.inline_boundary_connection_data_for_ports(normalized_source, normalized_target, fallback_kind)
                        except Exception:
                            fallback_data = None
                        if fallback_data:
                            connection_data = fallback_data
                            break
                    if connection_data is not None:
                        break

        drag_conn.remove_from_ports()
        self.removeItem(drag_conn)

        if connection_data:
            consumed_inline = False
            try:
                editor = getattr(self.views()[0], "editor", None) if self.views() else None
                if editor is not None and hasattr(editor, 'consume_inline_boundary_connection_data'):
                    consumed_inline = bool(editor.consume_inline_boundary_connection_data(connection_data))
            except Exception:
                consumed_inline = False
            if consumed_inline:
                connection_data = None
            elif self.undo_stack is not None and not self._suspend_undo:
                self.undo_stack.push(AddConnectionCommand(self, connection_data))
            else:
                self.add_connection_from_dict(connection_data)
            try:
                editor = getattr(self.views()[0], "editor", None) if self.views() else None
                if editor is not None:
                    if hasattr(editor, '_hide_real_connections_for_expanded_containers'):
                        editor._hide_real_connections_for_expanded_containers()
                    if hasattr(editor, '_refresh_inline_projection_connections'):
                        editor._refresh_inline_projection_connections()
                    for cid in list((getattr(editor, '_inline_subgraph_expansions', {}) or {}).keys()):
                        editor._refresh_inline_expansion_bounds(cid)
            except Exception:
                pass

        self.drag_source_port = None
        self.drag_resolved_source_port = None
        self.drag_resolved_target_port = None

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
                source_for_kind = chosen_port
                target_for_kind = connection.target_port
            else:
                new_data["target_node_id"] = chosen_port.parent_node.node_data.node_id
                new_data["target_port_name"] = chosen_port.name
                source_for_kind = connection.source_port
                target_for_kind = chosen_port
            try:
                editor = getattr(self.views()[0], "editor", None) if self.views() else None
                if editor is not None and hasattr(editor, "_connection_kind_for_ports"):
                    new_data["connection_kind"] = editor._connection_kind_for_ports(source_for_kind, target_for_kind)
            except Exception:
                pass
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
        if getattr(connection, 'is_projection', False):
            # Expanded-subgraph projection wires are stand-ins for hidden model
            # wires. Let users add bend points immediately on the visible wire;
            # model persistence is handled by the owning expansion refresh/collapse
            # path rather than the normal scene connection lookup.
            connection.set_route_points(new_route_points)
            connection.setSelected(True)
            target_connection = connection
        else:
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
        if getattr(connection, 'is_projection', False):
            connection.set_route_points(new_route_points)
            connection.setSelected(True)
            return
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

        if getattr(connection, 'is_projection', False):
            connection.set_route_points(new_route_points)
            connection.setSelected(True)
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
            if isinstance(item, (NodeItem, ZoneBoundaryItem)) and item.node_data.node_id == node_id:
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
            if not isinstance(item, ConnectionItem) or getattr(item, 'is_projection', False):
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
            self._notify_graph_changed()

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
        self._notify_graph_changed()

    def snapshot_items_for_delete(self, selected_items):
        node_items = {item for item in selected_items if isinstance(item, NodeItem)}
        connection_items = {item for item in selected_items if isinstance(item, ConnectionItem) and not getattr(item, 'is_projection', False)}

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


    def clear_path_highlighting(self):
        for item in self.items():
            if isinstance(item, NodeItem) and hasattr(item, 'set_path_highlight_state'):
                item.set_path_highlight_state('normal')
            elif isinstance(item, ConnectionItem) and hasattr(item, 'set_path_highlight_state'):
                item.set_path_highlight_state('normal')

    def clear_validation_feedback(self):
        for item in self.items():
            if isinstance(item, NodeItem) and hasattr(item, 'set_validation_feedback'):
                item.set_validation_feedback(None, [])
            elif isinstance(item, ConnectionItem) and hasattr(item, 'set_validation_feedback'):
                item.set_validation_feedback(None, [])

    def apply_validation_issues(self, issues):
        self.clear_validation_feedback()
        ranked = {'error': 2, 'warning': 1, None: 0}
        node_state = {}
        node_messages = {}
        conn_state = {}
        conn_messages = {}
        for issue in issues or []:
            state = getattr(issue, 'state', None) or getattr(issue, 'severity', None) or 'warning'
            state = 'error' if str(state).lower() == 'error' else 'warning'
            message = str(getattr(issue, 'message', '') or '')
            for node in getattr(issue, 'nodes', []) or []:
                if node is None:
                    continue
                if ranked[state] > ranked.get(node_state.get(node), 0):
                    node_state[node] = state
                if message:
                    node_messages.setdefault(node, []).append(message)
            for conn in getattr(issue, 'connections', []) or []:
                if conn is None:
                    continue
                if ranked[state] > ranked.get(conn_state.get(conn), 0):
                    conn_state[conn] = state
                if message:
                    conn_messages.setdefault(conn, []).append(message)
        for node, state in node_state.items():
            if hasattr(node, 'set_validation_feedback'):
                node.set_validation_feedback(state, node_messages.get(node, []))
        for conn, state in conn_state.items():
            if hasattr(conn, 'set_validation_feedback'):
                conn.set_validation_feedback(state, conn_messages.get(conn, []))

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
            elif isinstance(item, ConnectionItem) and not getattr(item, 'is_projection', False):
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
        editor = self._editor()
        if editor is not None and hasattr(editor, '_after_graph_loaded'):
            editor._after_graph_loaded()
        self._notify_graph_changed()

    def handle_node_moved(self, node_item, old_pos, new_pos):
        if old_pos == new_pos or self.undo_stack is None:
            return
        # Programmatic group moves, including live zone drag/reflow, set
        # _suspend_undo while they update actual item positions. Do not run
        # membership/resize refreshes or enqueue per-node undo commands during
        # those internal layout transactions; the caller owns the coherent
        # boundary/content update.
        if bool(getattr(self, '_suspend_undo', False)):
            return
        editor = self._editor()
        if editor is not None and hasattr(editor, '_update_zone_membership_for_node'):
            editor._update_zone_membership_for_node(node_item)
        if editor is not None and hasattr(editor, 'refresh_all_zone_bounds'):
            editor.refresh_all_zone_bounds()
        self.undo_stack.push(MoveNodeCommand(node_item, old_pos, new_pos))
