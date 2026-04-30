# ============================================================================
# Nexus
# File: plugins/owner/NoDELite/node_plugin/tool.py
# Description: Primary tool implementation for NoDE Lite Plugin.
# Part of: NoDE Lite Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================

import json
import csv
import os
import uuid
from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets
from nexus_workspace.core.serialization import NexusSerializable
from nexus_workspace.core.themes import build_stylesheet, get_theme_colors
from nexus_workspace.core.selection_contract import SELECTION_CURRENT_CONTRACT, SelectionPublisher
from nexus_workspace.core.inspectable_contract import build_field_descriptor, build_inspectable_object, build_section
from nexus_workspace.core.action_contract import ACTION_STATUS_HANDLED, ACTION_STATUS_UNHANDLED, PROPERTY_EDIT_REQUEST, normalize_action_request
from .view import GraphView
from .scene import GraphScene
from .commands import AddNodeCommand, DeleteItemsCommand, PasteItemsCommand, RenameNodeCommand, SetNodePropertyCommand
from .definitions import NODE_REGISTRY, NODE_DEFINITIONS_DIR, load_external_node_definitions, node_definition_for_type, create_node_entry
from .node_views import NODE_VIEW_MANIFESTS_DIR, NODE_VIEW_REGISTRY, NodeViewSession, NodeViewRules, load_node_views
from .graphics_items import NodeItem, ConnectionItem, ConnectionPinItem, InlineSubgraphBoundaryItem


class NoDELiteTool(QtWidgets.QMainWindow, NexusSerializable):
    selectionChanged = QtCore.pyqtSignal(object)
    titleChanged = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, theme_name="Midnight", editor_title="Untitled Graph", plugin_context=None):
        super().__init__(parent)
        self.setDockOptions(
            QtWidgets.QMainWindow.AllowNestedDocks |
            QtWidgets.QMainWindow.AllowTabbedDocks |
            QtWidgets.QMainWindow.GroupedDragging
        )
        self.setDocumentMode(True)
        self.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtWidgets.QTabWidget.North)

        self._build_central_surfaces()

        self.scene = GraphScene(theme_name=theme_name, parent=self)
        self.graphView.setScene(self.scene)
        self.graphView.setFocus()

        self.undo_stack = QtWidgets.QUndoStack(self)
        self.scene.undo_stack = self.undo_stack

        self.selected_node_item = None
        self._updating_property_panel = False
        self._property_title_before_edit = ""
        self._dock_tab_refresh_pending = False
        self._editor_title = editor_title
        self.current_file_path = None
        self._clipboard_mime_type = 'application/x-nexus-node-selection+json'
        self._paste_sequence = 0
        self._graph_menu = None
        self.plugin_context = plugin_context
        self._edit_menu = None
        self._initial_fit_pending = True
        self._theme_applied_once = False
        self._node_view_session = NodeViewSession(NODE_REGISTRY, NODE_VIEW_REGISTRY, select_default_on_reset=False)
        self._active_node_view_id = self._node_view_session.active_view_id()
        self._selection_publisher = SelectionPublisher(plugin_context=plugin_context, tool=self, plugin_id='NoDELite')
        self._action_handler_scope = None
        self._graph_context_stack = []
        self._root_graph_data = None
        self._inline_subgraph_expansions = {}

        self._connect_action_requests()
        self._build_local_menus()
        self._build_local_panels()
        self._apply_view_header_styles()
        self._apply_active_node_view_registry()
        self._refresh_node_view_ui()
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.editNodeTitle.textEdited.connect(self.on_node_title_edited)
        self.editNodeTitle.editingFinished.connect(self.commit_node_title_edit)
        self.setWindowTitle(editor_title)
        self.clear_property_panel()

    def _connect_action_requests(self):
        if self.plugin_context is None or self._action_handler_scope is not None:
            return
        self._action_handler_scope = self.plugin_context.create_action_handler_scope()
        if self._action_handler_scope is None:
            return
        self._action_handler_scope.register(
            action_type=PROPERTY_EDIT_REQUEST,
            callback=self._on_action_requested,
            plugin_id='NoDELite',
            target_kind='node',
            target_contract=SELECTION_CURRENT_CONTRACT,
            name=f"NoDE:{id(self)}:property_edit",
        )

    def _on_action_requested(self, payload):
        if not isinstance(payload, dict):
            return {'handled': False}
        payload = normalize_action_request(payload)
        if payload.get('action_type') != PROPERTY_EDIT_REQUEST:
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        target = payload.get('target') or {}
        if target.get('source_plugin') != 'NoDE':
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        if self.selected_node_item is None:
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        if target.get('selection_id') != self.selected_node_item.node_data.node_id:
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        action_payload = payload.get('payload') if isinstance(payload.get('payload'), dict) else {}
        return self._apply_property_edit_request(target, action_payload.get('value', payload.get('value')))

    def _apply_property_edit_request(self, target, value):
        field_path = str((target or {}).get('field_path') or '')
        if not field_path.startswith('properties.'):
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        property_name = field_path.split('.', 1)[1]
        if not property_name:
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        node_item = self.selected_node_item
        if node_item is None:
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        if property_name in {'node_type', 'position_x', 'position_y'}:
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        if property_name == 'title':
            old_title = node_item.node_data.title
            new_title = '' if value is None else str(value)
            if new_title == old_title:
                return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
            self.undo_stack.push(RenameNodeCommand(node_item, old_title, new_title))
            self.set_editor_title(new_title)
            return {'handled': True, 'status': ACTION_STATUS_HANDLED, 'data': {'field_path': field_path, 'property_name': property_name}}
        old_value = node_item.node_data.properties.get(property_name)
        if old_value == value:
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        self.undo_stack.push(SetNodePropertyCommand(node_item, property_name, old_value, value))
        return {'handled': True, 'status': ACTION_STATUS_HANDLED, 'data': {'field_path': field_path, 'property_name': property_name}}

    def on_node_mutated(self, node_item, update_editor_title=False):
        if node_item is None:
            return
        if self.selected_node_item is node_item:
            self.populate_property_panel(node_item)
            self._publish_selection_to_data_store(node_item)
        if update_editor_title:
            self.set_editor_title(node_item.node_data.title)

    def _build_central_surfaces(self):
        self.graphView = GraphView(self, editor=self)
        self.graphView.setObjectName("graphView")

        self._editorSurface = QtWidgets.QWidget(self)
        self._editorSurface.setObjectName("nodeEditorSurface")
        editor_layout = QtWidgets.QVBoxLayout(self._editorSurface)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self._viewHeaderFrame = QtWidgets.QFrame(self._editorSurface)
        self._viewHeaderFrame.setObjectName("nodeViewHeaderFrame")
        header_layout = QtWidgets.QHBoxLayout(self._viewHeaderFrame)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(10)

        self._viewHeaderLabel = QtWidgets.QLabel("NoDE View", self._viewHeaderFrame)
        self._viewHeaderLabel.setObjectName("nodeViewHeaderLabel")

        self._viewHeaderNameBadge = QtWidgets.QLabel("Not Selected", self._viewHeaderFrame)
        self._viewHeaderNameBadge.setObjectName("nodeViewHeaderNameBadge")
        self._viewHeaderNameBadge.setAlignment(QtCore.Qt.AlignCenter)

        self._viewHeaderStateBadge = QtWidgets.QLabel("Select a view to begin", self._viewHeaderFrame)
        self._viewHeaderStateBadge.setObjectName("nodeViewHeaderStateBadge")
        self._viewHeaderStateBadge.setAlignment(QtCore.Qt.AlignCenter)

        self._viewHeaderDescriptionLabel = QtWidgets.QLabel("", self._viewHeaderFrame)
        self._viewHeaderDescriptionLabel.setObjectName("nodeViewHeaderDescriptionLabel")
        self._viewHeaderDescriptionLabel.setWordWrap(True)
        self._viewHeaderDescriptionLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self._subgraphBackButton = QtWidgets.QPushButton("Back to Parent", self._viewHeaderFrame)
        self._subgraphBackButton.setObjectName("nodeSubgraphBackButton")
        self._subgraphBackButton.clicked.connect(self.close_current_subgraph)
        self._subgraphBackButton.hide()

        self._subgraphPathLabel = QtWidgets.QLabel("", self._viewHeaderFrame)
        self._subgraphPathLabel.setObjectName("nodeSubgraphPathLabel")
        self._subgraphPathLabel.setAlignment(QtCore.Qt.AlignCenter)
        self._subgraphPathLabel.hide()

        header_layout.addWidget(self._viewHeaderLabel, 0)
        header_layout.addWidget(self._viewHeaderNameBadge, 0)
        header_layout.addWidget(self._viewHeaderStateBadge, 0)
        header_layout.addWidget(self._viewHeaderDescriptionLabel, 1)
        header_layout.addWidget(self._subgraphPathLabel, 0)
        header_layout.addWidget(self._subgraphBackButton, 0)
        editor_layout.addWidget(self._viewHeaderFrame, 0)
        editor_layout.addWidget(self.graphView, 1)

        self._viewSelectionSurface = QtWidgets.QWidget(self)
        self._viewSelectionSurface.setObjectName("nodeViewSelectionSurface")
        selection_layout = QtWidgets.QVBoxLayout(self._viewSelectionSurface)
        selection_layout.setContentsMargins(48, 40, 48, 40)
        selection_layout.setSpacing(20)
        selection_layout.addStretch(1)

        self._viewSelectionCard = QtWidgets.QFrame(self._viewSelectionSurface)
        self._viewSelectionCard.setObjectName("nodeViewSelectionCard")
        self._viewSelectionCard.setMinimumWidth(520)
        self._viewSelectionCard.setMaximumWidth(640)
        self._viewSelectionCard.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        card_layout = QtWidgets.QVBoxLayout(self._viewSelectionCard)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(16)

        title = QtWidgets.QLabel("Select a NoDE View", self._viewSelectionCard)
        title.setObjectName("nodeViewSelectionTitle")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title_font = title.font()
        title_font.setPointSize(max(title_font.pointSize(), 13))
        title_font.setBold(True)
        title.setFont(title_font)
        title.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        card_layout.addWidget(title)

        description = QtWidgets.QLabel(
            "Choose a view before opening the graph canvas. The selected view determines which node definitions are available for this graph.",
            self._viewSelectionCard,
        )
        description.setWordWrap(True)
        description.setAlignment(QtCore.Qt.AlignCenter)
        description.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        description.setMinimumHeight(56)
        card_layout.addWidget(description)

        self._viewSelectionCombo = QtWidgets.QComboBox(self._viewSelectionCard)
        self._viewSelectionCombo.setMinimumHeight(34)
        combo_font = self._viewSelectionCombo.font()
        combo_font.setPointSize(max(combo_font.pointSize(), 10))
        self._viewSelectionCombo.setFont(combo_font)
        card_layout.addWidget(self._viewSelectionCombo)

        self._viewSelectionDescription = QtWidgets.QLabel("", self._viewSelectionCard)
        self._viewSelectionDescription.setWordWrap(True)
        self._viewSelectionDescription.setAlignment(QtCore.Qt.AlignCenter)
        self._viewSelectionDescription.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        self._viewSelectionDescription.setMinimumHeight(48)
        card_layout.addWidget(self._viewSelectionDescription)

        self._viewSelectionButton = QtWidgets.QPushButton("Open Graph in Selected View", self._viewSelectionCard)
        self._viewSelectionButton.setMinimumHeight(38)
        button_font = self._viewSelectionButton.font()
        button_font.setPointSize(max(button_font.pointSize(), 10))
        self._viewSelectionButton.setFont(button_font)
        self._viewSelectionButton.clicked.connect(self._confirm_initial_node_view_selection)
        card_layout.addWidget(self._viewSelectionButton)

        self._viewSelectionCombo.currentIndexChanged.connect(self._update_view_selection_description)

        selection_layout.addWidget(self._viewSelectionCard, 0, QtCore.Qt.AlignCenter)
        selection_layout.addStretch(1)

        self._centralStack = QtWidgets.QStackedWidget(self)
        self._centralStack.addWidget(self._viewSelectionSurface)
        self._centralStack.addWidget(self._editorSurface)
        self.setCentralWidget(self._centralStack)

    def _graph_has_nodes(self):
        return any(isinstance(item, NodeItem) for item in self.scene.items())

    def _graph_has_content(self):
        return any(isinstance(item, (NodeItem, ConnectionItem)) for item in self.scene.items())

    def is_subgraph_container_node(self, node_item):
        definition = getattr(node_item, "definition", None)
        if definition is None:
            return False
        metadata = getattr(definition, "metadata", {}) or {}
        return bool(metadata.get("is_subgraph_container") or node_item.node_data.node_type == "flow.subgraph_container")

    def _default_subgraph_data(self, graph_name="Sub-Graph"):
        return {
            "metadata": {
                "active_node_view_id": self._active_node_view_id,
                "graph_kind": "subgraph",
                "graph_name": graph_name or "Sub-Graph",
            },
            "nodes": [
                create_node_entry("flow.start", pos=QtCore.QPointF(-240, 0), title="Start"),
                create_node_entry("flow.end", pos=QtCore.QPointF(240, 0), title="End"),
            ],
            "connections": [],
        }

    def _normalize_graph_control_flow_boundaries(self, graph_data):
        """Migrate legacy sub-graph boundary nodes to universal Start/End nodes."""
        if not isinstance(graph_data, dict):
            return graph_data
        for entry in graph_data.get("nodes", []) or []:
            node_data = entry.get("node_data", {}) if isinstance(entry, dict) else {}
            node_type = node_data.get("node_type")
            if node_type in ("flow.subgraph_input", "flow.start"):
                node_data["node_type"] = "flow.start"
                node_data["title"] = "Start"
                entry["inputs"] = []
                entry["outputs"] = ["Exec Out"]
            elif node_type in ("flow.subgraph_output", "flow.end"):
                node_data["node_type"] = "flow.end"
                node_data["title"] = "End"
                entry["inputs"] = ["Exec In"]
                entry["outputs"] = []
        return graph_data

    def _ensure_graph_control_flow_nodes(self, graph_data):
        graph_data = self._normalize_graph_control_flow_boundaries(graph_data or {"nodes": [], "connections": []})
        nodes = graph_data.setdefault("nodes", [])
        node_types = [((entry.get("node_data", {}) if isinstance(entry, dict) else {}).get("node_type")) for entry in nodes]
        if "flow.start" not in node_types:
            nodes.append(create_node_entry("flow.start", pos=QtCore.QPointF(-240, 0), title="Start"))
        if "flow.end" not in node_types:
            nodes.append(create_node_entry("flow.end", pos=QtCore.QPointF(240, 0), title="End"))
        graph_data.setdefault("connections", [])
        return graph_data

    def _ensure_current_graph_control_flow_nodes(self):
        if self.active_node_view() is None or self._graph_has_content():
            return False
        graph_data = self._ensure_graph_control_flow_nodes({"nodes": [], "connections": []})
        self.scene._suspend_undo = True
        try:
            self.scene.load_graph(self._ensure_graph_control_flow_nodes(graph_data))
        finally:
            self.scene._suspend_undo = False
        self.undo_stack.clear()
        self._initial_fit_pending = True
        QtCore.QTimer.singleShot(0, self._ensure_initial_fit)
        return True

    def _find_node_properties_in_graph(self, graph_data, node_id):
        if not isinstance(graph_data, dict):
            return None
        for entry in graph_data.get("nodes", []) or []:
            data = entry.get("node_data", {}) if isinstance(entry, dict) else {}
            if data.get("node_id") == node_id:
                return data.setdefault("properties", {})
        return None

    def _save_current_graph_context(self):
        self.collapse_all_inline_subgraphs()
        current_graph = self.scene.serialize_graph()
        metadata = current_graph.setdefault("metadata", {})
        metadata["active_node_view_id"] = self._active_node_view_id
        if self._graph_context_stack:
            context = self._graph_context_stack[-1]
            context["node_properties"]["subgraph"] = current_graph
            context["node_properties"].setdefault("graph_name", metadata.get("graph_name", "Sub-Graph"))
        else:
            self._root_graph_data = current_graph
        return current_graph

    def _load_graph_context(self, graph_data):
        self.collapse_all_inline_subgraphs()
        self.scene._suspend_undo = True
        try:
            self.scene.load_graph(self._ensure_graph_control_flow_nodes(graph_data or {"nodes": [], "connections": []}))
        finally:
            self.scene._suspend_undo = False
        self.undo_stack.clear()
        self.selected_node_item = None
        self.clear_property_panel()
        self._refresh_node_view_ui()
        self._initial_fit_pending = True
        QtCore.QTimer.singleShot(0, self._ensure_initial_fit)

    def open_subgraph_for_node(self, node_item):
        if not self.is_subgraph_container_node(node_item):
            self.open_properties_for_node(node_item)
            return False
        parent_graph = self._save_current_graph_context()
        node_properties = self._find_node_properties_in_graph(parent_graph, node_item.node_data.node_id) or node_item.node_data.properties
        graph_name = node_properties.get("graph_name") or node_item.node_data.title or "Sub-Graph"
        subgraph = node_properties.get("subgraph")
        if not isinstance(subgraph, dict) or not subgraph.get("nodes"):
            subgraph = self._default_subgraph_data(graph_name)
            node_properties["subgraph"] = subgraph
        context = {
            "node_id": node_item.node_data.node_id,
            "title": node_item.node_data.title,
            "node_properties": node_properties,
        }
        self._graph_context_stack.append(context)
        self._load_graph_context(subgraph)
        self._status_message("Opened sub-graph: %s" % graph_name, 3500)
        return True

    def close_current_subgraph(self):
        if not self._graph_context_stack:
            return False
        self._save_current_graph_context()
        self._graph_context_stack.pop()
        if self._graph_context_stack:
            parent_graph = self._graph_context_stack[-1]["node_properties"].get("subgraph", {})
        else:
            parent_graph = self._root_graph_data or {"nodes": [], "connections": []}
        self._load_graph_context(parent_graph)
        self._status_message("Returned to parent graph", 2500)
        return True

    def _current_subgraph_path(self):
        if not self._graph_context_stack:
            return ""
        labels = []
        for context in self._graph_context_stack:
            props = context.get("node_properties") or {}
            labels.append(str(props.get("graph_name") or context.get("title") or "Sub-Graph"))
        return " / ".join(labels)

    def _new_node_id(self, old_id, remap):
        if old_id not in remap:
            remap[old_id] = str(uuid.uuid4())
        return remap[old_id]

    def toggle_inline_subgraph_node(self, node_item):
        if node_item is None:
            return False
        node_id = node_item.node_data.node_id
        if node_id in self._inline_subgraph_expansions:
            return self.collapse_inline_subgraph(node_id)
        return self.expand_subgraph_node(node_item)

    def _reframe_visible_graph_after_layout_change(self):
        """Reframe after inline expansion/collapse changes the visible layout."""
        view = getattr(self, "graphView", None)
        if view is None:
            return

        def _frame():
            try:
                if hasattr(view, "frame_visible_graph"):
                    view.frame_visible_graph()
                else:
                    view.frame_selected_or_all()
            except RuntimeError:
                pass

        QtCore.QTimer.singleShot(0, _frame)

    def expand_subgraph_node(self, node_item):
        """Visually expand a sub-graph inline without permanently flattening the model."""
        if not self.is_subgraph_container_node(node_item):
            return False
        container_id = node_item.node_data.node_id
        if container_id in self._inline_subgraph_expansions:
            return True
        subgraph = node_item.node_data.properties.get("subgraph")
        if not isinstance(subgraph, dict) or not subgraph.get("nodes"):
            subgraph = self._default_subgraph_data(node_item.node_data.properties.get("graph_name") or node_item.node_data.title)
            node_item.node_data.properties["subgraph"] = subgraph
        subgraph = self._ensure_graph_control_flow_nodes(subgraph)
        start_ids, end_ids, inner_nodes = set(), set(), []
        for entry in subgraph.get("nodes", []):
            data = entry.get("node_data", {}) if isinstance(entry, dict) else {}
            node_type = data.get("node_type")
            node_id = data.get("node_id")
            if node_type in ("flow.subgraph_input", "flow.start"):
                start_ids.add(node_id)
            elif node_type in ("flow.subgraph_output", "flow.end"):
                end_ids.add(node_id)
            else:
                inner_nodes.append(entry)
        if not inner_nodes:
            self._status_message("Sub-graph has no internal nodes between Start and End", 3500)
            return False
        xs = [float((e.get("node_data", {}) or {}).get("x", 0.0)) for e in inner_nodes]
        ys = [float((e.get("node_data", {}) or {}).get("y", 0.0)) for e in inner_nodes]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        content_w = max(360.0, (max_x - min_x) + 260.0)
        gap = 120.0
        shift_amount = content_w + gap
        anchor = node_item.scenePos() + QtCore.QPointF(node_item.boundingRect().width() + 120.0, 0.0)
        self.scene._suspend_undo = True
        # Inline expansion is a reversible visual transaction. Snapshot every
        # real node before any visual shifting so collapse can restore the exact
        # pre-expansion layout, including the original container node.
        original_positions = {}
        shifted_positions = {}
        created_nodes = []
        created_connections = []
        hidden_connections = []
        try:
            for item in list(self.scene.items()):
                if isinstance(item, NodeItem) and not getattr(item, '_inline_subgraph_display', False):
                    original_positions[item.node_data.node_id] = QtCore.QPointF(item.pos())
            threshold_x = node_item.sceneBoundingRect().right() + 20.0
            for item in list(self.scene.items()):
                if isinstance(item, NodeItem) and item is not node_item and not getattr(item, '_inline_subgraph_display', False):
                    if item.scenePos().x() > threshold_x:
                        shifted_positions[item.node_data.node_id] = QtCore.QPointF(item.pos())
                        item.setPos(item.pos() + QtCore.QPointF(shift_amount, 0.0))
            remap = {}
            for entry in inner_nodes:
                clone = json.loads(json.dumps(entry))
                data = clone.setdefault("node_data", {})
                old_id = data.get("node_id")
                data["node_id"] = self._new_node_id(old_id, remap)
                data["x"] = anchor.x() + (float(data.get("x", 0.0)) - min_x)
                data["y"] = anchor.y() + (float(data.get("y", 0.0)) - min_y)
                data.setdefault("properties", {})["__inline_subgraph_parent"] = container_id
                item = self.scene.add_node_from_entry(clone, select_new=False)
                if item is not None:
                    item._inline_subgraph_display = True
                    item.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
                    item.setOpacity(0.96)
                    created_nodes.append(item)
            external_in = [c for c in self.scene.serialize_graph().get("connections", []) if c.get("target_node_id") == container_id]
            external_out = [c for c in self.scene.serialize_graph().get("connections", []) if c.get("source_node_id") == container_id]
            start_edges = [c for c in subgraph.get("connections", []) if c.get("source_node_id") in start_ids and c.get("target_node_id") not in end_ids]
            end_edges = [c for c in subgraph.get("connections", []) if c.get("target_node_id") in end_ids and c.get("source_node_id") not in start_ids]
            for conn in subgraph.get("connections", []):
                src, tgt = conn.get("source_node_id"), conn.get("target_node_id")
                if src in start_ids or tgt in end_ids or src in end_ids or tgt in start_ids:
                    continue
                cloned = dict(conn)
                cloned["source_node_id"] = self._new_node_id(src, remap)
                cloned["target_node_id"] = self._new_node_id(tgt, remap)
                cloned["route_points"] = []
                citem = self.scene.add_connection_from_dict(cloned)
                if citem is not None:
                    citem._inline_subgraph_display = True
                    created_connections.append(citem)
            for ext in external_in:
                for edge in start_edges:
                    bridged = dict(edge)
                    bridged["source_node_id"] = ext.get("source_node_id")
                    bridged["source_port_name"] = ext.get("source_port_name")
                    bridged["target_node_id"] = self._new_node_id(edge.get("target_node_id"), remap)
                    bridged["route_points"] = []
                    citem = self.scene.add_connection_from_dict(bridged)
                    if citem is not None:
                        citem._inline_subgraph_display = True
                        created_connections.append(citem)
            for edge in end_edges:
                for ext in external_out:
                    bridged = dict(edge)
                    bridged["source_node_id"] = self._new_node_id(edge.get("source_node_id"), remap)
                    bridged["target_node_id"] = ext.get("target_node_id")
                    bridged["target_port_name"] = ext.get("target_port_name")
                    bridged["route_points"] = []
                    citem = self.scene.add_connection_from_dict(bridged)
                    if citem is not None:
                        citem._inline_subgraph_display = True
                        created_connections.append(citem)
            for conn in list(self.scene.items()):
                if isinstance(conn, ConnectionItem) and not getattr(conn, '_inline_subgraph_display', False):
                    data = conn.to_dict()
                    if data and (data.get("source_node_id") == container_id or data.get("target_node_id") == container_id):
                        conn.setVisible(False)
                        hidden_connections.append(conn)
            # The expanded dashed boundary visually replaces the container. The
            # container remains in the model so save/load and collapse semantics
            # stay stable, but it is hidden while the inline expansion is open.
            node_item.setVisible(False)
            node_rect = QtCore.QRectF()
            for item in created_nodes:
                node_rect = item.sceneBoundingRect() if node_rect.isNull() else node_rect.united(item.sceneBoundingRect())
            boundary_title = getattr(node_item, 'title', None) or node_item.node_data.title or 'Sub-Graph'
            boundary = InlineSubgraphBoundaryItem(self, container_id, node_rect.adjusted(-35, -62, 45, 45), title=boundary_title)
            boundary._inline_subgraph_display = True
            self.scene.addItem(boundary)
            self._inline_subgraph_expansions[container_id] = {
                "nodes": created_nodes,
                "connections": created_connections,
                "boundary": boundary,
                "original_positions": original_positions,
                "shifted_positions": shifted_positions,
                "hidden_connections": hidden_connections,
                "container_node": node_item,
            }
        finally:
            self.scene._suspend_undo = False
        self.scene.clearSelection()
        self._reframe_visible_graph_after_layout_change()
        self._status_message("Expanded sub-graph inline", 3500)
        return True

    def collapse_inline_subgraph(self, container_node_id):
        expansion = self._inline_subgraph_expansions.pop(container_node_id, None)
        if not expansion:
            return False
        self.scene._suspend_undo = True
        try:
            container_node = expansion.get("container_node") or self.scene.find_node_by_id(container_node_id)
            if container_node is not None:
                try:
                    container_node.setVisible(True)
                except RuntimeError:
                    pass
            for conn in expansion.get("hidden_connections", []):
                try:
                    conn.setVisible(True)
                except RuntimeError:
                    pass
            for conn in list(expansion.get("connections", [])):
                try:
                    conn.remove_from_ports()
                    for pin in list(getattr(conn, 'pin_items', [])):
                        self.scene.removeItem(pin)
                    self.scene.removeItem(conn)
                except RuntimeError:
                    pass
            for node in list(expansion.get("nodes", [])):
                try:
                    self.scene.removeItem(node)
                except RuntimeError:
                    pass
            boundary = expansion.get("boundary")
            if boundary is not None:
                try:
                    self.scene.removeItem(boundary)
                except RuntimeError:
                    pass
            # Restore the full pre-expansion layout, not merely the nodes
            # that were shifted. This guarantees the original container and all
            # parent graph nodes return to their exact prior positions.
            restore_positions = expansion.get("original_positions") or expansion.get("shifted_positions", {})
            for node_id, old_pos in restore_positions.items():
                node = self.scene.find_node_by_id(node_id)
                if node is not None:
                    node.setPos(old_pos)
        finally:
            self.scene._suspend_undo = False
        self._reframe_visible_graph_after_layout_change()
        self._status_message("Collapsed inline sub-graph", 2500)
        return True

    def collapse_all_inline_subgraphs(self):
        for container_id in list(getattr(self, '_inline_subgraph_expansions', {}).keys()):
            self.collapse_inline_subgraph(container_id)

    def _refresh_node_view_ui(self):
        view_definition = self.active_node_view()
        has_view = view_definition is not None
        view_name = view_definition.name if has_view else "Not Selected"
        self._viewHeaderLabel.setText("NoDE View")
        self._viewHeaderNameBadge.setText(view_name)
        if has_view:
            description = view_definition.description or "This view filters the available node definitions for the graph."
            if self._graph_has_nodes():
                state_text = "Locked after node placement"
                state_role = "locked"
            else:
                state_text = "Open for view selection"
                state_role = "editable"
        else:
            description = "Choose a NoDE view before opening the graph canvas."
            state_text = "Awaiting selection"
            state_role = "pending"
        self._viewHeaderDescriptionLabel.setText(description)
        self._viewHeaderNameBadge.setProperty("viewRole", "active" if has_view else "inactive")
        self._viewHeaderStateBadge.setProperty("viewRole", state_role)
        self._viewHeaderStateBadge.setText(state_text)
        in_subgraph = bool(getattr(self, '_graph_context_stack', []))
        if hasattr(self, '_subgraphBackButton'):
            self._subgraphBackButton.setVisible(in_subgraph)
        if hasattr(self, '_subgraphPathLabel'):
            self._subgraphPathLabel.setVisible(in_subgraph)
            self._subgraphPathLabel.setText(self._current_subgraph_path() if in_subgraph else "")
        if in_subgraph:
            self._viewHeaderDescriptionLabel.setText("Editing nested sub-graph. Start maps to the container Exec In; End maps back to the container Exec Out.")
        if hasattr(self, '_viewHeaderNameBadge'):
            self._repolish_widget(self._viewHeaderNameBadge)
        self._repolish_widget(self._viewHeaderStateBadge)
        self._apply_view_header_styles()

        self._viewSelectionCombo.blockSignals(True)
        self._viewSelectionCombo.clear()
        for view in self.available_node_views():
            self._viewSelectionCombo.addItem(view.name, view.view_id)
        if has_view:
            index = self._viewSelectionCombo.findData(view_definition.view_id)
            if index >= 0:
                self._viewSelectionCombo.setCurrentIndex(index)
        elif self._viewSelectionCombo.count() > 0:
            self._viewSelectionCombo.setCurrentIndex(0)
        self._viewSelectionCombo.blockSignals(False)
        self._update_view_selection_description()

        show_editor = has_view or self._graph_has_content()
        self._centralStack.setCurrentWidget(self._editorSurface if show_editor else self._viewSelectionSurface)
        self.graphView.setEnabled(show_editor)

    def _update_view_selection_description(self):
        index = self._viewSelectionCombo.currentIndex()
        view_id = self._viewSelectionCombo.itemData(index) if index >= 0 else None
        view_definition = NODE_VIEW_REGISTRY.get(view_id) if view_id else None
        if view_definition is None:
            self._viewSelectionDescription.setText("No NoDE views are currently available.")
            self._viewSelectionButton.setEnabled(False)
            return
        description = view_definition.description or "This view filters the available node definitions for the graph."
        self._viewSelectionDescription.setText(description)
        self._viewSelectionButton.setEnabled(True)

    def _apply_view_header_styles(self):
        self._viewHeaderFrame.setStyleSheet("""
        QFrame#nodeViewHeaderFrame {
            border-bottom: 1px solid rgba(255, 255, 255, 0.10);
            background: rgba(255, 255, 255, 0.03);
        }
        QLabel#nodeViewHeaderLabel {
            font-weight: 600;
            padding-right: 4px;
        }
        QLabel#nodeViewHeaderDescriptionLabel {
            color: rgba(230, 230, 230, 0.78);
            padding-left: 2px;
        }
        QLabel#nodeViewHeaderNameBadge,
        QLabel#nodeViewHeaderStateBadge {
            padding: 4px 10px;
            border-radius: 10px;
            font-weight: 600;
        }
        QLabel#nodeViewHeaderNameBadge[viewRole="active"] {
            background: rgba(42, 116, 255, 0.22);
            border: 1px solid rgba(42, 116, 255, 0.55);
            color: rgb(215, 231, 255);
        }
        QLabel#nodeViewHeaderNameBadge[viewRole="inactive"] {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: rgb(225, 225, 225);
        }
        QLabel#nodeViewHeaderStateBadge[viewRole="editable"] {
            background: rgba(52, 168, 83, 0.18);
            border: 1px solid rgba(52, 168, 83, 0.52);
            color: rgb(208, 244, 215);
        }
        QLabel#nodeViewHeaderStateBadge[viewRole="locked"] {
            background: rgba(255, 193, 7, 0.16);
            border: 1px solid rgba(255, 193, 7, 0.50);
            color: rgb(255, 237, 179);
        }
        QLabel#nodeViewHeaderStateBadge[viewRole="pending"] {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            color: rgb(225, 225, 225);
        }
        """)

    def _registry_for_view_id(self, view_id):
        preview_session = NodeViewSession(NODE_REGISTRY, NODE_VIEW_REGISTRY, select_default_on_reset=False)
        preview_session.set_active_view_id(view_id)
        return preview_session.active_registry()

    def _node_type_allowed_in_registry(self, node_type, registry=None):
        registry = registry or self.active_node_registry()
        return registry.get(node_type) is not None

    def _disallowed_node_types_in_graph_data(self, graph_data, registry=None):
        registry = registry or self.active_node_registry()
        disallowed = []
        nodes = graph_data.get("nodes", []) if isinstance(graph_data, dict) else []
        for node_entry in nodes:
            node_data = node_entry.get("node_data", {}) if isinstance(node_entry, dict) else {}
            node_type = node_data.get("node_type")
            if node_type and not self._node_type_allowed_in_registry(node_type, registry=registry):
                disallowed.append(node_type)
        return sorted(set(disallowed))

    def _find_compatible_view_id_for_graph_data(self, graph_data, preferred_view_id=None):
        candidate_ids = []
        if preferred_view_id:
            candidate_ids.append(preferred_view_id)
        default_view = NODE_VIEW_REGISTRY.default_view()
        if default_view is not None and default_view.view_id not in candidate_ids:
            candidate_ids.append(default_view.view_id)
        for view in self.available_node_views():
            if view.view_id not in candidate_ids:
                candidate_ids.append(view.view_id)
        if not candidate_ids:
            return None
        for view_id in candidate_ids:
            registry = self._registry_for_view_id(view_id)
            if not self._disallowed_node_types_in_graph_data(graph_data, registry=registry):
                return view_id
        return None

    def active_node_view_rules(self):
        view = self.active_node_view()
        if view is None:
            return NodeViewRules()
        return view.rules or NodeViewRules()

    def _graph_node_type_counts(self, graph_data=None):
        counts = {}
        if graph_data is None:
            nodes = [item for item in self.scene.items() if isinstance(item, NodeItem)]
            for node in nodes:
                node_type = getattr(node.node_data, 'node_type', None)
                if node_type:
                    counts[node_type] = counts.get(node_type, 0) + 1
            return counts
        nodes = graph_data.get('nodes', []) if isinstance(graph_data, dict) else []
        for node_entry in nodes:
            node_data = node_entry.get('node_data', {}) if isinstance(node_entry, dict) else {}
            node_type = node_data.get('node_type')
            if node_type:
                counts[node_type] = counts.get(node_type, 0) + 1
        return counts

    def _total_graph_node_count(self, graph_data=None):
        if graph_data is None:
            return len([item for item in self.scene.items() if isinstance(item, NodeItem)])
        nodes = graph_data.get('nodes', []) if isinstance(graph_data, dict) else []
        return len(nodes)

    def _validate_graph_against_rules(self, graph_data=None, view_definition=None):
        view_definition = view_definition or self.active_node_view()
        rules = view_definition.rules if view_definition is not None and getattr(view_definition, 'rules', None) is not None else NodeViewRules()
        messages = []
        type_counts = self._graph_node_type_counts(graph_data)
        total_count = self._total_graph_node_count(graph_data)

        if rules.max_nodes is not None and total_count > int(rules.max_nodes):
            messages.append("View allows at most %d nodes, but the graph has %d." % (int(rules.max_nodes), total_count))

        for node_type, limit in (rules.max_nodes_per_type or {}).items():
            actual = type_counts.get(node_type, 0)
            try:
                limit_value = int(limit)
            except Exception:
                continue
            if actual > limit_value:
                definition = NODE_REGISTRY.get(node_type)
                label = definition.display_name if definition is not None else node_type
                messages.append("View allows at most %d '%s' nodes, but the graph has %d." % (limit_value, label, actual))

        if rules.required_categories:
            present_categories = set()
            for node_type in type_counts:
                definition = NODE_REGISTRY.get(node_type)
                if definition is not None:
                    present_categories.add(definition.category)
            for category in rules.required_categories:
                if category not in present_categories:
                    messages.append("View expects at least one node from the '%s' category." % category)

        if rules.required_type_ids:
            for node_type in rules.required_type_ids:
                if type_counts.get(node_type, 0) <= 0:
                    definition = NODE_REGISTRY.get(node_type)
                    label = definition.display_name if definition is not None else node_type
                    messages.append("View expects at least one '%s' node." % label)

        return messages

    def _can_add_node_type(self, node_type, show_feedback=True, counts_override=None):
        if self.active_node_view() is None:
            if show_feedback:
                self._status_message("Select a NoDE view before adding nodes.", 3500)
            return False
        if not self._node_type_allowed_in_registry(node_type):
            if show_feedback:
                self._status_message("Node type is not available in the active NoDE view.", 4000)
            return False
        rules = self.active_node_view_rules()
        counts = dict(counts_override or self._graph_node_type_counts())
        total_count = sum(counts.values())
        proposed_total = total_count + 1
        if rules.max_nodes is not None and proposed_total > int(rules.max_nodes):
            if show_feedback:
                self._status_message("Active NoDE view allows at most %d nodes." % int(rules.max_nodes), 4500)
            return False
        type_limit = (rules.max_nodes_per_type or {}).get(node_type)
        if type_limit is not None:
            proposed_count = counts.get(node_type, 0) + 1
            if proposed_count > int(type_limit):
                definition = NODE_REGISTRY.get(node_type)
                label = definition.display_name if definition is not None else node_type
                if show_feedback:
                    self._status_message("Active NoDE view allows at most %d '%s' nodes." % (int(type_limit), label), 4500)
                return False
        return True

    def _port_category(self, port):
        node = getattr(port, 'parent_node', None)
        definition = getattr(node, 'definition', None) if node is not None else None
        if definition is None:
            return None
        return definition.category

    def _port_data_type(self, port):
        definition_port = getattr(port, 'definition_port', None)
        if definition_port is None:
            return 'any'
        return getattr(definition_port, 'data_type', 'any') or 'any'

    def _port_connection_kind(self, port):
        definition_port = getattr(port, 'definition_port', None)
        if definition_port is None:
            return 'data'
        resolver = getattr(definition_port, 'resolved_connection_kind', None)
        if callable(resolver):
            return resolver() or 'data'
        explicit = getattr(definition_port, 'connection_kind', None)
        if explicit:
            return str(explicit).strip().lower()
        data_type = getattr(definition_port, 'data_type', 'any') or 'any'
        data_type = str(data_type).strip().lower()
        if data_type == 'exec':
            return 'exec'
        if data_type == 'requirement':
            return 'requirement'
        return 'data'

    def _connection_kind_for_ports(self, source_port, target_port):
        source_kind = self._port_connection_kind(source_port)
        target_kind = self._port_connection_kind(target_port)
        if source_kind == target_kind:
            return source_kind
        if source_kind in ('', 'any', '*'):
            return target_kind
        if target_kind in ('', 'any', '*'):
            return source_kind
        return None

    @staticmethod
    def _rule_value_matches(actual, expected):
        actual_value = str(actual or '').strip().lower()
        expected_value = str(expected or '*').strip().lower()
        if expected_value in ('', '*', 'any'):
            return True
        return actual_value == expected_value

    def _matches_category_rule(self, source_port, target_port, rule):
        return (
            self._rule_value_matches(self._port_category(source_port), getattr(rule, 'source_category', '*')) and
            self._rule_value_matches(self._port_category(target_port), getattr(rule, 'target_category', '*'))
        )

    def _matches_data_type_rule(self, source_port, target_port, rule):
        return (
            self._rule_value_matches(self._port_data_type(source_port), getattr(rule, 'source_data_type', '*')) and
            self._rule_value_matches(self._port_data_type(target_port), getattr(rule, 'target_data_type', '*'))
        )

    def _matches_connection_kind_rule(self, source_port, target_port, rule):
        return (
            self._rule_value_matches(self._port_connection_kind(source_port), getattr(rule, 'source_connection_kind', '*')) and
            self._rule_value_matches(self._port_connection_kind(target_port), getattr(rule, 'target_connection_kind', '*'))
        )

    def _data_types_are_compatible(self, source_port, target_port):
        source_type = str(self._port_data_type(source_port) or 'any').strip().lower()
        target_type = str(self._port_data_type(target_port) or 'any').strip().lower()
        if source_type in ('', 'any') or target_type in ('', 'any'):
            return True
        return source_type == target_type

    def _check_connection_view_rules(self, source_port, target_port):
        rules = self.active_node_view_rules()

        blocked_category_rules = list(getattr(rules, 'blocked_connection_category_rules', []) or [])
        for rule in blocked_category_rules:
            if self._matches_category_rule(source_port, target_port, rule):
                return False, 'Active NoDE view blocks this category-to-category connection.'

        allowed_category_rules = list(getattr(rules, 'allowed_connection_category_rules', []) or [])
        if allowed_category_rules:
            if not any(self._matches_category_rule(source_port, target_port, rule) for rule in allowed_category_rules):
                return False, 'Active NoDE view does not allow this category-to-category connection.'

        blocked_data_type_rules = list(getattr(rules, 'blocked_connection_data_type_rules', []) or [])
        for rule in blocked_data_type_rules:
            if self._matches_data_type_rule(source_port, target_port, rule):
                return False, 'Active NoDE view blocks this data-type connection.'

        allowed_data_type_rules = list(getattr(rules, 'allowed_connection_data_type_rules', []) or [])
        if allowed_data_type_rules:
            if not any(self._matches_data_type_rule(source_port, target_port, rule) for rule in allowed_data_type_rules):
                return False, 'Active NoDE view does not allow this data-type connection.'

        connection_kind = self._connection_kind_for_ports(source_port, target_port)
        if not connection_kind:
            return False, 'Ports use incompatible connection kinds.'

        blocked_connection_kind_rules = list(getattr(rules, 'blocked_connection_kind_rules', []) or [])
        for rule in blocked_connection_kind_rules:
            if self._matches_connection_kind_rule(source_port, target_port, rule):
                return False, 'Active NoDE view blocks this connection kind.'

        allowed_connection_kind_rules = list(getattr(rules, 'allowed_connection_kind_rules', []) or [])
        if allowed_connection_kind_rules:
            if not any(self._matches_connection_kind_rule(source_port, target_port, rule) for rule in allowed_connection_kind_rules):
                return False, 'Active NoDE view does not allow this connection kind.'

        if getattr(rules, 'enforce_data_type_compatibility', False) and not self._data_types_are_compatible(source_port, target_port):
            return False, 'Active NoDE view requires compatible port data types.'

        return True, None

    def allows_connection_between_ports(self, source_port, target_port, connection_to_ignore=None):
        if source_port is None or target_port is None:
            return False
        rules = self.active_node_view_rules()
        source_node = getattr(source_port, 'parent_node', None)
        target_node = getattr(target_port, 'parent_node', None)
        if source_node is None or target_node is None:
            return False
        allowed_by_view, reason = self._check_connection_view_rules(source_port, target_port)
        if not allowed_by_view:
            if reason:
                self._status_message(reason, 3500)
            return False
        if source_node == target_node and not rules.allow_self_connections:
            return False
        connection_kind = self._connection_kind_for_ports(source_port, target_port)
        cycle_checked_kinds = {str(item).strip().lower() for item in list(getattr(rules, 'cycle_checked_connection_kinds', []) or []) if str(item).strip()}
        should_check_cycles = bool(cycle_checked_kinds) and connection_kind in cycle_checked_kinds
        if should_check_cycles and not rules.allow_cycles and self._connection_would_create_cycle(source_node, target_node, connection_to_ignore=connection_to_ignore, connection_kind=connection_kind):
            self._status_message("Active NoDE view does not allow graph cycles.", 3500)
            return False
        return True

    def connection_style_for_kind(self, connection_kind):
        kind = str(connection_kind or 'data').strip().lower() or 'data'
        view_definition = self.active_node_view()
        if view_definition is None:
            return None
        return getattr(view_definition, 'connection_styles', {}).get(kind)

    def _connection_would_create_cycle(self, source_node_item, target_node_item, connection_to_ignore=None, connection_kind=None):
        if source_node_item is None or target_node_item is None:
            return False
        source_id = source_node_item.node_data.node_id
        target_id = target_node_item.node_data.node_id
        if source_id is None or target_id is None:
            return False
        adjacency = {}
        for item in self.scene.items():
            if not isinstance(item, ConnectionItem):
                continue
            if connection_to_ignore is not None and item is connection_to_ignore:
                continue
            data = item.to_dict()
            if not data:
                continue
            if connection_kind is not None:
                existing_kind = data.get('connection_kind')
                if existing_kind and str(existing_kind).strip().lower() != str(connection_kind).strip().lower():
                    continue
            adjacency.setdefault(data.get('source_node_id'), set()).add(data.get('target_node_id'))
        stack = [target_id]
        visited = set()
        while stack:
            current = stack.pop()
            if current == source_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(adjacency.get(current, set()))
        return False

    def _filter_snapshot_to_active_view(self, snapshot):
        if not isinstance(snapshot, dict):
            return {'nodes': [], 'connections': []}, []
        allowed_nodes = []
        allowed_ids = set()
        blocked_reasons = []
        planned_counts = self._graph_node_type_counts()
        for node_entry in snapshot.get('nodes', []):
            node_data = node_entry.get('node_data', {}) if isinstance(node_entry, dict) else {}
            node_type = node_data.get('node_type')
            node_id = node_data.get('node_id')
            if not node_type:
                continue
            if not self._node_type_allowed_in_registry(node_type):
                blocked_reasons.append(node_type)
                continue
            if not self._can_add_node_type(node_type, show_feedback=False, counts_override=planned_counts):
                blocked_reasons.append(node_type)
                continue
            allowed_nodes.append(node_entry)
            planned_counts[node_type] = planned_counts.get(node_type, 0) + 1
            if node_id:
                allowed_ids.add(node_id)
        allowed_connections = []
        for conn_entry in snapshot.get('connections', []):
            source_id = conn_entry.get('source_node_id')
            target_id = conn_entry.get('target_node_id')
            if source_id in allowed_ids and target_id in allowed_ids:
                allowed_connections.append(conn_entry)
        return {'nodes': allowed_nodes, 'connections': allowed_connections}, sorted(set(blocked_reasons))

    def _confirm_initial_node_view_selection(self):
        index = self._viewSelectionCombo.currentIndex()
        view_id = self._viewSelectionCombo.itemData(index) if index >= 0 else None
        if not view_id:
            QtWidgets.QMessageBox.information(self, "Select NoDE View", "Choose a NoDE view before opening the graph canvas.")
            return False
        self.set_active_node_view(view_id)
        self.graphView.setFocus()
        return True

    def _can_change_node_view(self, target_view_id=None, show_feedback=True):
        target_view_id = target_view_id or None
        if target_view_id == self._active_node_view_id:
            return True
        if self._graph_has_nodes():
            if show_feedback:
                QtWidgets.QMessageBox.information(
                    self,
                    "NoDE View Locked",
                    "This graph already contains nodes. NoDE views can only be changed before any nodes are placed on the graph.",
                )
                self._status_message("NoDE view is locked after nodes are placed on the graph.", 4000)
            return False
        return True

    def _build_local_panels(self):
        self.dockProperties = QtWidgets.QDockWidget("Properties", self)
        self.dockProperties.setObjectName(f"dockProperties_{id(self)}")
        self.dockProperties.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea |
            QtCore.Qt.RightDockWidgetArea |
            QtCore.Qt.BottomDockWidgetArea
        )
        self.dockProperties.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetClosable
        )

        self._property_editors = {}
        self._table_editor_updating = False

        properties_host = QtWidgets.QWidget(self.dockProperties)
        root_layout = QtWidgets.QVBoxLayout(properties_host)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        self.propertiesForm = QtWidgets.QFormLayout()
        self.propertiesForm.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.propertiesForm.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.labelNodeIdValue = QtWidgets.QLabel("—", properties_host)
        self.labelNodeIdValue.setWordWrap(True)
        self.labelNodeTypeValue = QtWidgets.QLabel("—", properties_host)
        self.editNodeTitle = QtWidgets.QLineEdit(properties_host)

        self.propertiesForm.addRow("Node ID", self.labelNodeIdValue)
        self.propertiesForm.addRow("Node Type", self.labelNodeTypeValue)
        self.propertiesForm.addRow("Title", self.editNodeTitle)

        self.dynamicPropertiesContainer = QtWidgets.QWidget(properties_host)
        self.dynamicPropertiesForm = QtWidgets.QFormLayout(self.dynamicPropertiesContainer)
        self.dynamicPropertiesForm.setContentsMargins(0, 0, 0, 0)
        self.dynamicPropertiesForm.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.dynamicPropertiesForm.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        self.tableEditorGroup = QtWidgets.QGroupBox("Table Data", properties_host)
        table_layout = QtWidgets.QVBoxLayout(self.tableEditorGroup)
        table_toolbar = QtWidgets.QHBoxLayout()
        self.btnImportTableCsv = QtWidgets.QPushButton("Import CSV", self.tableEditorGroup)
        self.btnAddTableColumn = QtWidgets.QPushButton("Add Column", self.tableEditorGroup)
        self.btnRenameTableColumn = QtWidgets.QPushButton("Rename Column", self.tableEditorGroup)
        self.btnRemoveTableColumn = QtWidgets.QPushButton("Remove Column", self.tableEditorGroup)
        self.btnAddTableRow = QtWidgets.QPushButton("Add Row", self.tableEditorGroup)
        self.btnRemoveTableRow = QtWidgets.QPushButton("Remove Row", self.tableEditorGroup)
        for btn in (self.btnImportTableCsv, self.btnAddTableColumn, self.btnRenameTableColumn, self.btnRemoveTableColumn, self.btnAddTableRow, self.btnRemoveTableRow):
            table_toolbar.addWidget(btn)
        table_toolbar.addStretch(1)
        table_layout.addLayout(table_toolbar)
        self.tableColumnsSummary = QtWidgets.QLabel("", self.tableEditorGroup)
        self.tableColumnsSummary.setWordWrap(True)
        table_layout.addWidget(self.tableColumnsSummary)
        self.tableWidget = QtWidgets.QTableWidget(self.tableEditorGroup)
        self.tableWidget.setAlternatingRowColors(False)
        self.tableWidget.setShowGrid(True)
        self.tableWidget.setCornerButtonEnabled(True)
        self.tableWidget.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.tableWidget.setStyleSheet("background: transparent;")
        self.tableWidget.verticalHeader().setVisible(True)
        self.tableWidget.verticalHeader().setHighlightSections(False)
        self.tableWidget.horizontalHeader().setHighlightSections(False)
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.tableWidget.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignCenter)
        table_layout.addWidget(self.tableWidget)
        self.tableEditorGroup.hide()

        self.btnImportTableCsv.clicked.connect(self.import_table_from_csv)
        self.btnAddTableColumn.clicked.connect(self.add_table_column)
        self.btnRenameTableColumn.clicked.connect(self.rename_selected_table_column)
        self.btnRemoveTableColumn.clicked.connect(self.remove_selected_table_column)
        self.btnAddTableRow.clicked.connect(self.add_table_row)
        self.btnRemoveTableRow.clicked.connect(self.remove_selected_table_row)
        self.tableWidget.itemChanged.connect(self.on_table_item_changed)

        root_layout.addLayout(self.propertiesForm)
        root_layout.addWidget(self.dynamicPropertiesContainer)
        root_layout.addWidget(self.tableEditorGroup)
        root_layout.addStretch(1)

        self.dockProperties.setWidget(properties_host)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dockProperties)
        self.dockProperties.hide()

    def _clear_form_layout(self, form_layout):
        while form_layout.count():
            item = form_layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_form_layout(child_layout)

    def _connect_property_editor(self, prop_name, editor, property_type):
        if property_type == "string":
            if isinstance(editor, QtWidgets.QTextEdit):
                editor.textChanged.connect(lambda name=prop_name, w=editor: self.on_dynamic_property_changed(name, w.toPlainText()))
            else:
                editor.textEdited.connect(lambda value, name=prop_name: self.on_dynamic_property_changed(name, value))
        elif property_type == "int":
            editor.valueChanged.connect(lambda value, name=prop_name: self.on_dynamic_property_changed(name, int(value)))
        elif property_type == "float":
            editor.valueChanged.connect(lambda value, name=prop_name: self.on_dynamic_property_changed(name, float(value)))
        elif property_type == "bool":
            editor.toggled.connect(lambda value, name=prop_name: self.on_dynamic_property_changed(name, bool(value)))
        elif property_type == "choice":
            editor.currentTextChanged.connect(lambda value, name=prop_name: self.on_dynamic_property_changed(name, value))

    def _create_property_editor(self, prop_def):
        property_type = prop_def.property_type
        if property_type == "int":
            editor = QtWidgets.QSpinBox(self.dynamicPropertiesContainer)
            editor.setRange(-999999999, 999999999)
        elif property_type == "float":
            editor = QtWidgets.QDoubleSpinBox(self.dynamicPropertiesContainer)
            editor.setRange(-1e12, 1e12)
            editor.setDecimals(6)
        elif property_type == "bool":
            editor = QtWidgets.QCheckBox(self.dynamicPropertiesContainer)
        elif property_type == "choice":
            editor = QtWidgets.QComboBox(self.dynamicPropertiesContainer)
            editor.addItems(prop_def.options)
        else:
            if prop_def.multiline:
                editor = QtWidgets.QTextEdit(self.dynamicPropertiesContainer)
                editor.setFixedHeight(72)
            else:
                editor = QtWidgets.QLineEdit(self.dynamicPropertiesContainer)
        self._connect_property_editor(prop_def.name, editor, property_type)
        return editor

    def _set_editor_value(self, editor, prop_def, value):
        property_type = prop_def.property_type
        if property_type == "int":
            editor.blockSignals(True)
            editor.setValue(int(value or 0))
            editor.blockSignals(False)
        elif property_type == "float":
            editor.blockSignals(True)
            editor.setValue(float(value or 0.0))
            editor.blockSignals(False)
        elif property_type == "bool":
            editor.blockSignals(True)
            editor.setChecked(bool(value))
            editor.blockSignals(False)
        elif property_type == "choice":
            editor.blockSignals(True)
            text_value = "" if value is None else str(value)
            index = editor.findText(text_value)
            if index < 0 and text_value:
                editor.addItem(text_value)
                index = editor.findText(text_value)
            editor.setCurrentIndex(max(index, 0))
            editor.blockSignals(False)
        else:
            editor.blockSignals(True)
            text_value = "" if value is None else str(value)
            if isinstance(editor, QtWidgets.QTextEdit):
                editor.setPlainText(text_value)
            else:
                editor.setText(text_value)
            editor.blockSignals(False)

    def rebuild_dynamic_property_form(self, node_item):
        self._clear_form_layout(self.dynamicPropertiesForm)
        self._property_editors = {}
        definition = getattr(node_item, "definition", None)
        if definition is None:
            self.tableEditorGroup.hide()
            return

        for prop_def in definition.properties:
            if prop_def.property_type in ("table_columns", "table_rows"):
                continue
            editor = self._create_property_editor(prop_def)
            self.dynamicPropertiesForm.addRow(prop_def.label, editor)
            self._property_editors[prop_def.name] = (prop_def, editor)

        self.refresh_table_editor(node_item)

    def refresh_table_editor(self, node_item):
        definition = getattr(node_item, "definition", None)
        is_table_node = definition is not None and definition.type_id == "table.table_data"
        self.tableEditorGroup.setVisible(is_table_node)
        if not is_table_node:
            return

        columns = list(node_item.node_data.properties.get("columns", []))
        rows = list(node_item.node_data.properties.get("rows", []))
        self._table_editor_updating = True
        self.tableWidget.blockSignals(True)
        try:
            self.tableColumnsSummary.setText(
                "Columns: " + ", ".join(f"{col.get('name', 'column')} ({col.get('type', 'string')})" for col in columns)
                if columns else "Columns: none"
            )
            self.tableWidget.clear()
            self.tableWidget.setColumnCount(len(columns))
            self.tableWidget.setRowCount(len(rows))
            self.tableWidget.setHorizontalHeaderLabels([col.get("name", f"Column {index + 1}") for index, col in enumerate(columns)])
            for row_index, row_data in enumerate(rows):
                for column_index, column in enumerate(columns):
                    value = row_data.get(column.get("name", ""), "")
                    item = QtWidgets.QTableWidgetItem("" if value is None else str(value))
                    self.tableWidget.setItem(row_index, column_index, item)
        finally:
            self.tableWidget.blockSignals(False)
            self._table_editor_updating = False
        header = self.tableWidget.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(110)
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        for column_index in range(self.tableWidget.columnCount()):
            label = self.tableWidget.horizontalHeaderItem(column_index).text() if self.tableWidget.horizontalHeaderItem(column_index) else ""
            text_width = self.tableWidget.fontMetrics().horizontalAdvance(label) + 36
            self.tableWidget.setColumnWidth(column_index, max(120, text_width))
        self.tableWidget.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        self.tableWidget.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.tableWidget.verticalHeader().setDefaultSectionSize(26)
        self.tableWidget.viewport().update()
        self.tableWidget.update()

    def on_dynamic_property_changed(self, prop_name, value):
        if self._updating_property_panel or self.selected_node_item is None:
            return
        self.selected_node_item.node_data.properties[prop_name] = value
        self.on_node_mutated(self.selected_node_item)

    def _sync_dynamic_property_values(self, node_item):
        definition = getattr(node_item, "definition", None)
        if definition is None:
            return
        for prop_def, editor in self._property_editors.values():
            value = node_item.node_data.properties.get(prop_def.name, prop_def.default)
            self._set_editor_value(editor, prop_def, value)


    def _table_column_names(self, node_item):
        columns = list(node_item.node_data.properties.get("columns", []))
        names = []
        for index, column in enumerate(columns):
            name = str(column.get("name") or f"column_{index + 1}").strip() or f"column_{index + 1}"
            names.append(name)
        return names

    def _sync_table_node_ports(self, node_item):
        if node_item is None or node_item.node_data.node_type != "table.table_data":
            return
        output_names = self._table_column_names(node_item)
        node_item.rebuild_ports(inputs=[], outputs=output_names)
        node_item.node_data.properties["columns"] = [
            {"name": name, "type": "string"} for name in output_names
        ]
        node_item.update()
        if hasattr(self, "scene") and self.scene is not None:
            self.scene.update()

    def _sanitize_csv_header(self, header, index, existing):
        base = str(header or "").strip()
        if not base:
            base = f"column_{index + 1}"
        # Keep labels readable but remove line breaks/tabs that make ports ugly.
        base = " ".join(base.replace("\t", " ").replace("\r", " ").replace("\n", " ").split())
        candidate = base
        suffix = 2
        while candidate in existing:
            candidate = f"{base}_{suffix}"
            suffix += 1
        existing.add(candidate)
        return candidate

    def import_table_from_csv(self):
        if self.selected_node_item is None or self.selected_node_item.node_data.node_type != "table.table_data":
            return
        path, _selected_filter = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import CSV into Table Data Node",
            "",
            "CSV Files (*.csv);;All Files (*.*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as handle:
                sample = handle.read(4096)
                handle.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample) if sample else csv.excel
                except csv.Error:
                    dialect = csv.excel
                reader = csv.reader(handle, dialect)
                raw_rows = list(reader)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, "Import CSV", f"Could not import CSV:\n{exc}")
            return

        if not raw_rows:
            QtWidgets.QMessageBox.information(self, "Import CSV", "The selected CSV did not contain any rows.")
            return

        existing = set()
        headers = [
            self._sanitize_csv_header(value, index, existing)
            for index, value in enumerate(raw_rows[0])
        ]
        data_rows = []
        for raw in raw_rows[1:]:
            row = {}
            for index, header in enumerate(headers):
                row[header] = raw[index] if index < len(raw) else ""
            data_rows.append(row)

        self.selected_node_item.node_data.properties["columns"] = [
            {"name": header, "type": "string"} for header in headers
        ]
        self.selected_node_item.node_data.properties["rows"] = data_rows
        self.selected_node_item.node_data.properties["source_csv"] = path
        self._sync_table_node_ports(self.selected_node_item)
        self.refresh_table_editor(self.selected_node_item)
        self.on_node_mutated(self.selected_node_item)
        self._status_message(f"Imported {len(data_rows)} CSV rows and {len(headers)} columns.", 3500)

    def rename_selected_table_column(self):
        if self.selected_node_item is None or self.selected_node_item.node_data.node_type != "table.table_data":
            return
        column_index = self.tableWidget.currentColumn()
        columns = self.selected_node_item.node_data.properties.get("columns", [])
        if column_index < 0 or column_index >= len(columns):
            return
        old_name = columns[column_index].get("name", f"column_{column_index + 1}")
        new_name, accepted = QtWidgets.QInputDialog.getText(
            self,
            "Rename Table Column",
            "Column name:",
            text=old_name,
        )
        if not accepted:
            return
        new_name = str(new_name or "").strip()
        if not new_name or new_name == old_name:
            return
        existing = {col.get("name") for idx, col in enumerate(columns) if idx != column_index}
        if new_name in existing:
            QtWidgets.QMessageBox.information(self, "Rename Table Column", "A column with that name already exists.")
            return
        columns[column_index]["name"] = new_name
        for row in self.selected_node_item.node_data.properties.get("rows", []):
            row[new_name] = row.pop(old_name, "")
        self._sync_table_node_ports(self.selected_node_item)
        self.refresh_table_editor(self.selected_node_item)

    def add_table_column(self):
        if self.selected_node_item is None or self.selected_node_item.node_data.node_type != "table.table_data":
            return
        columns = self.selected_node_item.node_data.properties.setdefault("columns", [])
        base_name = f"column_{len(columns) + 1}"
        existing_names = {column.get("name") for column in columns}
        candidate = base_name
        suffix = 1
        while candidate in existing_names:
            suffix += 1
            candidate = f"{base_name}_{suffix}"
        columns.append({"name": candidate, "type": "string"})
        for row in self.selected_node_item.node_data.properties.setdefault("rows", []):
            row.setdefault(candidate, "")
        self._sync_table_node_ports(self.selected_node_item)
        self.refresh_table_editor(self.selected_node_item)

    def remove_selected_table_column(self):
        if self.selected_node_item is None or self.selected_node_item.node_data.node_type != "table.table_data":
            return
        column_index = self.tableWidget.currentColumn()
        columns = self.selected_node_item.node_data.properties.get("columns", [])
        if column_index < 0 or column_index >= len(columns):
            return
        removed = columns.pop(column_index)
        removed_name = removed.get("name")
        for row in self.selected_node_item.node_data.properties.get("rows", []):
            row.pop(removed_name, None)
        self._sync_table_node_ports(self.selected_node_item)
        self.refresh_table_editor(self.selected_node_item)

    def add_table_row(self):
        if self.selected_node_item is None or self.selected_node_item.node_data.node_type != "table.table_data":
            return
        columns = self.selected_node_item.node_data.properties.setdefault("columns", [])
        new_row = {column.get("name", f"column_{index + 1}"): "" for index, column in enumerate(columns)}
        self.selected_node_item.node_data.properties.setdefault("rows", []).append(new_row)
        self.refresh_table_editor(self.selected_node_item)

    def remove_selected_table_row(self):
        if self.selected_node_item is None or self.selected_node_item.node_data.node_type != "table.table_data":
            return
        row_index = self.tableWidget.currentRow()
        rows = self.selected_node_item.node_data.properties.get("rows", [])
        if row_index < 0 or row_index >= len(rows):
            return
        rows.pop(row_index)
        self.refresh_table_editor(self.selected_node_item)

    def on_table_item_changed(self, item):
        if self._table_editor_updating or self._updating_property_panel or self.selected_node_item is None:
            return
        if self.selected_node_item.node_data.node_type != "table.table_data":
            return
        columns = self.selected_node_item.node_data.properties.get("columns", [])
        rows = self.selected_node_item.node_data.properties.setdefault("rows", [])
        row_index = item.row()
        column_index = item.column()
        if row_index < 0 or column_index < 0 or column_index >= len(columns):
            return
        while row_index >= len(rows):
            rows.append({})
        column_name = columns[column_index].get("name", f"column_{column_index + 1}")
        rows[row_index][column_name] = item.text()

    def _build_local_menus(self):
        menu_bar = self.menuBar()
        if menu_bar is not None:
            menu_bar.hide()
        self._graph_menu = None
        self._edit_menu = None
    def available_node_views(self):
        return self._node_view_session.available_views()

    def active_node_view_id(self):
        return self._active_node_view_id

    def active_node_view(self):
        if self._active_node_view_id:
            return self._node_view_session.active_view()
        return None

    def active_node_registry(self):
        return self._node_view_session.active_registry()

    def set_active_node_view(self, view_id, announce=True, ignore_lock=False):
        if not ignore_lock and not self._can_change_node_view(view_id, show_feedback=announce):
            return None
        view_definition = self._node_view_session.set_active_view_id(view_id)
        self._active_node_view_id = self._node_view_session.active_view_id()
        self._apply_active_node_view_registry()
        self._refresh_node_view_ui()
        self.set_editor_title(self._editor_title)
        self._ensure_current_graph_control_flow_nodes()
        if announce:
            label = view_definition.name if view_definition is not None else "Not Selected"
            self._status_message("NoDE view: %s" % label, 3500)
        return view_definition

    def prompt_select_node_view(self):
        views = self.available_node_views()
        if not views:
            self._status_message("NoDE view: no views available", 3000)
            return False
        if not self._can_change_node_view(show_feedback=True):
            return False

        labels = [view.name for view in views]
        current_view = self.active_node_view()
        current_name = current_view.name if current_view is not None else labels[0]
        current_index = labels.index(current_name) if current_name in labels else 0

        selected_name, accepted = QtWidgets.QInputDialog.getItem(
            self,
            "Select NoDE View",
            "Active view:",
            labels,
            current_index,
            False,
        )
        if not accepted:
            return False

        for view in views:
            if view.name == selected_name:
                return self.set_active_node_view(view.view_id) is not None
        return False

    def cycle_node_view(self, step=1):
        views = self.available_node_views()
        if not views:
            return False
        active_id = self.active_node_view_id()
        current_index = 0
        for index, view in enumerate(views):
            if view.view_id == active_id:
                current_index = index
                break
        next_index = (current_index + int(step)) % len(views)
        return self.set_active_node_view(views[next_index].view_id) is not None

    def _install_definition_live_reload(self):
        watch_roots = []
        for root in (NODE_DEFINITIONS_DIR, NODE_VIEW_MANIFESTS_DIR):
            try:
                resolved = str(Path(root).resolve())
            except Exception:
                resolved = str(root)
            if resolved not in watch_roots:
                watch_roots.append(resolved)
        self._definition_watch_roots = watch_roots

        watcher = QtCore.QFileSystemWatcher(self)
        watcher.directoryChanged.connect(self._schedule_definition_reload)
        watcher.fileChanged.connect(self._schedule_definition_reload)
        self._definition_watcher = watcher

        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(150)
        timer.timeout.connect(self._reload_definition_sources)
        self._definition_reload_timer = timer

        self._refresh_definition_watch_paths()

    def _iter_definition_watch_paths(self):
        paths = []
        seen = set()
        for root_str in list(self._definition_watch_roots or []):
            root = Path(root_str)
            candidates = [root]
            if root.exists():
                candidates.extend(sorted(path for path in root.rglob('*') if path.is_dir() or path.suffix.lower() == '.json'))
            for candidate in candidates:
                candidate_str = str(candidate)
                if candidate_str in seen:
                    continue
                seen.add(candidate_str)
                yield candidate_str

    def _refresh_definition_watch_paths(self):
        watcher = self._definition_watcher
        if watcher is None:
            return
        desired = list(self._iter_definition_watch_paths())
        current = set(watcher.files()) | set(watcher.directories())
        desired_set = set(desired)
        remove_paths = sorted(current - desired_set)
        if remove_paths:
            watcher.removePaths(remove_paths)
        add_paths = [path for path in desired if path not in current]
        if add_paths:
            watcher.addPaths(add_paths)

    def _schedule_definition_reload(self, *_args):
        if self._definition_reload_timer is None:
            return
        self._definition_reload_timer.start()

    def _reload_definition_sources(self):
        active_view_id = self._active_node_view_id
        try:
            load_external_node_definitions(clear_existing=True)
            load_node_views(clear_existing=True)
            self._node_view_session = NodeViewSession(NODE_REGISTRY, NODE_VIEW_REGISTRY, select_default_on_reset=False)
            fallback_view_id = None
            if active_view_id and NODE_VIEW_REGISTRY.get(active_view_id) is None:
                default_view = NODE_VIEW_REGISTRY.default_view()
                fallback_view_id = default_view.view_id if default_view is not None else None
            self._active_node_view_id = active_view_id if fallback_view_id is None else fallback_view_id
            self._node_view_session.set_active_view_id(self._active_node_view_id)
            self._apply_active_node_view_registry()
            self._refresh_node_view_ui()
            self._refresh_definition_watch_paths()
            if hasattr(self, 'graphView') and self.graphView is not None:
                self.graphView.viewport().update()
            if hasattr(self, 'scene') and self.scene is not None:
                self.scene.update()
            self._status_message('NoDE Lite definitions refreshed.', 1800)
        except Exception as exc:
            self._refresh_definition_watch_paths()
            self._status_message('Failed to refresh NoDE Lite definitions: %s' % exc, 5000)

    def _apply_active_node_view_registry(self):
        registry = self._node_view_session.active_registry()
        self.graphView.set_node_registry(registry)


    def _supports_program_execution(self):
        return False

    def reset_graph_execution(self, *_args, **_kwargs):
        return False

    def pause_graph_execution(self):
        return False

    def step_into_graph_execution(self):
        return False

    def step_over_graph_execution(self):
        return False

    def step_out_graph_execution(self):
        return False

    def run_graph_execution(self):
        return False

    def toggle_node_breakpoint(self, node_item=None):
        return False

    def toggle_selected_breakpoint(self):
        return False

    def node_supports_runtime_breakpoint(self, node_item) -> bool:
        return False

    def is_runtime_breakpoint_toggle_active(self) -> bool:
        return False

    def open_execution_panel(self):
        return False

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if self.close_properties_dock():
                event.accept()
                return
        super().keyPressEvent(event)

    def close_editor(self):
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, 'index_of_tool') and hasattr(parent, 'close_tab'):
                index = parent.index_of_tool(self)
                if index >= 0:
                    parent.close_tab(index)
                    return
            parent = parent.parentWidget()
        self.close()

    def focus_primary_surface(self):
        if self._centralStack.currentWidget() is self._viewSelectionSurface:
            self._viewSelectionCombo.setFocus()
            return
        self.graphView.setFocus()

    def get_undo_stack(self):
        return self.undo_stack

    def save(self):
        return self.save_graph_to_file()

    def save_as(self):
        return self.save_graph_to_file_as()

    def load(self):
        return self.load_graph_from_file()

    def load_from_path(self, file_path):
        return self.load_graph_from_file(file_path)

    def editor_title(self):
        return self._editor_title

    def set_editor_title(self, title):
        self._editor_title = title
        self.titleChanged.emit(title)
        view_definition = self.active_node_view()
        if view_definition is not None:
            self.setWindowTitle("%s [%s]" % (title, view_definition.name))
        else:
            self.setWindowTitle(title)

    def current_theme_name(self):
        return self.scene.theme_name

    def _repolish_widget(self, widget):
        if widget is None:
            return
        style = widget.style()
        if style is None:
            return
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _apply_stylesheet_to_widget_tree(self, widget, stylesheet):
        if widget is None:
            return
        widget.setStyleSheet(stylesheet)
        self._repolish_widget(widget)
        for child in widget.findChildren(QtWidgets.QWidget):
            child.setStyleSheet("")
            self._repolish_widget(child)

    def apply_theme(self, theme_name):
        self.scene.set_theme(theme_name)
        theme = get_theme_colors(theme_name)
        stylesheet = build_stylesheet(theme)

        self.setStyleSheet(stylesheet)
        self._repolish_widget(self)

        menu_bar = self.menuBar()
        if menu_bar is not None:
            self._apply_stylesheet_to_widget_tree(menu_bar, stylesheet)
            for action in menu_bar.actions():
                menu = action.menu()
                if menu is not None:
                    self._apply_stylesheet_to_widget_tree(menu, stylesheet)

        self._apply_stylesheet_to_widget_tree(self.graphView, stylesheet)
        self._apply_stylesheet_to_widget_tree(self.graphView.viewport(), stylesheet)
        self._apply_stylesheet_to_widget_tree(self.graphView.horizontalScrollBar(), stylesheet)
        self._apply_stylesheet_to_widget_tree(self.graphView.verticalScrollBar(), stylesheet)
        self._apply_stylesheet_to_widget_tree(self.dockProperties, stylesheet)
        self._apply_stylesheet_to_widget_tree(self.dockProperties.widget(), stylesheet)
        dock_execution = getattr(self, 'dockExecution', None)
        if dock_execution is not None:
            self._apply_stylesheet_to_widget_tree(dock_execution, stylesheet)
            self._apply_stylesheet_to_widget_tree(dock_execution.widget(), stylesheet)
        self._apply_stylesheet_to_widget_tree(self.tableWidget, stylesheet)
        self._apply_stylesheet_to_widget_tree(self.tableWidget.viewport(), stylesheet)
        self._apply_stylesheet_to_widget_tree(self.tableWidget.horizontalHeader(), stylesheet)
        self._apply_stylesheet_to_widget_tree(self.tableWidget.verticalHeader(), stylesheet)

        for child in self.findChildren(QtWidgets.QWidget):
            child.setPalette(self.palette())
            self._repolish_widget(child)

        self.scene.update()
        self.graphView.viewport().update()
        self._theme_applied_once = True

    def showEvent(self, event):
        super().showEvent(event)
        if not self._theme_applied_once:
            QtCore.QTimer.singleShot(0, lambda: self.apply_theme(self.current_theme_name()))
        if self._initial_fit_pending:
            QtCore.QTimer.singleShot(0, self._ensure_initial_fit)

    def _ensure_initial_fit(self):
        if not self._initial_fit_pending:
            return
        if self._centralStack.currentWidget() is self._viewSelectionSurface:
            return
        if self.graphView.viewport().width() <= 1 or self.graphView.viewport().height() <= 1:
            QtCore.QTimer.singleShot(0, self._ensure_initial_fit)
            return

        nodes = [item for item in self.scene.items() if isinstance(item, NodeItem)]
        if nodes:
            self.frame_all_nodes()
        else:
            self.graphView.frame_scene_rect()
        self._initial_fit_pending = False

    def add_demo_content(self):
        self.scene._suspend_undo = True
        try:
            self.scene.add_node("Start Test", QtCore.QPointF(0, 0), node_type="flow.start_test")
            self.scene.add_node("Click Button", QtCore.QPointF(260, 40), node_type="action.click_button")
            self.scene.add_node("Assert Equals", QtCore.QPointF(560, 20), node_type="assert.equals")
            self.scene.add_node("Table Data", QtCore.QPointF(0, 220), node_type="table.table_data")
            self.scene.add_node("For Each Row", QtCore.QPointF(280, 220), node_type="table.for_each_row")
            self.scene.add_node("Call Function", QtCore.QPointF(560, 220), node_type="function.call")
        finally:
            self.scene._suspend_undo = False
        self._initial_fit_pending = True
        QtCore.QTimer.singleShot(0, self._ensure_initial_fit)

    def add_node_from_toolbar(self):
        if self.active_node_view() is None:
            self._centralStack.setCurrentWidget(self._viewSelectionSurface)
            self._status_message("Select a NoDE view before adding nodes.", 3500)
            self.focus_primary_surface()
            return
        center = self.graphView.mapToScene(self.graphView.viewport().rect().center())
        preferred_type = "action.click_button"
        if not self._node_type_allowed_in_registry(preferred_type):
            definitions = self.active_node_registry().all_definitions()
            if not definitions:
                self._status_message("No nodes are available in the active NoDE view.", 3500)
                return
            preferred_type = definitions[0].type_id
        if not self._can_add_node_type(preferred_type, show_feedback=True):
            return
        self.undo_stack.push(AddNodeCommand(
            self.scene,
            "Click Button",
            center,
            node_type=preferred_type
        ))

    def center_view(self):
        self.graphView.centerOn(0, 0)

    def reset_zoom(self):
        self.graphView.reset_zoom()

    def frame_selected_or_all(self):
        self.graphView.frame_selected_or_all()

    def frame_all_nodes(self):
        self.graphView.frame_all_nodes()

    def _install_edit_shortcuts(self):
        return

    def _selected_graph_snapshot(self):
        selected = self.scene.selectedItems()
        if not selected:
            return None
        snapshot = self.scene.snapshot_items_for_delete(selected)
        if not snapshot.get('nodes') and not snapshot.get('connections'):
            return None
        return snapshot

    def _serialize_clipboard_snapshot(self, snapshot):
        if not snapshot:
            return ''
        return json.dumps(snapshot, indent=2)

    def copy(self):
        snapshot = self._selected_graph_snapshot()
        if not snapshot:
            return False
        clipboard = QtWidgets.QApplication.clipboard()
        mime = QtCore.QMimeData()
        payload = self._serialize_clipboard_snapshot(snapshot)
        mime.setData(self._clipboard_mime_type, payload.encode('utf-8'))
        mime.setText(payload)
        clipboard.setMimeData(mime)
        return True

    def cut(self):
        if not self.copy():
            return False
        return self.delete_selected_items()

    def duplicate_selection(self):
        snapshot = self._selected_graph_snapshot()
        if not snapshot:
            return False
        pasted = self._generate_pasted_snapshot(snapshot)
        pasted, blocked_types = self._filter_snapshot_to_active_view(pasted)
        if blocked_types:
            self._status_message("Skipped nodes blocked by the active NoDE view: %s" % ", ".join(blocked_types), 5000)
        if not pasted.get('nodes'):
            return False
        self.undo_stack.push(PasteItemsCommand(self.scene, pasted))
        return True

    def break_node_links(self, node_item=None):
        if node_item is None:
            node_item = self.selected_node_item
        if node_item is None:
            return False

        connections = []
        seen = set()
        for port in list(node_item.inputs) + list(node_item.outputs):
            for connection in list(port.connections):
                conn_data = connection.to_dict()
                if not conn_data:
                    continue
                key = (
                    conn_data.get('source_node_id'),
                    conn_data.get('source_port_name'),
                    conn_data.get('target_node_id'),
                    conn_data.get('target_port_name'),
                    tuple(tuple(point) for point in conn_data.get('route_points', [])),
                )
                if key in seen:
                    continue
                seen.add(key)
                connections.append(conn_data)

        if not connections:
            return False

        connections.sort(key=lambda entry: (
            entry.get('source_node_id', ''),
            entry.get('source_port_name', ''),
            entry.get('target_node_id', ''),
            entry.get('target_port_name', ''),
        ))
        self.undo_stack.push(DeleteItemsCommand(self.scene, {'nodes': [], 'connections': connections}))
        return True

    def _generate_pasted_snapshot(self, snapshot):
        offset_step = 32.0
        self._paste_sequence += 1
        dx = offset_step * self._paste_sequence
        dy = offset_step * self._paste_sequence
        id_map = {}
        new_nodes = []
        for node_entry in snapshot.get('nodes', []):
            node_data = dict(node_entry.get('node_data', {}))
            old_id = node_data.get('node_id')
            new_entry = create_node_entry(
                node_type=node_data.get('node_type', 'generic'),
                pos=QtCore.QPointF(float(node_data.get('x', 0.0)) + dx, float(node_data.get('y', 0.0)) + dy),
                title=node_data.get('title'),
                properties=dict(node_data.get('properties', {})),
                inputs=list(node_entry.get('inputs', [])),
                outputs=list(node_entry.get('outputs', [])),
            )
            if old_id:
                id_map[old_id] = new_entry.get('node_data', {}).get('node_id')
            new_nodes.append(new_entry)

        new_connections = []
        for conn_entry in snapshot.get('connections', []):
            source_id = id_map.get(conn_entry.get('source_node_id'))
            target_id = id_map.get(conn_entry.get('target_node_id'))
            if not source_id or not target_id:
                continue
            route_points = []
            for point in conn_entry.get('route_points', []):
                if isinstance(point, (list, tuple)) and len(point) >= 2:
                    route_points.append((float(point[0]) + dx, float(point[1]) + dy))
            new_connections.append({
                'source_node_id': source_id,
                'source_port_name': conn_entry.get('source_port_name'),
                'target_node_id': target_id,
                'target_port_name': conn_entry.get('target_port_name'),
                'route_points': route_points,
            })
        return {'nodes': new_nodes, 'connections': new_connections}

    def paste(self):
        clipboard = QtWidgets.QApplication.clipboard()
        mime = clipboard.mimeData()
        payload = ''
        if mime is not None:
            if mime.hasFormat(self._clipboard_mime_type):
                try:
                    payload = bytes(mime.data(self._clipboard_mime_type)).decode('utf-8')
                except Exception:
                    payload = ''
            elif mime.hasText():
                payload = mime.text()
        if not payload:
            return False
        try:
            snapshot = json.loads(payload)
        except Exception:
            return False
        if not isinstance(snapshot, dict) or 'nodes' not in snapshot:
            return False
        pasted = self._generate_pasted_snapshot(snapshot)
        pasted, blocked_types = self._filter_snapshot_to_active_view(pasted)
        if blocked_types:
            self._status_message("Skipped nodes blocked by the active NoDE view: %s" % ", ".join(blocked_types), 5000)
        if not pasted.get('nodes'):
            return False
        self.undo_stack.push(PasteItemsCommand(self.scene, pasted))
        return True

    def delete_selected_items(self):
        selected = self.scene.selectedItems()
        if not selected:
            return False

        pin_items = [item for item in selected if isinstance(item, ConnectionPinItem)]
        if pin_items:
            grouped = {}
            for pin in pin_items:
                grouped.setdefault(pin.connection_item, set()).add(pin.index)
            self.undo_stack.beginMacro("Delete Connection Pin(s)")
            try:
                for connection, indices in grouped.items():
                    for index in sorted(indices, reverse=True):
                        self.scene.remove_connection_pin(connection, index)
            finally:
                self.undo_stack.endMacro()
            return True

        snapshot = self.scene.snapshot_items_for_delete(selected)
        if not snapshot["nodes"] and not snapshot["connections"]:
            return False
        self.undo_stack.push(DeleteItemsCommand(self.scene, snapshot))
        return True

    def on_selection_changed(self):
        items = self.scene.selectedItems()
        node_item = next((item for item in items if isinstance(item, NodeItem)), None)
        self.selected_node_item = node_item

        if node_item is None:
            self.clear_property_panel()
        else:
            self.populate_property_panel(node_item)

        self._publish_selection_to_data_store(node_item)
        self.selectionChanged.emit(node_item)


    def _build_inspectable_payload(self, node_item, position, node_properties):
        node_data = node_item.node_data
        definition = node_definition_for_type(node_data.node_type)
        fields = [
            build_field_descriptor(
                field_path='properties.title',
                label='Title',
                value=node_data.title,
                value_type='string',
                editable=True,
                category='Identity',
                editor={'kind': 'text', 'clearable': True},
            ),
            build_field_descriptor(
                field_path='properties.node_type',
                label='Node Type',
                value=node_data.node_type,
                value_type='string',
                editable=False,
                category='Identity',
                description='Registered node definition type identifier.',
            ),
            build_field_descriptor(
                field_path='properties.position_x',
                label='Position X',
                value=position['x'],
                value_type='float',
                editable=False,
                category='Identity',
            ),
            build_field_descriptor(
                field_path='properties.position_y',
                label='Position Y',
                value=position['y'],
                value_type='float',
                editable=False,
                category='Identity',
            ),
        ]

        property_defs = {prop.name: prop for prop in (definition.properties if definition is not None else [])}
        visible_properties = {key: value for key, value in node_properties.items() if not str(key).startswith('__')}
        for key in sorted(visible_properties.keys(), key=lambda item: str(item).lower()):
            value = visible_properties.get(key)
            prop_def = property_defs.get(key)
            field_kwargs = {
                'field_path': f'properties.{key}',
                'label': getattr(prop_def, 'label', None) or str(key).replace('_', ' ').title(),
                'value': value,
                'value_type': self._inspectable_value_type(prop_def, value),
                'editable': isinstance(value, (str, int, float, bool)),
                'category': 'Properties',
                'description': getattr(definition, 'description', None) if prop_def is None else None,
                'editor': self._inspectable_editor_hint(prop_def, value),
            }
            fields.append(build_field_descriptor(**field_kwargs))

        identity_fields = [field for field in fields if field.get('category') == 'Identity']
        property_fields = [field for field in fields if field.get('category') != 'Identity']
        sections = [
            build_section(section_id='identity', title='Node', fields=identity_fields),
            build_section(section_id='properties', title='Properties', fields=property_fields),
        ]
        return build_inspectable_object(
            object_id=node_data.node_id,
            object_type='node',
            display_name=node_data.title,
            sections=sections,
            summary={
                'plugin_id': 'NoDE',
                'node_type': node_data.node_type,
                'definition_category': getattr(definition, 'category', None),
            },
            metadata={
                'source_plugin': 'NoDE',
            },
        )

    def _inspectable_value_type(self, prop_def, value):
        prop_type = getattr(prop_def, 'property_type', None)
        if prop_type == 'bool':
            return 'bool'
        if prop_type == 'int':
            return 'int'
        if prop_type == 'float':
            return 'float'
        if prop_type in {'choice', 'string'}:
            return 'string'
        if isinstance(value, bool):
            return 'bool'
        if isinstance(value, int) and not isinstance(value, bool):
            return 'int'
        if isinstance(value, float):
            return 'float'
        return 'string'

    def _inspectable_editor_hint(self, prop_def, value):
        if prop_def is None:
            if isinstance(value, bool):
                return {'kind': 'boolean'}
            if isinstance(value, int) and not isinstance(value, bool):
                return {'kind': 'number', 'numeric': {'minimum': -999999999, 'maximum': 999999999, 'step': 1}}
            if isinstance(value, float):
                return {'kind': 'number', 'numeric': {'minimum': -1e12, 'maximum': 1e12, 'decimals': 6}}
            return {'kind': 'text', 'clearable': True}

        prop_type = getattr(prop_def, 'property_type', 'string')
        if prop_type == 'choice':
            return {
                'kind': 'choice',
                'options': [{'value': option, 'label': str(option)} for option in getattr(prop_def, 'options', [])],
            }
        if prop_type == 'bool':
            return {'kind': 'boolean'}
        if prop_type == 'int':
            return {'kind': 'number', 'numeric': {'minimum': -999999999, 'maximum': 999999999, 'step': 1}}
        if prop_type == 'float':
            return {'kind': 'number', 'numeric': {'minimum': -1e12, 'maximum': 1e12, 'decimals': 6}}
        if getattr(prop_def, 'multiline', False):
            return {'kind': 'multiline', 'multiline': True, 'clearable': True}
        return {'kind': 'text', 'clearable': True}

    def _publish_selection_to_data_store(self, node_item):
        if node_item is None:
            self._selection_publisher.clear()
            return

        node_data = node_item.node_data
        position = {
            'x': round(float(node_item.pos().x()), 3),
            'y': round(float(node_item.pos().y()), 3),
        }
        node_properties = dict(getattr(node_data, 'properties', {}) or {})
        editable_fields = ['properties.title']
        for key, value in node_properties.items():
            if isinstance(value, (str, int, float, bool)):
                editable_fields.append(f'properties.{key}')
        inspectable = self._build_inspectable_payload(node_item, position, node_properties)
        self._selection_publisher.publish(
            object_id=node_data.node_id,
            kind='node',
            display_name=node_data.title,
            properties={
                'title': node_data.title,
                'node_type': node_data.node_type,
                'position_x': position['x'],
                'position_y': position['y'],
                **node_properties,
            },
            metadata={
                'selected': True,
                'editable': True,
                'editable_fields': editable_fields,
                'inspectable': inspectable,
            },
        )

    def populate_property_panel(self, node_item: NodeItem):
        self._updating_property_panel = True
        self.labelNodeIdValue.setText(node_item.node_data.node_id)
        self.labelNodeTypeValue.setText(node_item.node_data.node_type)
        self.editNodeTitle.setText(node_item.node_data.title)
        self._property_title_before_edit = node_item.node_data.title
        self.rebuild_dynamic_property_form(node_item)
        self._sync_dynamic_property_values(node_item)
        self._updating_property_panel = False

    def clear_property_panel(self):
        self._updating_property_panel = True
        self.labelNodeIdValue.setText("—")
        self.labelNodeTypeValue.setText("—")
        self.editNodeTitle.setText("")
        self._property_title_before_edit = ""
        self._clear_form_layout(self.dynamicPropertiesForm)
        self._property_editors = {}
        self.tableEditorGroup.hide()
        self._updating_property_panel = False

    def open_properties_for_node(self, node_item):
        if node_item is None:
            return
        self.selected_node_item = node_item
        self.populate_property_panel(node_item)
        self.dockProperties.show()
        self.dockProperties.raise_()
        self.dockProperties.activateWindow()

    def close_properties_dock(self):
        if self.dockProperties.isVisible():
            self.dockProperties.hide()
            return True
        return False

    def on_node_title_edited(self, text):
        if self._updating_property_panel:
            return
        if self.selected_node_item is None:
            return
        self.selected_node_item.title = text

    def commit_node_title_edit(self):
        if self._updating_property_panel:
            return
        if self.selected_node_item is None:
            return

        old_title = self._property_title_before_edit
        new_title = self.editNodeTitle.text()

        if new_title == old_title:
            return

        self.undo_stack.push(RenameNodeCommand(self.selected_node_item, old_title, new_title))
        self.set_editor_title(new_title)


    def save_state(self):
        graph_data = self._save_current_graph_context() if self._graph_context_stack else (self.collapse_all_inline_subgraphs() or self.scene.serialize_graph())
        if self._graph_context_stack and self._root_graph_data is not None:
            graph_data = self._root_graph_data
        return {
            "editor_title": self.editor_title(),
            "current_file_path": self.current_file_path,
            "properties_visible": self.dockProperties.isVisible(),
            "graph": graph_data,
            "active_node_view_id": self._active_node_view_id,
        }

    def load_state(self, state):
        self._graph_context_stack = []
        self._root_graph_data = None
        self._inline_subgraph_expansions = {}
        if not state:
            self._refresh_node_view_ui()
            return
        graph_data = state.get("graph")
        active_view_id = state.get("active_node_view_id")
        if graph_data:
            metadata = graph_data.get("metadata") if isinstance(graph_data, dict) else None
            if active_view_id is None and isinstance(metadata, dict):
                active_view_id = metadata.get("active_node_view_id")
        self.current_file_path = state.get("current_file_path")
        if active_view_id is not None:
            self.set_active_node_view(active_view_id, announce=False, ignore_lock=True)
        elif graph_data and graph_data.get("nodes") and self.available_node_views():
            default_view = self.available_node_views()[0]
            self.set_active_node_view(default_view.view_id, announce=False, ignore_lock=True)
        else:
            self._refresh_node_view_ui()
        if graph_data:
            if active_view_id is None and graph_data.get("nodes"):
                compatible_view_id = self._find_compatible_view_id_for_graph_data(graph_data)
                if compatible_view_id is not None:
                    self.set_active_node_view(compatible_view_id, announce=False, ignore_lock=True)
            disallowed_types = self._disallowed_node_types_in_graph_data(graph_data)
            if disallowed_types:
                compatible_view_id = self._find_compatible_view_id_for_graph_data(graph_data, preferred_view_id=self._active_node_view_id)
                if compatible_view_id and compatible_view_id != self._active_node_view_id:
                    self.set_active_node_view(compatible_view_id, announce=False, ignore_lock=True)
                    disallowed_types = self._disallowed_node_types_in_graph_data(graph_data)
            if disallowed_types:
                QtWidgets.QMessageBox.warning(
                    self,
                    "NoDE View Compatibility",
                    "This graph contains node types that are not available in the selected NoDE view\n\n%s" % "\n".join(disallowed_types),
                )
            self.scene._suspend_undo = True
            try:
                self.scene.load_graph(self._ensure_graph_control_flow_nodes(graph_data))
            finally:
                self.scene._suspend_undo = False
            self.undo_stack.clear()
        title = state.get("editor_title")
        if title:
            self.set_editor_title(title)
        if state.get("properties_visible"):
            self.dockProperties.show()
        else:
            self.dockProperties.hide()
        dock_execution = getattr(self, 'dockExecution', None)
        if dock_execution is not None:
            if state.get("execution_panel_visible"):
                dock_execution.show()
            else:
                dock_execution.hide()
        self.selected_node_item = None
        self.clear_property_panel()
        self._refresh_node_view_ui()
        self._initial_fit_pending = True
        QtCore.QTimer.singleShot(0, self._ensure_initial_fit)

    def _status_message(self, message, timeout=5000):
        window = self.window()
        if hasattr(window, "statusbar"):
            window.statusbar.showMessage(message, timeout)

    def _default_file_name(self):
        return self.current_file_path or f"{self.editor_title()}.nexnode"

    def save_graph_to_file(self):
        if self.current_file_path:
            self._save_graph_to_path(self.current_file_path)
        else:
            self.save_graph_to_file_as()

    def save_graph_to_file_as(self):
        file_path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Graph",
            self._default_file_name(),
            "Nexus Graph (*.nexnode);;Graph JSON (*.json);;All Files (*)"
        )
        if not file_path:
            return False
        if '.' not in os.path.basename(file_path):
            if selected_filter.startswith('Graph JSON'):
                file_path = f"{file_path}.json"
            else:
                file_path = f"{file_path}.nexnode"
        return self._save_graph_to_path(file_path)

    def _save_graph_to_path(self, file_path):
        graph_data = self._save_current_graph_context() if self._graph_context_stack else (self.collapse_all_inline_subgraphs() or self.scene.serialize_graph())
        if self._graph_context_stack and self._root_graph_data is not None:
            graph_data = self._root_graph_data
        metadata = graph_data.setdefault("metadata", {})
        metadata["active_node_view_id"] = self._active_node_view_id

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(graph_data, f, indent=2)
            self.current_file_path = file_path
            self.set_editor_title(os.path.splitext(os.path.basename(file_path))[0])
            self._status_message(f"Saved graph to {file_path}", 5000)
            return True
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save Failed", f"Could not save graph:\n{exc}")
            return False

    def load_graph_from_file(self, file_path=None):
        if not file_path:
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Load Graph",
                "",
                "Nexus Graph (*.nexnode);;Graph JSON (*.json);;All Files (*)"
            )
        if not file_path:
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)

            self._graph_context_stack = []
            self._root_graph_data = None
            self._inline_subgraph_expansions = {}
            metadata = graph_data.get("metadata") if isinstance(graph_data, dict) else None
            active_view_id = metadata.get("active_node_view_id") if isinstance(metadata, dict) else None
            if active_view_id is not None:
                self.set_active_node_view(active_view_id, announce=False, ignore_lock=True)
            elif not self._graph_has_nodes():
                self._node_view_session.set_active_view_id(None)
                self._active_node_view_id = None
                self._apply_active_node_view_registry()
                self._refresh_node_view_ui()

            if active_view_id is None and graph_data.get("nodes"):
                compatible_view_id = self._find_compatible_view_id_for_graph_data(graph_data)
                if compatible_view_id is not None:
                    self.set_active_node_view(compatible_view_id, announce=False, ignore_lock=True)
            disallowed_types = self._disallowed_node_types_in_graph_data(graph_data)
            if disallowed_types:
                compatible_view_id = self._find_compatible_view_id_for_graph_data(graph_data, preferred_view_id=self._active_node_view_id)
                if compatible_view_id and compatible_view_id != self._active_node_view_id:
                    self.set_active_node_view(compatible_view_id, announce=False, ignore_lock=True)
                    disallowed_types = self._disallowed_node_types_in_graph_data(graph_data)
                if disallowed_types:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "NoDE View Compatibility",
                        "This graph contains node types that are not available in the selected NoDE view\n\n%s" % "\n".join(disallowed_types),
                    )

            self.scene._suspend_undo = True
            try:
                self.scene.load_graph(self._ensure_graph_control_flow_nodes(graph_data))
            finally:
                self.scene._suspend_undo = False

            if self.active_node_view() is None and self._graph_has_content() and self.available_node_views():
                compatible_view_id = self._find_compatible_view_id_for_graph_data(graph_data)
                if compatible_view_id is not None:
                    self.set_active_node_view(compatible_view_id, announce=False, ignore_lock=True)
                else:
                    self.set_active_node_view(self.available_node_views()[0].view_id, announce=False, ignore_lock=True)

            self.undo_stack.clear()
            self.selected_node_item = None
            self.clear_property_panel()
            self._refresh_node_view_ui()
            self._initial_fit_pending = True
            QtCore.QTimer.singleShot(0, self._ensure_initial_fit)
            self.current_file_path = file_path
            self.set_editor_title(os.path.splitext(os.path.basename(file_path))[0])
            self._status_message(f"Loaded graph from {file_path}", 5000)
            return True
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Load Failed", f"Could not load graph:\n{exc}")
            return False



    def closeEvent(self, event):
        if self._action_handler_scope is not None:
            try:
                self._action_handler_scope.clear()
            except Exception:
                pass
            self._action_handler_scope = None
        super().closeEvent(event)
