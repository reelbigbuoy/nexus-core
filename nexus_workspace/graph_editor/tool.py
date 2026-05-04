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
import hashlib
import os
import uuid
from pathlib import Path
from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets
from nexus_workspace.framework.controls import NexusTableEditor
from .geometry import px, qpoint, qrect
from nexus_workspace.core.serialization import NexusSerializable
from nexus_workspace.core.themes import build_stylesheet, get_theme_colors
from nexus_workspace.core.selection_contract import SELECTION_CURRENT_CONTRACT, SelectionPublisher
from nexus_workspace.core.inspectable_contract import build_field_descriptor, build_inspectable_object, build_section
from nexus_workspace.core.action_contract import ACTION_STATUS_HANDLED, ACTION_STATUS_UNHANDLED, PROPERTY_EDIT_REQUEST, normalize_action_request
from .view import GraphView
from .scene import GraphScene
from .commands import AddNodeCommand, DeleteItemsCommand, MoveNodeCommand, MoveInlineExpansionCommand, PasteItemsCommand, RenameNodeCommand, SetNodePropertyCommand
from .definitions import NODE_REGISTRY, NODE_DEFINITIONS_DIR, load_external_node_definitions, node_definition_for_type, create_node_entry
from .node_views import NODE_VIEW_MANIFESTS_DIR, NODE_VIEW_REGISTRY, NodeViewSession, NodeViewRules, load_node_views
from .graphics_items import NodeItem, ConnectionItem, ConnectionPinItem, InlineSubgraphBoundaryItem
from .graph_integrity import GraphIdRewriter, graph_json_safe
from .authoring import GraphCommandDescriptor, GRAPH_COMMAND_REGISTRY, SelectionManager
from .templates import GraphTemplateService
from .validation import GraphValidationEngine







class NoDELiteTool(QtWidgets.QMainWindow, NexusSerializable):
    selectionChanged = QtCore.pyqtSignal(object)
    titleChanged = QtCore.pyqtSignal(str)

    def __init__(
        self,
        parent=None,
        theme_name="Midnight",
        editor_title="Untitled Graph",
        plugin_context=None,
        *,
        tool_type_id="NoDELite",
        plugin_id="NoDELite",
        tool_label="NoDE Lite",
        view_label="NoDE View",
        default_node_view_id=None,
        allowed_node_view_ids=None,
        allowed_node_view_prefixes=None,
    ):
        self.graph_tool_type_id = str(tool_type_id or "NoDELite")
        self.graph_plugin_id = str(plugin_id or self.graph_tool_type_id)
        self.graph_tool_label = str(tool_label or self.graph_tool_type_id)
        self.graph_view_label = str(view_label or "Graph View")
        self.graph_default_node_view_id = default_node_view_id
        self.graph_allowed_node_view_ids = allowed_node_view_ids
        self.graph_allowed_node_view_prefixes = allowed_node_view_prefixes
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
        # Keep graph-type lock state synchronized with graph content changes.
        # Commands are used for normal node add/delete/paste/undo/redo paths, so
        # QUndoStack index changes give us one framework-level hook without
        # coupling STAT policy into the scene or individual commands.
        self.undo_stack.indexChanged.connect(self._on_graph_content_command_index_changed)

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
        self._node_view_session = NodeViewSession(NODE_REGISTRY, NODE_VIEW_REGISTRY, select_default_on_reset=False, allowed_view_ids=self.graph_allowed_node_view_ids, allowed_view_prefixes=self.graph_allowed_node_view_prefixes)
        if self.graph_default_node_view_id:
            self._node_view_session.set_active_view_id(self.graph_default_node_view_id)
        self._active_node_view_id = self._node_view_session.active_view_id()
        self._selection_publisher = SelectionPublisher(plugin_context=plugin_context, tool=self, plugin_id=self.graph_plugin_id)
        self._action_handler_scope = None
        self._graph_context_stack = []
        self._root_graph_data = None
        self._inline_subgraph_expansions = {}
        self.template_service = GraphTemplateService(tool_type_id=self.graph_tool_type_id, plugin_id=self.graph_plugin_id, parent=self)
        self._graph_bookmarks = []
        self.validation_engine = GraphValidationEngine()
        self.validation_issues = []
        self._validation_panel_updating = False

        self._connect_action_requests()
        self._register_shared_authoring_commands()
        self._build_local_menus()
        self._build_local_panels()
        self._apply_view_header_styles()
        self._apply_active_node_view_registry()
        self._refresh_node_view_ui()
        self._refresh_bookmarks_menu()
        self.scene.selectionChanged.connect(self.on_selection_changed)
        self.editNodeTitle.textEdited.connect(self.on_node_title_edited)
        self.editNodeTitle.editingFinished.connect(self.commit_node_title_edit)
        self.setWindowTitle(editor_title)
        self.clear_property_panel()
        self._ensure_current_graph_control_flow_nodes()


    # ------------------------------------------------------------------
    # Shared graph authoring commands
    # ------------------------------------------------------------------
    def _register_shared_authoring_commands(self):
        """Register framework-owned authoring commands only.

        Domain tools may add their own command maps, but nexus-core commands
        must remain generic and must not reference STAT concepts.
        """
        descriptors = [
            GraphCommandDescriptor('graph.align.left', 'Align Left', 'Layout', 'Ctrl+Alt+Left', 'Align selected nodes to the left edge.', lambda: self.align_selected_nodes('left')),
            GraphCommandDescriptor('graph.align.right', 'Align Right', 'Layout', 'Ctrl+Alt+Right', 'Align selected nodes to the right edge.', lambda: self.align_selected_nodes('right')),
            GraphCommandDescriptor('graph.align.center', 'Align Center X', 'Layout', '', 'Align selected items to the anchor center X.', lambda: self.align_selected_nodes('center')),
            GraphCommandDescriptor('graph.align.top', 'Align Top', 'Layout', 'Ctrl+Alt+Up', 'Align selected nodes to the top edge.', lambda: self.align_selected_nodes('top')),
            GraphCommandDescriptor('graph.align.bottom', 'Align Bottom', 'Layout', 'Ctrl+Alt+Down', 'Align selected nodes to the bottom edge.', lambda: self.align_selected_nodes('bottom')),
            GraphCommandDescriptor('graph.align.middle', 'Align Middle Y', 'Layout', '', 'Align selected items to the anchor center Y.', lambda: self.align_selected_nodes('middle')),
            GraphCommandDescriptor('graph.distribute.horizontal', 'Distribute Horizontally', 'Layout', 'Ctrl+Shift+Left/Right', 'Evenly distribute selected nodes horizontally.', lambda: self.distribute_selected_nodes('horizontal')),
            GraphCommandDescriptor('graph.distribute.vertical', 'Distribute Vertically', 'Layout', 'Ctrl+Shift+Up/Down', 'Evenly distribute selected nodes vertically.', lambda: self.distribute_selected_nodes('vertical')),
        ]
        for descriptor in descriptors:
            GRAPH_COMMAND_REGISTRY.register(descriptor)

    def _connect_action_requests(self):
        if self.plugin_context is None or self._action_handler_scope is not None:
            return
        self._action_handler_scope = self.plugin_context.create_action_handler_scope()
        if self._action_handler_scope is None:
            return
        self._action_handler_scope.register(
            action_type=PROPERTY_EDIT_REQUEST,
            callback=self._on_action_requested,
            plugin_id=self.graph_plugin_id,
            target_kind='node',
            target_contract=SELECTION_CURRENT_CONTRACT,
            name=f"{self.graph_tool_type_id}:{id(self)}:property_edit",
        )

    def _on_action_requested(self, payload):
        if not isinstance(payload, dict):
            return {'handled': False}
        payload = normalize_action_request(payload)
        if payload.get('action_type') != PROPERTY_EDIT_REQUEST:
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        target = payload.get('target') or {}
        if target.get('source_plugin') not in {self.graph_plugin_id, self.graph_tool_type_id, 'NoDE'}:
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
            return {'handled': True, 'status': ACTION_STATUS_HANDLED, 'data': {'field_path': field_path, 'property_name': property_name}}
        old_value = node_item.node_data.properties.get(property_name)
        if old_value == value:
            return {'handled': False, 'status': ACTION_STATUS_UNHANDLED}
        self.undo_stack.push(SetNodePropertyCommand(node_item, property_name, old_value, value))
        return {'handled': True, 'status': ACTION_STATUS_HANDLED, 'data': {'field_path': field_path, 'property_name': property_name}}

    def on_node_mutated(self, node_item, update_editor_title=False, refresh_properties=True):
        if node_item is None:
            return
        if self.selected_node_item is node_item:
            if refresh_properties:
                self.populate_property_panel(node_item)
            self._publish_selection_to_data_store(node_item)
        if update_editor_title:
            self.set_editor_title(node_item.node_data.title)
        self.schedule_validation_update()

    def validation_policy(self):
        return None

    def schedule_validation_update(self):
        if getattr(self, '_validation_update_pending', False):
            return
        self._validation_update_pending = True
        QtCore.QTimer.singleShot(0, self.run_graph_validation)

    def run_graph_validation(self):
        self._validation_update_pending = False
        policy = self.validation_policy()
        try:
            self.validation_issues = self.validation_engine.run(self, self.scene, policy)
        except Exception as exc:
            self.validation_issues = []
            self._status_message(f'Graph validation failed: {exc}', 6000)
        if hasattr(self.scene, 'apply_validation_issues'):
            self.scene.apply_validation_issues(self.validation_issues)
        self._refresh_validation_panel()
        self._refresh_validation_button_state()
        return self.validation_issues

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

        self._viewHeaderLabel = QtWidgets.QLabel(self.graph_view_label, self._viewHeaderFrame)
        self._viewHeaderLabel.setObjectName("nodeViewHeaderLabel")

        self._viewHeaderNameBadge = QtWidgets.QLabel("Not Selected", self._viewHeaderFrame)
        self._viewHeaderNameBadge.setObjectName("nodeViewHeaderNameBadge")
        self._viewHeaderNameBadge.setAlignment(QtCore.Qt.AlignCenter)

        self._viewHeaderStateBadge = QtWidgets.QLabel("Select a view to begin", self._viewHeaderFrame)
        self._viewHeaderStateBadge.setObjectName("nodeViewHeaderStateBadge")
        self._viewHeaderStateBadge.setAlignment(QtCore.Qt.AlignCenter)

        self._viewHeaderTypeLabel = QtWidgets.QLabel("Graph Type", self._viewHeaderFrame)
        self._viewHeaderTypeLabel.setObjectName("nodeViewHeaderTypeLabel")
        self._viewHeaderTypeCombo = QtWidgets.QComboBox(self._viewHeaderFrame)
        self._viewHeaderTypeCombo.setObjectName("nodeViewHeaderTypeCombo")
        self._viewHeaderTypeCombo.setMinimumWidth(180)
        self._viewHeaderTypeCombo.currentIndexChanged.connect(self._on_header_node_view_combo_changed)

        self._viewHeaderDescriptionLabel = QtWidgets.QLabel("", self._viewHeaderFrame)
        self._viewHeaderDescriptionLabel.setObjectName("nodeViewHeaderDescriptionLabel")
        self._viewHeaderDescriptionLabel.setWordWrap(True)
        self._viewHeaderDescriptionLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self._reframeButton = QtWidgets.QPushButton("Reframe", self._viewHeaderFrame)
        self._reframeButton.setObjectName("nodeReframeButton")
        self._reframeButton.setToolTip("Frame the visible graph. If multiple nodes are selected, frame the selection.")
        self._reframeButton.clicked.connect(self.frame_selected_or_all)

        self._addBookmarkButton = QtWidgets.QPushButton("Add Bookmark", self._viewHeaderFrame)
        self._addBookmarkButton.setObjectName("nodeAddBookmarkButton")
        self._addBookmarkButton.setToolTip("Bookmark the current graph view or selected region.")
        self._addBookmarkButton.clicked.connect(self.add_graph_bookmark)

        self._bookmarksButton = QtWidgets.QToolButton(self._viewHeaderFrame)
        self._bookmarksButton.setObjectName("nodeBookmarksButton")
        self._bookmarksButton.setText("Bookmarks")
        self._bookmarksButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self._bookmarksButton.setToolTip("Jump to saved graph bookmarks.")

        self._validationButton = QtWidgets.QPushButton("Validation", self._viewHeaderFrame)
        self._validationButton.setObjectName("nodeValidationButton")
        self._validationButton.setToolTip("Show graph validation errors and warnings.")
        self._validationButton.clicked.connect(self.show_validation_panel)

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
        header_layout.addWidget(self._viewHeaderTypeLabel, 0)
        header_layout.addWidget(self._viewHeaderTypeCombo, 0)
        header_layout.addWidget(self._viewHeaderDescriptionLabel, 1)
        header_layout.addWidget(self._reframeButton, 0)
        header_layout.addWidget(self._addBookmarkButton, 0)
        header_layout.addWidget(self._bookmarksButton, 0)
        header_layout.addWidget(self._validationButton, 0)
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

        title = QtWidgets.QLabel(f"Select a {self.graph_view_label}", self._viewSelectionCard)
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

    def _on_graph_content_command_index_changed(self, *_args):
        """Refresh graph-type controls after undoable content mutations.

        The active graph type must lock immediately when the first user node is
        added and unlock when the last user node is removed. We defer one event
        turn so the command redo/undo has fully updated the scene before
        computing required-only vs. user-node content.
        """
        QtCore.QTimer.singleShot(0, self._refresh_graph_type_lock_state)

    def _refresh_graph_type_lock_state(self):
        if not hasattr(self, "_viewHeaderTypeCombo"):
            return
        self._refresh_node_view_ui()

    def _graph_has_nodes(self):
        return any(isinstance(item, NodeItem) for item in self.scene.items())

    def _is_required_graph_node(self, node_item):
        node_data = getattr(node_item, "node_data", None)
        properties = getattr(node_data, "properties", {}) if node_data is not None else {}
        return bool(isinstance(properties, dict) and properties.get("__graph_required"))

    def _graph_has_user_nodes(self):
        return any(isinstance(item, NodeItem) and not self._is_required_graph_node(item) for item in self.scene.items())

    def _graph_has_content(self):
        return any(isinstance(item, (NodeItem, ConnectionItem)) for item in self.scene.items())

    # ------------------------------------------------------------------
    # Linked sub-graph support
    # ------------------------------------------------------------------
    def graph_file_extension_for_view_id(self, view_id):
        """Return the preferred file extension for a graph view.

        Generic graph tools keep the existing .nexnode behavior. Domain tools
        such as STAT can override this to provide view-specific extensions.
        """
        return ".nexnode"

    def graph_file_filter_for_view_id(self, view_id, *, save=False):
        ext = self.graph_file_extension_for_view_id(view_id)
        view = NODE_VIEW_REGISTRY.get(view_id) if view_id else None
        label = view.name if view is not None else "Nexus Graph"
        if ext and not ext.startswith('.'):
            ext = '.' + ext
        if ext:
            return f"{label} (*{ext});;Nexus Graph (*.nexnode);;Graph JSON (*.json);;All Files (*)"
        return "Nexus Graph (*.nexnode);;Graph JSON (*.json);;All Files (*)"

    def _expected_node_view_id_for_container_type(self, container_type):
        """Return the graph view expected for a generic container node.

        Domain-specific tools override this method. The shared framework must
        not know about plugin-specific graph types or file extensions.
        """
        return self._active_node_view_id

    def linked_graph_policy_for_node(self, node_item):
        """Return a policy dict for nodes that may reference external graphs.

        The base framework supports linked graph references, but does not expose
        the UI unless a tool/domain opts in by returning a policy. Expected keys:
        expected_view_id, extension, file_filter, label.
        """
        return None

    def _graph_path_is_valid_for_policy(self, file_path, policy):
        expected_ext = str((policy or {}).get('extension') or '').strip()
        if expected_ext and not expected_ext.startswith('.'):
            expected_ext = '.' + expected_ext
        if expected_ext and Path(file_path).suffix.lower() != expected_ext.lower():
            return False, f"Expected a {expected_ext} graph file."
        return True, ""

    def _load_graph_data_from_path(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        if not isinstance(graph_data, dict):
            raise ValueError("Graph file did not contain a graph object.")
        return graph_data

    def _validate_linked_graph_for_policy(self, file_path, policy, *, show_feedback=True):
        ok, reason = self._graph_path_is_valid_for_policy(file_path, policy)
        if not ok:
            if show_feedback:
                QtWidgets.QMessageBox.warning(self, "Invalid Linked Graph", reason)
            return False, reason
        expected_view_id = (policy or {}).get('expected_view_id')
        try:
            graph_data = self._load_graph_data_from_path(file_path)
        except Exception as exc:
            reason = f"Could not load graph file:\n{exc}"
            if show_feedback:
                QtWidgets.QMessageBox.warning(self, "Invalid Linked Graph", reason)
            return False, reason
        ok, reason = self._validate_graph_payload_for_load(
            graph_data,
            file_path=file_path,
            expected_view_id=expected_view_id,
            show_feedback=False,
        )
        if not ok:
            if show_feedback:
                QtWidgets.QMessageBox.warning(self, "Invalid Linked Graph", reason)
            return False, reason
        return True, ""

    def _linked_graph_path_for_storage(self, file_path):
        # Store an absolute path for now so links remain resolvable even when the
        # containing graph has not been saved yet. This can be upgraded to
        # project-relative paths once Nexus project files are introduced.
        return os.path.abspath(file_path) if file_path else ""

    def _resolve_linked_graph_path(self, stored_path):
        if not stored_path:
            return ""
        if os.path.isabs(stored_path):
            return stored_path
        base = os.path.dirname(self.current_file_path) if self.current_file_path else os.getcwd()
        return os.path.abspath(os.path.join(base, stored_path))

    def _get_active_subgraph_for_node(self, node_item, *, create_if_missing=True, show_feedback=True):
        """Return the graph represented by a container node.

        Embedded mode returns/creates the embedded subgraph. Linked mode loads a
        fresh graph from disk and never writes changes back through the parent.
        """
        props = getattr(getattr(node_item, 'node_data', None), 'properties', {}) or {}
        mode = str(props.get('subgraph_source') or props.get('subgraph_mode') or 'embedded').lower()
        if mode == 'linked':
            path = self._resolve_linked_graph_path(props.get('linked_graph_path') or '')
            if not path or not os.path.exists(path):
                if show_feedback:
                    QtWidgets.QMessageBox.warning(self, "Linked Graph Missing", "The linked graph file could not be found.")
                return None
            policy = self.linked_graph_policy_for_node(node_item)
            ok, _reason = self._validate_linked_graph_for_policy(path, policy, show_feedback=show_feedback)
            if not ok:
                return None
            try:
                graph_data = self._load_graph_data_from_path(path)
            except Exception as exc:
                if show_feedback:
                    QtWidgets.QMessageBox.warning(self, "Linked Graph Load Failed", f"Could not load linked graph:\n{exc}")
                return None
            return self._prepare_linked_graph_data_for_node(graph_data, node_item, policy)
        subgraph = props.get('subgraph')
        if create_if_missing and (not isinstance(subgraph, dict) or not subgraph.get('nodes')):
            subgraph = self._default_subgraph_data(props.get('graph_name') or node_item.node_data.title, node_item.node_data.node_type)
            props['subgraph'] = subgraph
        return subgraph if isinstance(subgraph, dict) else None

    def _prepare_linked_graph_data_for_node(self, graph_data, node_item, policy=None):
        """Prepare externally linked graph data without mutating the parent node.

        Linked graphs are reference-only. They should load and preview using the
        linked file's graph type, not the parent graph's active type.
        """
        if not isinstance(graph_data, dict):
            return None
        metadata = graph_data.setdefault('metadata', {})
        expected_view_id = (policy or {}).get('expected_view_id')
        if expected_view_id and not metadata.get('active_node_view_id'):
            metadata['active_node_view_id'] = expected_view_id
        target_view_id = metadata.get('active_node_view_id') or expected_view_id
        if target_view_id and target_view_id != self._active_node_view_id:
            previous_view_id = self._active_node_view_id
            try:
                self.set_active_node_view(target_view_id, announce=False, ignore_lock=True)
                return self._ensure_graph_control_flow_nodes(graph_data)
            finally:
                if previous_view_id != self._active_node_view_id:
                    self.set_active_node_view(previous_view_id, announce=False, ignore_lock=True)
        return self._ensure_graph_control_flow_nodes(graph_data)

    def is_subgraph_container_node(self, node_item):
        definition = getattr(node_item, "definition", None)
        if definition is None:
            return False
        metadata = getattr(definition, "metadata", {}) or {}
        return bool(metadata.get("is_subgraph_container") or node_item.node_data.node_type == "flow.subgraph_container")

    def _default_subgraph_data(self, graph_name="Sub-Graph", container_type=None):
        target_view_id = self._expected_node_view_id_for_container_type(container_type)
        previous_view_id = self._active_node_view_id
        if target_view_id and target_view_id != self._active_node_view_id:
            self.set_active_node_view(target_view_id, announce=False, ignore_lock=True)
        try:
            graph = self._ensure_graph_control_flow_nodes({"nodes": [], "connections": []})
        finally:
            if previous_view_id != self._active_node_view_id:
                self.set_active_node_view(previous_view_id, announce=False, ignore_lock=True)
        graph.setdefault("metadata", {}).update({
                "active_node_view_id": target_view_id,
                "graph_kind": "subgraph",
                "graph_name": graph_name or "Sub-Graph",
                "container_type": container_type or "",
            })
        return graph

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
        required_specs = self._required_node_specs_for_active_view()
        if required_specs:
            for spec in required_specs:
                if spec.type_id in node_types:
                    for entry in nodes:
                        data = entry.get("node_data", {}) if isinstance(entry, dict) else {}
                        if data.get("node_type") == spec.type_id:
                            if getattr(spec, "title", ""):
                                data["title"] = spec.title
                            props = data.setdefault("properties", {})
                            props["__graph_required"] = True
                            props["__graph_locked"] = bool(getattr(spec, "locked", True))
                            break
                    continue
                props = {"__graph_required": True, "__graph_locked": bool(getattr(spec, "locked", True))}
                title = getattr(spec, "title", "") or None
                nodes.append(create_node_entry(spec.type_id, pos=QtCore.QPointF(float(getattr(spec, "x", 0.0)), float(getattr(spec, "y", 0.0))), title=title, properties=props))
        else:
            if "flow.start" not in node_types:
                nodes.append(create_node_entry("flow.start", pos=QtCore.QPointF(-240, 0), title="Start", properties={"__graph_required": True, "__graph_locked": True}))
            if "flow.end" not in node_types:
                nodes.append(create_node_entry("flow.end", pos=QtCore.QPointF(240, 0), title="End", properties={"__graph_required": True, "__graph_locked": True}))
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
        self._write_bookmark_metadata_to_graph(current_graph)
        if self._graph_context_stack:
            context = self._graph_context_stack[-1]
            if not context.get("reference_only"):
                context["node_properties"]["subgraph"] = current_graph
                context["node_properties"].setdefault("graph_name", metadata.get("graph_name", "Sub-Graph"))
        else:
            self._root_graph_data = current_graph
        return current_graph

    def _load_graph_context(self, graph_data):
        self.collapse_all_inline_subgraphs()
        metadata = (graph_data or {}).get("metadata", {}) if isinstance(graph_data, dict) else {}
        target_view_id = metadata.get("active_node_view_id") if isinstance(metadata, dict) else None
        if target_view_id and target_view_id != self._active_node_view_id:
            self.set_active_node_view(target_view_id, announce=False, ignore_lock=True)
        self.scene._suspend_undo = True
        try:
            payload = self._ensure_graph_control_flow_nodes(graph_data or {"nodes": [], "connections": []})
            self.scene.load_graph(payload)
            self._set_graph_bookmarks_from_payload(payload)
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

        # Capture the current parent graph first so edits made before opening
        # the child are not lost. Then resolve the selected node's active
        # subgraph source from the freshly serialized parent node properties.
        parent_graph = self._save_current_graph_context()
        node_properties = self._find_node_properties_in_graph(parent_graph, node_item.node_data.node_id) or node_item.node_data.properties
        graph_name = node_properties.get("graph_name") or node_item.node_data.title or "Sub-Graph"
        mode = str(node_properties.get('subgraph_source') or node_properties.get('subgraph_mode') or 'embedded').lower()

        parent_view_id = self._active_node_view_id
        parent_metadata = parent_graph.setdefault("metadata", {}) if isinstance(parent_graph, dict) else {}
        if isinstance(parent_metadata, dict) and parent_view_id:
            parent_metadata.setdefault("active_node_view_id", parent_view_id)

        if mode == 'linked':
            # Keep the live item in sync with the serialized parent properties,
            # then use the same active-subgraph resolver used by inline expand.
            node_item.node_data.properties = node_properties
            subgraph = self._get_active_subgraph_for_node(node_item, create_if_missing=False, show_feedback=True)
            if not isinstance(subgraph, dict):
                return False
            metadata = subgraph.get('metadata') if isinstance(subgraph, dict) else {}
            graph_name = (metadata.get('graph_name') if isinstance(metadata, dict) else None) or graph_name
            context = {
                "node_id": node_item.node_data.node_id,
                "title": node_item.node_data.title,
                "node_properties": node_properties,
                "parent_view_id": parent_view_id,
                "reference_only": True,
                "linked_graph_path": node_properties.get('linked_graph_path') or '',
            }
        else:
            subgraph = node_properties.get("subgraph")
            if not isinstance(subgraph, dict) or not subgraph.get("nodes"):
                subgraph = self._default_subgraph_data(graph_name, node_item.node_data.node_type)
                node_properties["subgraph"] = subgraph
            context = {
                "node_id": node_item.node_data.node_id,
                "title": node_item.node_data.title,
                "node_properties": node_properties,
                "parent_view_id": parent_view_id,
            }

        self._graph_context_stack.append(context)
        self._load_graph_context(subgraph)
        self._status_message("Opened linked graph: %s" % graph_name if mode == 'linked' else "Opened sub-graph: %s" % graph_name, 3500)
        return True

    def close_current_subgraph(self):
        if not self._graph_context_stack:
            return False
        self._save_current_graph_context()
        self._graph_context_stack.pop()
        if self._graph_context_stack:
            context = self._graph_context_stack[-1]
            if context.get("reference_only"):
                parent_graph = self._root_graph_data or {"nodes": [], "connections": []}
            else:
                parent_graph = context["node_properties"].get("subgraph", {})
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

    def _make_inline_node_read_only(self, item):
        """Make an inline sub-graph node a read-only preview item.

        Inline expansion is for parent-graph comprehension only. Users must
        double-click/open the container to edit the nested graph. Keeping the
        preview non-interactive prevents cloned subgraph nodes/wires from being
        edited in the parent scene and then discarded on collapse.
        """
        if item is None:
            return
        try:
            item._inline_subgraph_display = True
            item.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
            item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
            item.setAcceptedMouseButtons(QtCore.Qt.NoButton)
            item.setAcceptHoverEvents(False)
            for port in list(getattr(item, "inputs", []) or []) + list(getattr(item, "outputs", []) or []):
                port.setAcceptedMouseButtons(QtCore.Qt.NoButton)
                port.setAcceptHoverEvents(False)
        except RuntimeError:
            pass

    def _make_inline_connection_read_only(self, item):
        """Make an inline sub-graph wire a read-only preview item."""
        if item is None:
            return
        try:
            item._inline_subgraph_display = True
            item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
            item.setAcceptedMouseButtons(QtCore.Qt.NoButton)
            item.setAcceptHoverEvents(False)
            for pin in list(getattr(item, "pin_items", []) or []):
                pin.setVisible(False)
                pin.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
                pin.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
                pin.setAcceptedMouseButtons(QtCore.Qt.NoButton)
                pin.setAcceptHoverEvents(False)
        except RuntimeError:
            pass

    def _capture_inline_base_positions(self):
        base = {}
        try:
            for item in list(self.scene.items()):
                if isinstance(item, NodeItem) and not getattr(item, '_inline_subgraph_display', False):
                    base[item.node_data.node_id] = QtCore.QPointF(item.pos())
        except RuntimeError:
            pass
        self._inline_base_positions = base

    def _restore_inline_base_positions(self):
        for node_id, pos in list((getattr(self, '_inline_base_positions', {}) or {}).items()):
            node = self.scene.find_node_by_id(node_id)
            if node is not None:
                try:
                    node.setPos(QtCore.QPointF(pos))
                except RuntimeError:
                    pass

    def _remove_inline_expansion_visuals(self, expansion, show_container=True, show_connections=True):
        if not expansion:
            return
        container_node = expansion.get("container_node")
        if container_node is not None and show_container:
            try:
                container_node.setVisible(True)
            except RuntimeError:
                pass
        if show_connections:
            for conn in expansion.get("hidden_connections", []) or []:
                try:
                    conn.setVisible(True)
                except RuntimeError:
                    pass
        for conn in list(expansion.get("connections", []) or []):
            try:
                conn.remove_from_ports()
                for pin in list(getattr(conn, 'pin_items', [])):
                    self.scene.removeItem(pin)
                self.scene.removeItem(conn)
            except RuntimeError:
                pass
        for node in list(expansion.get("nodes", []) or []):
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

    def _rebuild_inline_expansions_from_base(self, expanded_ids):
        existing = getattr(self, '_inline_subgraph_expansions', {}) or {}
        for cid, expansion in list(existing.items()):
            self._remove_inline_expansion_visuals(expansion, show_container=True, show_connections=True)
        self._inline_subgraph_expansions = {}
        self._restore_inline_base_positions()

        def _sort_key(cid):
            pos = (getattr(self, '_inline_base_positions', {}) or {}).get(cid)
            if pos is not None:
                return (float(pos.x()), float(pos.y()))
            node = self.scene.find_node_by_id(cid)
            if node is not None:
                try:
                    p = node.pos()
                    return (float(p.x()), float(p.y()))
                except RuntimeError:
                    pass
            return (0.0, 0.0)

        self._rebuilding_inline_expansions = True
        try:
            for cid in sorted([c for c in expanded_ids if c], key=_sort_key):
                node = self.scene.find_node_by_id(cid)
                if node is not None:
                    self.expand_subgraph_node(node)
        finally:
            self._rebuilding_inline_expansions = False

    def _translate_expanded_container_projection(self, container_id, dx, dy=0.0):
        """Move the visible inline projection for an already-expanded container."""
        if not container_id or container_id not in getattr(self, '_inline_subgraph_expansions', {}):
            return False
        return self._translate_inline_expansion(container_id, dx, dy)


    def _capture_inline_expansion_group_state(self, container_id):
        """Capture absolute visual positions for a read-only inline expansion.

        Boundary drags should be applied from this immutable start state rather
        than by incremental deltas. That keeps the dashed boundary, child-node
        projections, internal wires, and bridge wires locked together even when
        Qt sends many move events or when route points are present.
        """
        expansion = (getattr(self, '_inline_subgraph_expansions', {}) or {}).get(container_id)
        if not expansion:
            return None
        state = {
            'container_pos': None,
            'boundary_pos': None,
            'node_positions': [],
            'connection_routes': [],
        }
        container = expansion.get('container_node')
        if container is not None:
            try:
                state['container_pos'] = QtCore.QPointF(container.pos())
            except RuntimeError:
                pass
        boundary = expansion.get('boundary')
        if boundary is not None:
            try:
                state['boundary_pos'] = QtCore.QPointF(boundary.pos())
            except RuntimeError:
                pass
        for node in list(expansion.get('nodes', []) or []):
            try:
                state['node_positions'].append((node, QtCore.QPointF(node.pos())))
            except RuntimeError:
                continue
        for conn in list(expansion.get('connections', []) or []):
            try:
                routes = [QtCore.QPointF(point) for point in list(getattr(conn, 'route_points', []) or [])]
                state['connection_routes'].append((conn, routes))
            except RuntimeError:
                continue
        return state

    def _apply_inline_expansion_group_drag_state(self, container_id, start_state, delta):
        """Apply a boundary drag from a captured start state.

        This is intentionally visual-only for projected child content, while the
        hidden parent container also moves so collapse/save behavior remains
        coherent. Existing wire styling and routing classes are not changed.
        """
        if not start_state:
            return False
        expansion = (getattr(self, '_inline_subgraph_expansions', {}) or {}).get(container_id)
        if not expansion:
            return False
        delta = QtCore.QPointF(delta)
        previous_suspend = bool(getattr(self.scene, '_suspend_undo', False))
        self.scene._suspend_undo = True
        try:
            container = expansion.get('container_node')
            base_container_pos = start_state.get('container_pos')
            if container is not None and base_container_pos is not None:
                try:
                    container.setPos(QtCore.QPointF(base_container_pos) + delta)
                except RuntimeError:
                    pass
            boundary = expansion.get('boundary')
            base_boundary_pos = start_state.get('boundary_pos')
            if boundary is not None and base_boundary_pos is not None:
                try:
                    boundary.setPos(QtCore.QPointF(base_boundary_pos) + delta)
                except RuntimeError:
                    pass
            for node, base_pos in list(start_state.get('node_positions', []) or []):
                try:
                    node.setPos(QtCore.QPointF(base_pos) + delta)
                except RuntimeError:
                    continue
            for conn, base_routes in list(start_state.get('connection_routes', []) or []):
                try:
                    if base_routes:
                        conn.set_route_points([QtCore.QPointF(point) + delta for point in base_routes])
                    conn.update_path()
                    conn.sync_pin_items()
                except RuntimeError:
                    continue
        finally:
            self.scene._suspend_undo = previous_suspend
        if hasattr(self.scene, 'ensure_logical_scene_rect'):
            boundary = expansion.get('boundary')
            if boundary is not None:
                self.scene.ensure_logical_scene_rect(boundary.sceneBoundingRect())
        return True

    def _apply_inline_expansion_group_move(self, container_id, new_container_pos):
        """Move an expanded inline subgraph as one visual/read-only group."""
        expansion = (getattr(self, '_inline_subgraph_expansions', {}) or {}).get(container_id)
        if not expansion:
            return False
        container = expansion.get('container_node')
        if container is None:
            return False
        try:
            old_pos = QtCore.QPointF(container.pos())
            new_pos = QtCore.QPointF(new_container_pos)
        except RuntimeError:
            return False
        if old_pos == new_pos:
            return True
        state = self._capture_inline_expansion_group_state(container_id)
        if not state:
            return False
        return self._apply_inline_expansion_group_drag_state(container_id, state, new_pos - old_pos)

    def handle_inline_boundary_moved(self, container_id, old_pos, new_pos):
        if old_pos == new_pos or self.undo_stack is None:
            return False
        self.undo_stack.push(MoveInlineExpansionCommand(self, container_id, old_pos, new_pos))
        return True

    def _inline_translated_route_points(self, conn_data, anchor, min_x, min_y):
        """Translate sub-graph wire bend points into parent-scene inline coordinates.

        Stored sub-graph route_points are authored in the nested graph's local scene
        coordinate system. Inline expansion offsets child nodes into the parent scene;
        applying the same offset to bend points preserves the exact routing the user
        created when editing the sub-graph directly.
        """
        translated = []
        dx = float(anchor.x()) - float(min_x)
        dy = float(anchor.y()) - float(min_y)
        for point in (conn_data or {}).get("route_points", []) or []:
            try:
                x, y = point
                translated.append([float(x) + dx, float(y) + dy])
            except Exception:
                continue
        return translated

    def _translate_inline_expansion(self, container_id, dx, dy=0.0, move_container=False):
        expansion = self._inline_subgraph_expansions.get(container_id)
        if not expansion:
            return False
        delta = QtCore.QPointF(float(dx), float(dy))
        if move_container:
            container = expansion.get("container_node")
            if container is not None:
                try:
                    container.setPos(container.pos() + delta)
                except RuntimeError:
                    pass
        for node in list(expansion.get("nodes", []) or []):
            try:
                node.setPos(node.pos() + delta)
            except RuntimeError:
                pass
        boundary = expansion.get("boundary")
        if boundary is not None:
            try:
                boundary.setPos(boundary.pos() + delta)
            except RuntimeError:
                pass
        for conn in list(expansion.get("connections", []) or []):
            try:
                if getattr(conn, "route_points", None):
                    conn.set_route_points([QtCore.QPointF(point) + delta for point in conn.route_points])
                else:
                    conn.update_path()
                    conn.sync_pin_items()
            except RuntimeError:
                pass
        return True

    def _shift_inline_expansions_after_x(self, threshold_x, dx, skip_container_id=None):
        shifted = []
        for container_id, expansion in list(getattr(self, "_inline_subgraph_expansions", {}).items()):
            if container_id == skip_container_id:
                continue
            boundary = expansion.get("boundary")
            if boundary is None:
                continue
            try:
                if boundary.sceneBoundingRect().left() > float(threshold_x):
                    if self._translate_inline_expansion(container_id, dx, 0.0):
                        shifted.append({"container_id": container_id, "dx": float(dx)})
            except RuntimeError:
                continue
        return shifted


    def _add_inline_projection_connection_from_dict(self, conn_entry):
        """Add a visual-only inline bridge connection.

        These wires show continuity across an expanded container, but they are
        not persisted, selectable, editable, or counted against input-port
        cardinality. This keeps the hidden parent/container model wire intact
        while letting users see the full path through the expanded subgraph.
        """
        if not isinstance(conn_entry, dict):
            return None
        source_node = self.scene.find_node_by_id(conn_entry.get("source_node_id"))
        target_node = self.scene.find_node_by_id(conn_entry.get("target_node_id"))
        if source_node is None or target_node is None:
            return None
        source_port = self.scene.find_output_port(source_node, conn_entry.get("source_port_name"))
        target_port = self.scene.find_input_port(target_node, conn_entry.get("target_port_name"))
        if source_port is None or target_port is None:
            return None
        route_points = []
        for point in conn_entry.get("route_points", []) or []:
            try:
                x, y = point
                route_points.append(QtCore.QPointF(float(x), float(y)))
            except Exception:
                continue
        citem = self.scene.create_projection_connection(
            source_port,
            target_port,
            route_points=route_points,
            connection_kind=conn_entry.get("connection_kind"),
        )
        if citem is not None:
            self._make_inline_connection_read_only(citem)
        return citem

    def _remove_inline_projection_connections(self, expansion):
        """Remove only visual bridge wires for an inline expansion."""
        if not expansion:
            return
        for conn in list(expansion.get("projection_connections", []) or []):
            try:
                conn.remove_from_ports()
                for pin in list(getattr(conn, 'pin_items', [])):
                    self.scene.removeItem(pin)
                self.scene.removeItem(conn)
            except RuntimeError:
                pass
        expansion["projection_connections"] = []

    def _inline_endpoint_sources_for_external_connection(self, conn_entry):
        """Return source endpoint dictionaries for a real parent-model connection.

        If the real source is itself an expanded container, use that expanded
        container's internal exit node projection endpoint rather than the
        hidden container port. This prevents bridge wires from being drawn back
        to a container's old/collapsed position when multiple containers are
        expanded at once.
        """
        source_node_id = conn_entry.get("source_node_id")
        source_port_name = conn_entry.get("source_port_name")
        source_expansion = (getattr(self, '_inline_subgraph_expansions', {}) or {}).get(source_node_id)
        if source_expansion:
            candidates = list(source_expansion.get("exit_sources", []) or [])
            matched = [item for item in candidates if not item.get("container_port_name") or item.get("container_port_name") == source_port_name]
            return matched or candidates
        return [{
            "node_id": source_node_id,
            "port_name": source_port_name,
        }]

    def _inline_endpoint_targets_for_external_connection(self, conn_entry):
        """Return target endpoint dictionaries for a real parent-model connection.

        If the real target is an expanded container, use that expanded
        container's internal entry node projection endpoint rather than the
        hidden container port.
        """
        target_node_id = conn_entry.get("target_node_id")
        target_port_name = conn_entry.get("target_port_name")
        target_expansion = (getattr(self, '_inline_subgraph_expansions', {}) or {}).get(target_node_id)
        if target_expansion:
            candidates = list(target_expansion.get("entry_targets", []) or [])
            matched = [item for item in candidates if not item.get("container_port_name") or item.get("container_port_name") == target_port_name]
            return matched or candidates
        return [{
            "node_id": target_node_id,
            "port_name": target_port_name,
        }]

    def _add_inline_projection_connection_between_endpoints(self, source_ep, target_ep, connection_kind=None):
        if not source_ep or not target_ep:
            return None
        conn_entry = {
            "source_node_id": source_ep.get("node_id"),
            "source_port_name": source_ep.get("port_name"),
            "target_node_id": target_ep.get("node_id"),
            "target_port_name": target_ep.get("port_name"),
            "route_points": [],
            "connection_kind": connection_kind,
        }
        return self._add_inline_projection_connection_from_dict(conn_entry)

    def _refresh_inline_projection_connections(self):
        """Rebuild all inter-layer bridge wires for expanded containers.

        This is intentionally a separate pass from creating inline node clones.
        With multiple expanded containers, a real parent connection may run from
        container A to container B. Both containers are hidden while expanded, so
        bridge endpoints must resolve to A's internal exit projection and B's
        internal entry projection. Rebuilding all bridges after the expansion set
        changes prevents stale wires from pointing at a container's old position.
        """
        expansions = getattr(self, '_inline_subgraph_expansions', {}) or {}
        if not expansions:
            return
        for expansion in list(expansions.values()):
            self._remove_inline_projection_connections(expansion)

        try:
            graph_connections = list(self.scene.serialize_graph().get("connections", []) or [])
        except Exception:
            graph_connections = []

        seen = set()
        created_by_container = {cid: [] for cid in expansions.keys()}

        for conn in graph_connections:
            src_id = conn.get("source_node_id")
            tgt_id = conn.get("target_node_id")
            if src_id not in expansions and tgt_id not in expansions:
                continue
            source_eps = self._inline_endpoint_sources_for_external_connection(conn)
            target_eps = self._inline_endpoint_targets_for_external_connection(conn)
            for source_ep in source_eps:
                for target_ep in target_eps:
                    key = (
                        source_ep.get("node_id"), source_ep.get("port_name"),
                        target_ep.get("node_id"), target_ep.get("port_name"),
                        conn.get("connection_kind"),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    citem = self._add_inline_projection_connection_between_endpoints(source_ep, target_ep, connection_kind=conn.get("connection_kind"))
                    if citem is None:
                        continue
                    # Track the projection under every expanded container it is
                    # visually bridging so cleanup remains deterministic.
                    owners = {cid for cid in (src_id, tgt_id) if cid in expansions}
                    if not owners:
                        owners = set(expansions.keys())
                    for cid in owners:
                        created_by_container.setdefault(cid, []).append(citem)

        for cid, items in created_by_container.items():
            if cid in expansions:
                expansions[cid]["projection_connections"] = items
                connections = list(expansions[cid].get("internal_connections", []) or [])
                for item in items:
                    if item not in connections:
                        connections.append(item)
                expansions[cid]["connections"] = connections

    def expand_subgraph_node(self, node_item):
        """Visually expand a sub-graph inline without permanently flattening the model."""
        if not self.is_subgraph_container_node(node_item):
            return False
        container_id = node_item.node_data.node_id
        if container_id in self._inline_subgraph_expansions:
            return True
        if not getattr(self, '_rebuilding_inline_expansions', False) and not getattr(self, '_inline_subgraph_expansions', {}):
            self._capture_inline_base_positions()
        subgraph = self._get_active_subgraph_for_node(node_item, create_if_missing=True, show_feedback=True)
        if not isinstance(subgraph, dict):
            return False
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
        # Inline expansion is a reversible visual projection. Only record the
        # nodes actually shifted by this expansion; never restore a full-scene
        # snapshot because multiple open expansions can otherwise fight each
        # other when one collapses.
        shifted_positions = {}
        created_nodes = []
        created_connections = []
        hidden_connections = []
        try:
            threshold_x = node_item.sceneBoundingRect().right() + 20.0
            for item in list(self.scene.items()):
                if isinstance(item, NodeItem) and item is not node_item and not getattr(item, '_inline_subgraph_display', False):
                    if item.scenePos().x() > threshold_x:
                        shifted_positions[item.node_data.node_id] = QtCore.QPointF(item.pos())
                        item.setPos(item.pos() + QtCore.QPointF(shift_amount, 0.0))
            shifted_inline_expansions = self._shift_inline_expansions_after_x(threshold_x, shift_amount, skip_container_id=container_id)
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
                    self._make_inline_node_read_only(item)
                    item.setOpacity(0.96)
                    created_nodes.append(item)
            start_edges = [c for c in subgraph.get("connections", []) if c.get("source_node_id") in start_ids and c.get("target_node_id") not in end_ids]
            end_edges = [c for c in subgraph.get("connections", []) if c.get("target_node_id") in end_ids and c.get("source_node_id") not in start_ids]
            entry_targets = []
            for edge in start_edges:
                target_node_id = self._new_node_id(edge.get("target_node_id"), remap)
                target_port_name = edge.get("target_port_name")
                if target_node_id and target_port_name:
                    entry_targets.append({
                        "node_id": target_node_id,
                        "port_name": target_port_name,
                        "container_port_name": edge.get("source_port_name"),
                    })
            exit_sources = []
            for edge in end_edges:
                source_node_id = self._new_node_id(edge.get("source_node_id"), remap)
                source_port_name = edge.get("source_port_name")
                if source_node_id and source_port_name:
                    exit_sources.append({
                        "node_id": source_node_id,
                        "port_name": source_port_name,
                        "container_port_name": edge.get("target_port_name"),
                    })

            previous_inline_preview_flag = bool(getattr(self.scene, '_allow_inline_preview_connections', False))
            self.scene._allow_inline_preview_connections = True
            try:
                for conn in subgraph.get("connections", []):
                    src, tgt = conn.get("source_node_id"), conn.get("target_node_id")
                    if src in start_ids or tgt in end_ids or src in end_ids or tgt in start_ids:
                        continue
                    cloned = dict(conn)
                    cloned["source_node_id"] = self._new_node_id(src, remap)
                    cloned["target_node_id"] = self._new_node_id(tgt, remap)
                    cloned["route_points"] = self._inline_translated_route_points(conn, anchor, min_x, min_y)
                    citem = self.scene.add_connection_from_dict(cloned)
                    if citem is not None:
                        self._make_inline_connection_read_only(citem)
                        created_connections.append(citem)
            finally:
                self.scene._allow_inline_preview_connections = previous_inline_preview_flag
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
                "internal_connections": list(created_connections),
                "projection_connections": [],
                "connections": list(created_connections),
                "entry_targets": entry_targets,
                "exit_sources": exit_sources,
                "boundary": boundary,
                "shifted_positions": shifted_positions,
                "hidden_connections": hidden_connections,
                "container_node": node_item,
                "shifted_inline_expansions": shifted_inline_expansions,
            }
            self._refresh_inline_projection_connections()
        finally:
            self.scene._suspend_undo = False
        self.scene.clearSelection()
        if not getattr(self, '_rebuilding_inline_expansions', False):
            self._reframe_visible_graph_after_layout_change()
            self._status_message("Expanded sub-graph inline", 3500)
        return True

    def collapse_inline_subgraph(self, container_node_id):
        expansion = self._inline_subgraph_expansions.pop(container_node_id, None)
        if not expansion:
            return False
        self.scene._suspend_undo = True
        try:
            self._remove_inline_expansion_visuals(expansion, show_container=True, show_connections=True)
            remaining_ids = list((getattr(self, '_inline_subgraph_expansions', {}) or {}).keys())
            if remaining_ids:
                self._rebuild_inline_expansions_from_base(remaining_ids)
            else:
                self._restore_inline_base_positions()
                self._inline_base_positions = {}
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
        self._viewHeaderLabel.setText(self.graph_view_label)
        self._viewHeaderNameBadge.setText(view_name)
        if has_view:
            description = view_definition.description or "This view filters the available node definitions for the graph."
            if self._graph_has_user_nodes():
                state_text = "Locked after node placement"
                state_role = "locked"
            else:
                state_text = "Open for graph type selection"
                state_role = "editable"
        else:
            description = f"Choose a {self.graph_view_label} before opening the graph canvas."
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
        self._sync_header_node_view_combo()
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

    def _sync_header_node_view_combo(self):
        if not hasattr(self, '_viewHeaderTypeCombo'):
            return
        views = self.available_node_views()
        visible = len(views) > 1
        self._viewHeaderTypeLabel.setVisible(visible)
        self._viewHeaderTypeCombo.setVisible(visible)
        self._viewHeaderTypeCombo.blockSignals(True)
        try:
            self._viewHeaderTypeCombo.clear()
            for view in views:
                self._viewHeaderTypeCombo.addItem(view.name, view.view_id)
            if self._active_node_view_id:
                index = self._viewHeaderTypeCombo.findData(self._active_node_view_id)
                if index >= 0:
                    self._viewHeaderTypeCombo.setCurrentIndex(index)
            enabled = bool(visible and not self._graph_has_user_nodes() and not getattr(self, '_graph_context_stack', []))
            self._viewHeaderTypeCombo.setEnabled(enabled)
            tooltip = "Graph type can be changed until the first non-required node is placed."
            if not enabled and visible:
                tooltip = "Remove all non-required nodes before changing the graph type."
            self._viewHeaderTypeCombo.setToolTip(tooltip)
        finally:
            self._viewHeaderTypeCombo.blockSignals(False)

    def _on_header_node_view_combo_changed(self, index):
        if not hasattr(self, '_viewHeaderTypeCombo') or index < 0:
            return
        view_id = self._viewHeaderTypeCombo.itemData(index)
        if view_id and view_id != self._active_node_view_id:
            self.set_active_node_view(view_id, announce=True)

    def _update_view_selection_description(self):
        index = self._viewSelectionCombo.currentIndex()
        view_id = self._viewSelectionCombo.itemData(index) if index >= 0 else None
        view_definition = NODE_VIEW_REGISTRY.get(view_id) if view_id else None
        if view_definition is None:
            self._viewSelectionDescription.setText(f"No {self.graph_view_label}s are currently available.")
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
        QLabel#nodeViewHeaderTypeLabel {
            color: rgba(230, 230, 230, 0.72);
            font-weight: 600;
            padding-left: 6px;
        }
        QComboBox#nodeViewHeaderTypeCombo {
            min-height: 24px;
            padding: 2px 8px;
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
        preview_session = NodeViewSession(NODE_REGISTRY, NODE_VIEW_REGISTRY, select_default_on_reset=False, allowed_view_ids=self.graph_allowed_node_view_ids, allowed_view_prefixes=self.graph_allowed_node_view_prefixes)
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

        def add_candidate(view_id):
            if view_id and view_id not in candidate_ids and self._view_id_allowed_for_tool(view_id):
                candidate_ids.append(view_id)

        # Caller preference wins first, then the tool-specific default. This is
        # Tool-specific defaults win before alphabetic view order so domain
        # plugins can choose their preferred compatible view without core
        # knowing those domain concepts.
        add_candidate(preferred_view_id)
        add_candidate(getattr(self, "graph_default_node_view_id", None))
        default_view = NODE_VIEW_REGISTRY.default_view()
        if default_view is not None:
            add_candidate(default_view.view_id)
        for view in self.available_node_views():
            add_candidate(view.view_id)
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

    def _required_node_specs_for_active_view(self):
        rules = self.active_node_view_rules()
        return [spec for spec in list(getattr(rules, "required_nodes", []) or []) if getattr(spec, "type_id", None)]

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
                self._status_message(f"Select a {self.graph_view_label} before adding nodes.", 3500)
            return False
        if not self._node_type_allowed_in_registry(node_type):
            if show_feedback:
                self._status_message(f"Node type is not available in the active {self.graph_view_label}.", 4000)
            return False
        rules = self.active_node_view_rules()
        counts = dict(counts_override or self._graph_node_type_counts())
        total_count = sum(counts.values())
        proposed_total = total_count + 1
        if rules.max_nodes is not None and proposed_total > int(rules.max_nodes):
            if show_feedback:
                self._status_message(f"Active {self.graph_view_label} allows at most %d nodes." % int(rules.max_nodes), 4500)
            return False
        type_limit = (rules.max_nodes_per_type or {}).get(node_type)
        if type_limit is not None:
            proposed_count = counts.get(node_type, 0) + 1
            if proposed_count > int(type_limit):
                definition = NODE_REGISTRY.get(node_type)
                label = definition.display_name if definition is not None else node_type
                if show_feedback:
                    self._status_message(f"Active {self.graph_view_label} allows at most %d '%s' nodes." % (int(type_limit), label), 4500)
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

    def _port_node_type_id(self, port):
        node = getattr(port, 'parent_node', None)
        node_data = getattr(node, 'node_data', None) if node is not None else None
        return getattr(node_data, 'node_type', None)

    def _matches_node_type_rule(self, source_port, target_port, rule):
        connection_kind = self._connection_kind_for_ports(source_port, target_port)
        return (
            self._rule_value_matches(self._port_node_type_id(source_port), getattr(rule, 'source_type_id', '*')) and
            self._rule_value_matches(self._port_node_type_id(target_port), getattr(rule, 'target_type_id', '*')) and
            self._rule_value_matches(connection_kind, getattr(rule, 'connection_kind', '*'))
        )

    @staticmethod
    def _normal_data_type_token(value):
        value = str(value or 'any').strip()
        aliases = {
            'string': 'str',
            'boolean': 'bool',
            'none': 'NoneType',
            'object': 'complex',
            'integer': 'int',
            'double': 'float',
        }
        return aliases.get(value.lower(), value).lower()

    def _data_types_are_compatible(self, source_port, target_port):
        source_type = self._normal_data_type_token(self._port_data_type(source_port) or 'any')
        target_type = self._normal_data_type_token(self._port_data_type(target_port) or 'any')
        if source_type in ('', 'any', '*') or target_type in ('', 'any', '*'):
            return True
        return source_type == target_type

    def _remove_invalid_connections_for_node(self, node_item):
        """Drop connections that no longer pass active view rules after a port metadata edit."""
        if node_item is None or not hasattr(self, 'scene') or self.scene is None:
            return 0
        removed = 0
        affected_ports = list(getattr(node_item, 'inputs', []) or []) + list(getattr(node_item, 'outputs', []) or [])
        affected_connections = []
        seen = set()
        for port in affected_ports:
            for conn in list(getattr(port, 'connections', []) or []):
                if id(conn) not in seen:
                    seen.add(id(conn))
                    affected_connections.append(conn)
        for conn in affected_connections:
            source = getattr(conn, 'source_port', None)
            target = getattr(conn, 'target_port', None)
            if source is None or target is None:
                continue
            # A data-port metadata change should only invalidate data wires.
            # Execution wires remain governed by execution sequencing/cycle rules.
            if self._connection_kind_for_ports(source, target) != 'data':
                continue
            allowed_by_view, _reason = self._check_connection_view_rules(source, target)
            if allowed_by_view:
                continue
            try:
                conn.remove_from_ports()
                self.scene.removeItem(conn)
                removed += 1
            except Exception:
                pass
        if removed:
            self._status_message(f'Removed {removed} incompatible data connection(s).', 3500)
            self.scene.update()
        return removed

    def _check_connection_view_rules(self, source_port, target_port):
        rules = self.active_node_view_rules()

        # Resolve the connection kind first and use it as the policy boundary.
        # Execution sequencing rules and data-type rules are intentionally
        # separate: data validation must never reject/allow execution wires,
        # and execution-flow rules must never be used as a substitute for data
        # port compatibility checks.
        connection_kind = self._connection_kind_for_ports(source_port, target_port)
        if not connection_kind:
            return False, 'Ports use incompatible connection kinds.'
        connection_kind = str(connection_kind).strip().lower()

        blocked_category_rules = list(getattr(rules, 'blocked_connection_category_rules', []) or [])
        for rule in blocked_category_rules:
            if self._matches_category_rule(source_port, target_port, rule):
                return False, f'Active {self.graph_view_label} blocks this category-to-category connection.'

        allowed_category_rules = list(getattr(rules, 'allowed_connection_category_rules', []) or [])
        if allowed_category_rules:
            if not any(self._matches_category_rule(source_port, target_port, rule) for rule in allowed_category_rules):
                return False, f'Active {self.graph_view_label} does not allow this category-to-category connection.'

        blocked_connection_kind_rules = list(getattr(rules, 'blocked_connection_kind_rules', []) or [])
        for rule in blocked_connection_kind_rules:
            if self._matches_connection_kind_rule(source_port, target_port, rule):
                return False, f'Active {self.graph_view_label} blocks this connection kind.'

        allowed_connection_kind_rules = list(getattr(rules, 'allowed_connection_kind_rules', []) or [])
        if allowed_connection_kind_rules:
            if not any(self._matches_connection_kind_rule(source_port, target_port, rule) for rule in allowed_connection_kind_rules):
                return False, f'Active {self.graph_view_label} does not allow this connection kind.'

        # Data-type allow/block rules are scoped to data wires only. Static
        # execution ports often carry data_type='exec' for rendering/metadata,
        # but they should not be processed by Python primitive type checks.
        if connection_kind == 'data':
            blocked_data_type_rules = list(getattr(rules, 'blocked_connection_data_type_rules', []) or [])
            for rule in blocked_data_type_rules:
                if self._matches_data_type_rule(source_port, target_port, rule):
                    return False, f'Active {self.graph_view_label} blocks this data-type connection.'

            allowed_data_type_rules = list(getattr(rules, 'allowed_connection_data_type_rules', []) or [])
            if allowed_data_type_rules:
                if not any(self._matches_data_type_rule(source_port, target_port, rule) for rule in allowed_data_type_rules):
                    return False, f'Active {self.graph_view_label} does not allow this data-type connection.'

            if getattr(rules, 'enforce_data_type_compatibility', False) and not self._data_types_are_compatible(source_port, target_port):
                return False, f'Active {self.graph_view_label} requires compatible port data types.'

        blocked_node_type_rules = list(getattr(rules, 'blocked_connection_node_type_rules', []) or [])
        for rule in blocked_node_type_rules:
            if self._matches_node_type_rule(source_port, target_port, rule):
                return False, f'Active {self.graph_view_label} blocks this node sequence.'

        allowed_node_type_rules = list(getattr(rules, 'allowed_connection_node_type_rules', []) or [])
        if allowed_node_type_rules:
            if not any(self._matches_node_type_rule(source_port, target_port, rule) for rule in allowed_node_type_rules):
                return False, f'Active {self.graph_view_label} does not allow this node sequence.'

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
            self._status_message(f"Active {self.graph_view_label} does not allow graph cycles.", 3500)
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
            QtWidgets.QMessageBox.information(self, f"Select {self.graph_view_label}", f"Choose a {self.graph_view_label} before opening the graph canvas.")
            return False
        self.set_active_node_view(view_id)
        self.graphView.setFocus()
        return True

    def _can_change_node_view(self, target_view_id=None, show_feedback=True):
        target_view_id = target_view_id or None
        if target_view_id == self._active_node_view_id:
            return True
        if self._graph_has_user_nodes():
            if show_feedback:
                QtWidgets.QMessageBox.information(
                    self,
                    f"{self.graph_view_label} Locked",
                    f"This graph already contains user-placed nodes. Remove all non-required nodes before changing the graph type.",
                )
                self._status_message(f"{self.graph_view_label} is locked after user nodes are placed on the graph.", 4000)
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
        # Default opening width only. Users may shrink below this manually.
        self._properties_default_width = 300
        self.dockProperties.setMinimumWidth(40)

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
        table_policy = self.table_editor_policy()
        self.btnImportTableCsv = QtWidgets.QPushButton("Import CSV", self.tableEditorGroup)
        self.btnAddTableColumn = QtWidgets.QPushButton("Add Column", self.tableEditorGroup)
        self.btnRenameTableColumn = QtWidgets.QPushButton("Rename Column", self.tableEditorGroup)
        self.btnRemoveTableColumn = QtWidgets.QPushButton("Remove Column", self.tableEditorGroup)
        self.btnAddTableRow = QtWidgets.QPushButton("Add Row", self.tableEditorGroup)
        self.btnRemoveTableRow = QtWidgets.QPushButton("Remove Row", self.tableEditorGroup)
        table_buttons = [self.btnImportTableCsv, self.btnAddTableColumn]
        if table_policy.get("show_rename_button", True):
            table_buttons.append(self.btnRenameTableColumn)
        table_buttons.extend([self.btnRemoveTableColumn, self.btnAddTableRow, self.btnRemoveTableRow])
        for btn in table_buttons:
            table_toolbar.addWidget(btn)
        self.btnRenameTableColumn.setVisible(table_policy.get("show_rename_button", True))
        table_toolbar.addStretch(1)
        table_layout.addLayout(table_toolbar)
        self.tableColumnsSummary = QtWidgets.QLabel("", self.tableEditorGroup)
        self.tableColumnsSummary.setWordWrap(True)
        table_layout.addWidget(self.tableColumnsSummary)
        self.tableWidget = NexusTableEditor(
            self.tableEditorGroup,
            object_name="GraphTableDataEditor",
            enable_sorting=table_policy.get("enable_sorting", True),
            enable_filtering=table_policy.get("enable_filtering", True),
            allow_structure_edit=True,
            editable_cells=True,
            spreadsheet_mode=True,
            selection_behavior=QtWidgets.QAbstractItemView.SelectItems,
        )
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
        self.tableWidget.tableDataChanged.connect(self.on_table_widget_data_changed)
        self.tableWidget.structureChanged.connect(self.on_table_widget_structure_changed)
        self.tableWidget.columnRenamed.connect(self.on_table_widget_column_renamed)


        self.messageSchemaGroup = QtWidgets.QGroupBox("Message Field Selection", properties_host)
        message_schema_layout = QtWidgets.QVBoxLayout(self.messageSchemaGroup)
        self.messageSchemaHint = QtWidgets.QLabel("Choose message type/topic above. Check primitive fields to include them.", self.messageSchemaGroup)
        self.messageSchemaHint.setWordWrap(True)
        message_schema_layout.addWidget(self.messageSchemaHint)
        self.messageSchemaTree = QtWidgets.QTreeWidget(self.messageSchemaGroup)
        self.messageSchemaTree.setColumnCount(3)
        self.messageSchemaTree.setHeaderLabels(["Field", "Type", "Value"])
        self.messageSchemaTree.setRootIsDecorated(True)
        self.messageSchemaTree.setAlternatingRowColors(False)
        self.messageSchemaTree.itemChanged.connect(self.on_message_schema_tree_item_changed)
        message_schema_layout.addWidget(self.messageSchemaTree)
        self.messageSchemaGroup.hide()

        self.dynamicPortsGroup = QtWidgets.QGroupBox("Data Ports", properties_host)
        ports_layout = QtWidgets.QVBoxLayout(self.dynamicPortsGroup)
        ports_toolbar = QtWidgets.QHBoxLayout()
        self.btnAddInputPort = QtWidgets.QPushButton("Add Input Pair", self.dynamicPortsGroup)
        self.btnAddOutputPort = QtWidgets.QPushButton("Add Output", self.dynamicPortsGroup)
        self.btnRemoveDynamicPort = QtWidgets.QPushButton("Remove Selected", self.dynamicPortsGroup)
        for btn in (self.btnAddInputPort, self.btnAddOutputPort, self.btnRemoveDynamicPort):
            ports_toolbar.addWidget(btn)
        ports_toolbar.addStretch(1)
        ports_layout.addLayout(ports_toolbar)
        self.dynamicPortsTable = QtWidgets.QTableWidget(self.dynamicPortsGroup)
        self.dynamicPortsTable.setColumnCount(4)
        self.dynamicPortsTable.setHorizontalHeaderLabels(["Direction", "Name", "Data Type", "Pair"])
        self.dynamicPortsTable.horizontalHeader().setStretchLastSection(True)
        self.dynamicPortsTable.verticalHeader().setVisible(False)
        self.dynamicPortsTable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.dynamicPortsTable.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        ports_layout.addWidget(self.dynamicPortsTable)
        self.dynamicPortsGroup.hide()
        self._dynamic_ports_updating = False
        self.btnAddInputPort.clicked.connect(self.add_dynamic_input_pair)
        self.btnAddOutputPort.clicked.connect(self.add_dynamic_output_port)
        self.btnRemoveDynamicPort.clicked.connect(self.remove_selected_dynamic_port)
        self.dynamicPortsTable.itemChanged.connect(self.on_dynamic_port_table_item_changed)

        self.subgraphSourceGroup = QtWidgets.QGroupBox("Subgraph Source", properties_host)
        subgraph_layout = QtWidgets.QVBoxLayout(self.subgraphSourceGroup)
        self.radioEmbeddedSubgraph = QtWidgets.QRadioButton("Embedded graph", self.subgraphSourceGroup)
        self.radioLinkedSubgraph = QtWidgets.QRadioButton("Linked graph file (reference only)", self.subgraphSourceGroup)
        subgraph_layout.addWidget(self.radioEmbeddedSubgraph)
        subgraph_layout.addWidget(self.radioLinkedSubgraph)
        link_row = QtWidgets.QHBoxLayout()
        self.editLinkedGraphPath = QtWidgets.QLineEdit(self.subgraphSourceGroup)
        self.editLinkedGraphPath.setReadOnly(True)
        self.btnBrowseLinkedGraph = QtWidgets.QPushButton("Browse…", self.subgraphSourceGroup)
        self.btnClearLinkedGraph = QtWidgets.QPushButton("Clear", self.subgraphSourceGroup)
        link_row.addWidget(self.editLinkedGraphPath, 1)
        link_row.addWidget(self.btnBrowseLinkedGraph)
        link_row.addWidget(self.btnClearLinkedGraph)
        subgraph_layout.addLayout(link_row)
        self.linkedGraphHint = QtWidgets.QLabel("Linked graphs are references. Open the graph file directly to edit it.", self.subgraphSourceGroup)
        self.linkedGraphHint.setWordWrap(True)
        subgraph_layout.addWidget(self.linkedGraphHint)
        self.subgraphSourceGroup.hide()
        self._subgraph_source_updating = False
        self.radioEmbeddedSubgraph.toggled.connect(self.on_subgraph_source_mode_changed)
        self.radioLinkedSubgraph.toggled.connect(self.on_subgraph_source_mode_changed)
        self.btnBrowseLinkedGraph.clicked.connect(self.browse_linked_graph_for_selected_node)
        self.btnClearLinkedGraph.clicked.connect(self.clear_linked_graph_for_selected_node)

        root_layout.addLayout(self.propertiesForm)
        root_layout.addWidget(self.dynamicPropertiesContainer)
        root_layout.addWidget(self.tableEditorGroup)
        root_layout.addWidget(self.messageSchemaGroup)
        root_layout.addWidget(self.dynamicPortsGroup)
        root_layout.addWidget(self.subgraphSourceGroup)
        root_layout.addStretch(1)

        self.dockProperties.setWidget(properties_host)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.dockProperties)
        self.dockProperties.resize(px(self._properties_default_width), px(self.dockProperties.height()))
        self.dockProperties.hide()

        self._build_validation_panel()

    def _build_validation_panel(self):
        """Create the shared, read-only validation issue panel.

        The panel is framework-owned. Domain plugins, such as STAT, only provide
        validation issues through their validation policy. The panel renders
        whatever issues the active policy returns and provides navigation back
        to the affected graph items.
        """
        self.dockValidation = QtWidgets.QDockWidget("Validation", self)
        self.dockValidation.setObjectName(f"dockValidation_{id(self)}")
        self.dockValidation.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea |
            QtCore.Qt.RightDockWidgetArea |
            QtCore.Qt.BottomDockWidgetArea
        )
        self.dockValidation.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetClosable
        )

        host = QtWidgets.QWidget(self.dockValidation)
        layout = QtWidgets.QVBoxLayout(host)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.validationSummaryLabel = QtWidgets.QLabel("No validation issues", host)
        self.validationSummaryLabel.setObjectName("graphValidationSummaryLabel")
        self.validationSummaryLabel.setWordWrap(True)
        layout.addWidget(self.validationSummaryLabel)

        self.validationTree = QtWidgets.QTreeWidget(host)
        self.validationTree.setObjectName("graphValidationTree")
        self.validationTree.setColumnCount(3)
        self.validationTree.setHeaderLabels(["Severity", "Issue", "Code"])
        self.validationTree.setRootIsDecorated(True)
        self.validationTree.setUniformRowHeights(False)
        self.validationTree.setAlternatingRowColors(False)
        self.validationTree.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.validationTree.itemActivated.connect(self._on_validation_tree_item_activated)
        self.validationTree.itemClicked.connect(self._on_validation_tree_item_clicked)
        self.validationTree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.validationTree.customContextMenuRequested.connect(self._show_validation_tree_context_menu)
        layout.addWidget(self.validationTree, 1)

        button_row = QtWidgets.QHBoxLayout()
        self.btnRefreshValidation = QtWidgets.QPushButton("Refresh", host)
        self.btnRefreshValidation.clicked.connect(self.run_graph_validation)
        self.btnFrameValidationIssue = QtWidgets.QPushButton("Focus Selected", host)
        self.btnFrameValidationIssue.clicked.connect(self.focus_selected_validation_issue)
        button_row.addWidget(self.btnRefreshValidation)
        button_row.addWidget(self.btnFrameValidationIssue)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.dockValidation.setWidget(host)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.dockValidation)
        self.dockValidation.hide()
        self._refresh_validation_panel()

    def _validation_issue_title(self, issue):
        return str(getattr(issue, 'message', '') or 'Validation issue')

    def _validation_issue_severity(self, issue):
        severity = str(getattr(issue, 'state', None) or getattr(issue, 'severity', '') or 'warning').strip().lower()
        return 'error' if severity == 'error' else 'warning'

    def _refresh_validation_panel(self):
        if not hasattr(self, 'validationTree'):
            return
        self._validation_panel_updating = True
        try:
            self.validationTree.clear()
            issues = list(getattr(self, 'validation_issues', []) or [])
            errors = [issue for issue in issues if self._validation_issue_severity(issue) == 'error']
            warnings = [issue for issue in issues if self._validation_issue_severity(issue) != 'error']
            if not issues:
                self.validationSummaryLabel.setText('✔ No validation issues')
                empty = QtWidgets.QTreeWidgetItem(['', 'No validation issues', ''])
                empty.setFlags(QtCore.Qt.ItemIsEnabled)
                self.validationTree.addTopLevelItem(empty)
                self.validationTree.resizeColumnToContents(0)
                self.validationTree.resizeColumnToContents(2)
                return

            self.validationSummaryLabel.setText(f'{len(errors)} error(s), {len(warnings)} warning(s)')
            groups = [('Errors', errors, '❌'), ('Warnings', warnings, '⚠')]
            for group_name, group_issues, icon in groups:
                if not group_issues:
                    continue
                group = QtWidgets.QTreeWidgetItem([icon, f'{group_name} ({len(group_issues)})', ''])
                group.setFlags(QtCore.Qt.ItemIsEnabled)
                self.validationTree.addTopLevelItem(group)
                for issue in group_issues:
                    try:
                        issue_index = next(index for index, candidate in enumerate(issues) if candidate is issue)
                    except StopIteration:
                        issue_index = issues.index(issue)
                    severity = self._validation_issue_severity(issue)
                    code = str(getattr(issue, 'code', '') or '')
                    label = self._validation_issue_title(issue)
                    item = QtWidgets.QTreeWidgetItem([icon if severity == 'error' else '⚠', label, code])
                    item.setData(0, QtCore.Qt.UserRole, issue_index)
                    item.setToolTip(1, label)
                    if code:
                        item.setToolTip(2, code)
                    group.addChild(item)
                group.setExpanded(True)
            self.validationTree.resizeColumnToContents(0)
            self.validationTree.resizeColumnToContents(2)
        finally:
            self._validation_panel_updating = False

    def _refresh_validation_button_state(self):
        button = getattr(self, '_validationButton', None)
        if button is None:
            return
        issues = list(getattr(self, 'validation_issues', []) or [])
        error_count = sum(1 for issue in issues if self._validation_issue_severity(issue) == 'error')
        warning_count = len(issues) - error_count
        if error_count:
            button.setText(f'Validation ({error_count}E)')
            button.setToolTip(f'{error_count} validation error(s), {warning_count} warning(s). Click to review.')
        elif warning_count:
            button.setText(f'Validation ({warning_count}W)')
            button.setToolTip(f'{warning_count} validation warning(s). Click to review.')
        else:
            button.setText('Validation')
            button.setToolTip('No validation issues. Click to open the validation panel.')

    def _issue_for_tree_item(self, item):
        if item is None:
            return None
        issue_index = item.data(0, QtCore.Qt.UserRole)
        if issue_index is None:
            return None
        issues = list(getattr(self, 'validation_issues', []) or [])
        try:
            index = int(issue_index)
        except Exception:
            return None
        if 0 <= index < len(issues):
            return issues[index]
        return None

    def _validation_issue_graph_items(self, issue):
        items = []
        for node in getattr(issue, 'nodes', []) or []:
            if node is not None and hasattr(node, 'sceneBoundingRect') and node.isVisible():
                items.append(node)
        for connection in getattr(issue, 'connections', []) or []:
            if connection is not None and hasattr(connection, 'sceneBoundingRect') and connection.isVisible():
                items.append(connection)
        return items

    def focus_validation_issue(self, issue):
        items = self._validation_issue_graph_items(issue)
        if not items:
            self._status_message('Validation issue has no visible graph item to focus.', 3000)
            return False
        self.scene.clearSelection()
        for item in items:
            try:
                item.setSelected(True)
            except Exception:
                pass
        if hasattr(self.graphView, 'frame_items'):
            self.graphView.frame_items(items)
        else:
            rect = QtCore.QRectF()
            for item in items:
                rect = rect.united(item.sceneBoundingRect())
            if rect.isValid() and not rect.isNull():
                self.graphView.centerOn(rect.center())
        self._status_message(self._validation_issue_title(issue), 4500)
        return True

    def focus_selected_validation_issue(self):
        if not hasattr(self, 'validationTree'):
            return False
        issue = self._issue_for_tree_item(self.validationTree.currentItem())
        if issue is None:
            return False
        return self.focus_validation_issue(issue)

    def _on_validation_tree_item_clicked(self, item, column):
        issue = self._issue_for_tree_item(item)
        if issue is not None:
            self.focus_validation_issue(issue)

    def _on_validation_tree_item_activated(self, item, column):
        issue = self._issue_for_tree_item(item)
        if issue is not None:
            self.focus_validation_issue(issue)

    def _show_validation_tree_context_menu(self, pos):
        if not hasattr(self, 'validationTree'):
            return
        item = self.validationTree.itemAt(pos)
        issue = self._issue_for_tree_item(item)
        menu = QtWidgets.QMenu(self.validationTree)
        focus_action = menu.addAction('Focus Issue')
        focus_action.setEnabled(issue is not None)
        refresh_action = menu.addAction('Refresh Validation')
        chosen = menu.exec_(self.validationTree.viewport().mapToGlobal(pos))
        if chosen is focus_action and issue is not None:
            self.focus_validation_issue(issue)
        elif chosen is refresh_action:
            self.run_graph_validation()

    def show_validation_panel(self):
        self.run_graph_validation()
        if hasattr(self, 'dockValidation') and self.dockValidation is not None:
            self.dockValidation.show()
            self.dockValidation.raise_()
            self.dockValidation.activateWindow()
        return True

    def _property_dock_current_width(self):
        if not hasattr(self, 'dockProperties') or self.dockProperties is None:
            return int(getattr(self, '_properties_default_width', 300))
        width = int(self.dockProperties.width() or 0)
        if width <= 0:
            width = int(getattr(self, '_properties_default_width', 300))
        return max(40, width)

    def _begin_properties_dock_width_lock(self, width=None):
        """Temporarily freeze dock width while rebuilding property content.

        Child widgets in the property panel can change size hints when switching
        nodes. If Qt resizes the dock during the same mouse event that selected
        a node, the graph viewport shifts under the cursor and a click can be
        misinterpreted as a drag. Freeze only for the rebuild, then release so
        the user can still resize the panel manually.
        """
        if not hasattr(self, 'dockProperties') or self.dockProperties is None:
            return None
        width = max(40, int(width or self._property_dock_current_width()))
        state = (self.dockProperties.minimumWidth(), self.dockProperties.maximumWidth())
        self.dockProperties.setMinimumWidth(width)
        self.dockProperties.setMaximumWidth(width)
        return state

    def _end_properties_dock_width_lock(self, state, width=None):
        if not hasattr(self, 'dockProperties') or self.dockProperties is None:
            return
        target_width = max(40, int(width or self._property_dock_current_width()))
        if state is not None:
            old_min, old_max = state
            self.dockProperties.setMinimumWidth(max(40, int(old_min or 40)))
            self.dockProperties.setMaximumWidth(int(old_max or 16777215))
        else:
            self.dockProperties.setMinimumWidth(40)
            self.dockProperties.setMaximumWidth(16777215)
        if self.dockProperties.isVisible():
            self.resizeDocks([self.dockProperties], [target_width], QtCore.Qt.Horizontal)
        else:
            self.dockProperties.resize(px(target_width), px(self.dockProperties.height()))

    def _stabilize_properties_dock_width(self, previous_width=None):
        """Preserve the current/user dock width across selection changes.

        The default width is used only for first opening. After that, node
        selection must not shrink or expand the dock. Users may still manually
        resize wider or narrower, including below the default width.
        """
        if not hasattr(self, 'dockProperties') or self.dockProperties is None:
            return
        if previous_width is None or previous_width <= 0:
            previous_width = self._property_dock_current_width()
        target_width = max(40, int(previous_width))
        if not self.dockProperties.isVisible():
            self.dockProperties.resize(px(target_width), px(self.dockProperties.height()))
            return
        self.resizeDocks([self.dockProperties], [target_width], QtCore.Qt.Horizontal)

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
                editor.textChanged.connect(lambda name=prop_name, w=editor: self.on_dynamic_property_changed(name, w.toPlainText(), defer_refresh=True))
            else:
                editor.textEdited.connect(lambda value, name=prop_name: self.on_dynamic_property_changed(name, value, defer_refresh=True))
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
        self.refresh_message_schema_editor(node_item)
        self.refresh_dynamic_ports_editor(node_item)

    DYNAMIC_PORT_DATA_TYPES = ['str', 'int', 'float', 'bool', 'bytes', 'complex', 'list', 'tuple', 'dict', 'set', 'NoneType']

    def _node_allows_dynamic_ports(self, node_item):
        
        if node_item is None:
            return False
        definition = getattr(node_item, 'definition', None)
        metadata = getattr(definition, 'metadata', {}) or {}
        return bool(metadata.get('allow_dynamic_ports'))

    def _node_allows_independent_paired_port_types(self, node_item):
        if node_item is None:
            return False
        definition = getattr(node_item, 'definition', None)
        metadata = getattr(definition, 'metadata', {}) or {}
        if metadata.get('independent_paired_port_types'):
            return True
        return False

    def _dynamic_port_specs(self, node_item=None):
        node_item = node_item or self.selected_node_item
        if node_item is None:
            return []
        props = node_item.node_data.properties if isinstance(node_item.node_data.properties, dict) else {}
        specs = props.setdefault('__dynamic_ports', [])
        if not isinstance(specs, list):
            specs = []
            props['__dynamic_ports'] = specs
        return specs

    def _node_is_linked_subgraph_reference(self, node_item):
        if node_item is None:
            return False
        props = getattr(getattr(node_item, 'node_data', None), 'properties', {}) or {}
        mode = str(props.get('subgraph_source') or props.get('subgraph_mode') or 'embedded').strip().lower()
        return mode == 'linked' and bool(self.linked_graph_policy_for_node(node_item))

    def _static_port_names(self, node_item, direction):
        definition = getattr(node_item, 'definition', None)
        if definition is None:
            return []
        ports = definition.inputs if direction == 'input' else definition.outputs
        return [p.name for p in ports]

    def _unique_dynamic_port_name(self, node_item, base='Data'):
        existing = set(node_item.input_names) | set(node_item.output_names)
        candidate = base
        index = 1
        while candidate in existing:
            index += 1
            candidate = f"{base} {index}"
        return candidate

    def refresh_dynamic_ports_editor(self, node_item):
        if not hasattr(self, 'dynamicPortsGroup'):
            return
        allow = self._node_allows_dynamic_ports(node_item)
        self.dynamicPortsGroup.setVisible(allow)
        if not allow:
            return
        linked_read_only = self._node_is_linked_subgraph_reference(node_item)
        self.btnAddInputPort.setEnabled(not linked_read_only)
        self.btnAddOutputPort.setEnabled(not linked_read_only)
        self.btnRemoveDynamicPort.setEnabled(not linked_read_only)
        self.dynamicPortsTable.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers if linked_read_only
            else (QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed | QtWidgets.QAbstractItemView.SelectedClicked)
        )
        specs = self._dynamic_port_specs(node_item)
        self._dynamic_ports_updating = True
        self.dynamicPortsTable.blockSignals(True)
        try:
            self.dynamicPortsTable.setRowCount(len(specs))
            for row, spec in enumerate(specs):
                direction_item = QtWidgets.QTableWidgetItem('Input' if spec.get('direction') == 'input' else 'Output')
                direction_item.setFlags(direction_item.flags() & ~QtCore.Qt.ItemIsEditable)
                name_item = QtWidgets.QTableWidgetItem(str(spec.get('name') or 'Data'))
                type_combo = QtWidgets.QComboBox(self.dynamicPortsTable)
                type_combo.addItems(self.DYNAMIC_PORT_DATA_TYPES)
                current_type = self._normal_dynamic_data_type(spec.get('data_type') or 'str')
                combo_index = type_combo.findText(current_type)
                type_combo.setCurrentIndex(max(combo_index, 0))
                type_combo.setProperty('dynamic_port_id', spec.get('id'))
                type_combo.setEnabled(not linked_read_only)
                type_combo.currentTextChanged.connect(lambda value, combo=type_combo: self.on_dynamic_port_type_combo_changed(combo.property('dynamic_port_id'), value))
                pair_item = QtWidgets.QTableWidgetItem(str(spec.get('pair_id') or ''))
                pair_item.setFlags(pair_item.flags() & ~QtCore.Qt.ItemIsEditable)
                for cell in (direction_item, name_item, pair_item):
                    cell.setData(QtCore.Qt.UserRole, spec.get('id'))
                self.dynamicPortsTable.setItem(row, 0, direction_item)
                self.dynamicPortsTable.setItem(row, 1, name_item)
                self.dynamicPortsTable.setCellWidget(row, 2, type_combo)
                self.dynamicPortsTable.setItem(row, 3, pair_item)
        finally:
            self.dynamicPortsTable.blockSignals(False)
            self._dynamic_ports_updating = False
        self.dynamicPortsTable.resizeColumnsToContents()

    def _connection_endpoints_for_node_rebuild(self, node_item):
        """Capture connections before a dynamic port rebuild.

        Editing data-port metadata rebuilds PortItem instances. Preserve any
        unchanged compatible connections so static execution wires are not
        destroyed by a data-port edit.
        """
        captured = []
        if node_item is None:
            return captured
        seen = set()
        for port in list(getattr(node_item, 'inputs', []) or []) + list(getattr(node_item, 'outputs', []) or []):
            for conn in list(getattr(port, 'connections', []) or []):
                if id(conn) in seen:
                    continue
                seen.add(id(conn))
                data_obj = conn.connection_data() if hasattr(conn, 'connection_data') else None
                if data_obj is not None:
                    captured.append(data_obj.to_dict())
        return captured

    def _restore_connections_after_node_rebuild(self, captured):
        if not captured or not hasattr(self, 'scene') or self.scene is None:
            return
        for data in captured:
            try:
                source_node = self.scene.find_node_by_id(data.get('source_node_id'))
                target_node = self.scene.find_node_by_id(data.get('target_node_id'))
                if source_node is None or target_node is None:
                    continue
                source_port = self.scene.find_output_port(source_node, data.get('source_port_name'))
                target_port = self.scene.find_input_port(target_node, data.get('target_port_name'))
                if source_port is None or target_port is None:
                    continue
                kind = self._connection_kind_for_ports(source_port, target_port)
                if not kind:
                    continue
                data['connection_kind'] = kind
                allowed, _reason = self._check_connection_view_rules(source_port, target_port)
                if not allowed:
                    continue
                if self.scene.find_connection(data, ignore_route_points=True) is not None:
                    continue
                self.scene.add_connection_from_dict(data)
            except Exception:
                continue

    def _sync_dynamic_ports_to_node(self, node_item):
        if node_item is None:
            return
        if getattr(self, '_syncing_dynamic_ports', False):
            return
        self._syncing_dynamic_ports = True
        try:
            captured_connections = self._connection_endpoints_for_node_rebuild(node_item)
            static_inputs = self._static_port_names(node_item, 'input')
            static_outputs = self._static_port_names(node_item, 'output')
            specs = self._dynamic_port_specs(node_item)
            dynamic_inputs = [str(spec.get('name') or 'Data') for spec in specs if spec.get('direction') == 'input']
            dynamic_outputs = [str(spec.get('name') or 'Data') for spec in specs if spec.get('direction') == 'output']
            node_item.rebuild_ports(inputs=static_inputs + dynamic_inputs, outputs=static_outputs + dynamic_outputs)
            self._restore_connections_after_node_rebuild(captured_connections)
            if hasattr(self, 'scene') and self.scene is not None:
                self.scene.update()
        finally:
            self._syncing_dynamic_ports = False

    def _new_dynamic_port_spec(self, direction, name, data_type='str', pair_id=''):
        return {'id': str(uuid.uuid4()), 'direction': direction, 'name': name, 'data_type': data_type, 'connection_kind': 'data', 'pair_id': pair_id or ''}

    def add_dynamic_input_pair(self):
        node_item = self.selected_node_item
        if not self._node_allows_dynamic_ports(node_item) or self._node_is_linked_subgraph_reference(node_item):
            if self._node_is_linked_subgraph_reference(node_item):
                self._status_message("Linked subgraph port names are read-only. Open the linked graph file to edit ports.", 4500)
            return
        name = self._unique_dynamic_port_name(node_item, 'Data')
        pair_id = str(uuid.uuid4())
        specs = self._dynamic_port_specs(node_item)
        specs.append(self._new_dynamic_port_spec('input', name, 'str', pair_id))
        specs.append(self._new_dynamic_port_spec('output', name, 'str', pair_id))
        self._sync_dynamic_ports_to_node(node_item)
        self.refresh_dynamic_ports_editor(node_item)
        self.on_node_mutated(node_item)

    def add_dynamic_output_port(self):
        node_item = self.selected_node_item
        if not self._node_allows_dynamic_ports(node_item) or self._node_is_linked_subgraph_reference(node_item):
            if self._node_is_linked_subgraph_reference(node_item):
                self._status_message("Linked subgraph port names are read-only. Open the linked graph file to edit ports.", 4500)
            return
        name = self._unique_dynamic_port_name(node_item, 'Data Out')
        specs = self._dynamic_port_specs(node_item)
        specs.append(self._new_dynamic_port_spec('output', name, 'str', ''))
        self._sync_dynamic_ports_to_node(node_item)
        self.refresh_dynamic_ports_editor(node_item)
        self.on_node_mutated(node_item)

    def _find_dynamic_port_index_by_id(self, specs, port_id):
        for idx, spec in enumerate(specs):
            if spec.get('id') == port_id:
                return idx
        return -1

    def remove_selected_dynamic_port(self):
        node_item = self.selected_node_item
        if not self._node_allows_dynamic_ports(node_item) or self._node_is_linked_subgraph_reference(node_item):
            if self._node_is_linked_subgraph_reference(node_item):
                self._status_message("Linked subgraph port names are read-only. Open the linked graph file to edit ports.", 4500)
            return
        row = self.dynamicPortsTable.currentRow()
        if row < 0:
            return
        item = self.dynamicPortsTable.item(row, 0)
        port_id = item.data(QtCore.Qt.UserRole) if item is not None else None
        specs = self._dynamic_port_specs(node_item)
        idx = self._find_dynamic_port_index_by_id(specs, port_id)
        if idx < 0:
            return
        pair_id = specs[idx].get('pair_id') or ''
        if pair_id:
            specs[:] = [p for p in specs if p.get('pair_id') != pair_id]
        else:
            specs.pop(idx)
        self._sync_dynamic_ports_to_node(node_item)
        self.refresh_dynamic_ports_editor(node_item)
        self.on_node_mutated(node_item)

    def _normal_dynamic_data_type(self, value):
        value = str(value or 'str').strip()
        aliases = {'string': 'str', 'boolean': 'bool', 'none': 'NoneType', 'object': 'complex'}
        value = aliases.get(value.lower(), value)
        return value if value in self.DYNAMIC_PORT_DATA_TYPES else 'complex'

    def on_dynamic_port_type_combo_changed(self, port_id, value):
        if self._dynamic_ports_updating or self.selected_node_item is None:
            return
        node_item = self.selected_node_item
        if self._node_is_linked_subgraph_reference(node_item):
            self._status_message("Linked subgraph port names are read-only. Open the linked graph file to edit ports.", 4500)
            self.refresh_dynamic_ports_editor(node_item)
            return
        specs = self._dynamic_port_specs(node_item)
        idx = self._find_dynamic_port_index_by_id(specs, port_id)
        if idx < 0:
            return
        spec = specs[idx]
        pair_id = spec.get('pair_id') or ''
        new_value = self._normal_dynamic_data_type(value)
        if pair_id and not self._node_allows_independent_paired_port_types(node_item):
            for other in specs:
                if other.get('pair_id') == pair_id:
                    other['data_type'] = new_value
        else:
            # Some domain nodes can model transformations/sources, so paired input/output
            # names stay linked while their data types may intentionally differ.
            spec['data_type'] = new_value
        self._sync_dynamic_ports_to_node(node_item)
        self._remove_invalid_connections_for_node(node_item)
        self.refresh_dynamic_ports_editor(node_item)
        self.on_node_mutated(node_item)

    def on_dynamic_port_table_item_changed(self, item):
        if self._dynamic_ports_updating or self.selected_node_item is None or item is None or item.column() != 1:
            return
        node_item = self.selected_node_item
        if self._node_is_linked_subgraph_reference(node_item):
            self._status_message("Linked subgraph port names are read-only. Open the linked graph file to edit ports.", 4500)
            self.refresh_dynamic_ports_editor(node_item)
            return
        specs = self._dynamic_port_specs(node_item)
        port_id = item.data(QtCore.Qt.UserRole)
        idx = self._find_dynamic_port_index_by_id(specs, port_id)
        if idx < 0:
            return
        spec = specs[idx]
        pair_id = spec.get('pair_id') or ''
        if item.column() == 1:
            new_value = str(item.text() or '').strip() or 'Data'
            used = set(self._static_port_names(node_item, 'input')) | set(self._static_port_names(node_item, 'output'))
            for other in specs:
                if other is not spec and other.get('pair_id') != pair_id:
                    used.add(other.get('name'))
            base = new_value
            suffix = 1
            while new_value in used:
                suffix += 1
                new_value = f"{base} {suffix}"
            if pair_id:
                for other in specs:
                    if other.get('pair_id') == pair_id:
                        other['name'] = new_value
            else:
                spec['name'] = new_value
        self._sync_dynamic_ports_to_node(node_item)
        self.refresh_dynamic_ports_editor(node_item)
        self.on_node_mutated(node_item)

    def refresh_subgraph_source_editor(self, node_item):
        if not hasattr(self, 'subgraphSourceGroup'):
            return
        policy = self.linked_graph_policy_for_node(node_item)
        allow = bool(policy)
        self.subgraphSourceGroup.setVisible(allow)
        if not allow or node_item is None:
            return
        props = node_item.node_data.properties
        mode = str(props.get('subgraph_source') or props.get('subgraph_mode') or 'embedded').lower()
        if mode not in {'embedded', 'linked'}:
            mode = 'embedded'
        path = props.get('linked_graph_path') or ''
        self._subgraph_source_updating = True
        try:
            self.radioEmbeddedSubgraph.setChecked(mode != 'linked')
            self.radioLinkedSubgraph.setChecked(mode == 'linked')
            self.editLinkedGraphPath.setText(path)
            self.editLinkedGraphPath.setEnabled(mode == 'linked')
            self.btnBrowseLinkedGraph.setEnabled(mode == 'linked')
            self.btnClearLinkedGraph.setEnabled(bool(path))
            label = str(policy.get('label') or 'linked graph')
            ext = str(policy.get('extension') or '')
            if ext and not ext.startswith('.'):
                ext = '.' + ext
            self.linkedGraphHint.setText(f"Select an existing {label} file ({ext}). Linked graphs are reference-only; open the graph file directly to edit it.")
        finally:
            self._subgraph_source_updating = False

    def on_subgraph_source_mode_changed(self, *_args):
        if getattr(self, '_subgraph_source_updating', False):
            return
        node_item = self.selected_node_item
        if not self.linked_graph_policy_for_node(node_item):
            return
        props = node_item.node_data.properties
        props['subgraph_source'] = 'linked' if self.radioLinkedSubgraph.isChecked() else 'embedded'
        self.refresh_subgraph_source_editor(node_item)
        self.on_node_mutated(node_item)

    def browse_linked_graph_for_selected_node(self):
        node_item = self.selected_node_item
        policy = self.linked_graph_policy_for_node(node_item)
        if not policy:
            return
        file_filter = policy.get('file_filter') or self.graph_file_filter_for_view_id(policy.get('expected_view_id'))
        file_path, _selected = QtWidgets.QFileDialog.getOpenFileName(self, "Link Existing Graph", "", file_filter)
        if not file_path:
            return
        ok, _reason = self._validate_linked_graph_for_policy(file_path, policy, show_feedback=True)
        if not ok:
            return
        props = node_item.node_data.properties
        props['subgraph_source'] = 'linked'
        props['linked_graph_path'] = self._linked_graph_path_for_storage(file_path)
        self.refresh_subgraph_source_editor(node_item)
        self.on_node_mutated(node_item)
        self._status_message(f"Linked graph: {file_path}", 4000)

    def clear_linked_graph_for_selected_node(self):
        node_item = self.selected_node_item
        if not self.linked_graph_policy_for_node(node_item):
            return
        props = node_item.node_data.properties
        props.pop('linked_graph_path', None)
        props['subgraph_source'] = 'embedded'
        self.refresh_subgraph_source_editor(node_item)
        self.on_node_mutated(node_item)

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
        if hasattr(self.tableWidget, "_table_snapshot"):
            self.tableWidget._last_table_snapshot = self.tableWidget._table_snapshot()
        self.tableWidget.viewport().update()
        self.tableWidget.update()

    def on_dynamic_property_changed(self, prop_name, value, defer_refresh=False):
        if self._updating_property_panel or self.selected_node_item is None:
            return
        self.selected_node_item.node_data.properties[prop_name] = value
        if prop_name in ("icd", "message_type", "topic"):
            self.refresh_stat_message_editor(self.selected_node_item)
        if defer_refresh:
            # Text editors emit changes on every character. Rebuilding the full
            # property panel here destroys/recreates the active editor and makes
            # the user lose focus after one keystroke. Persist the value and
            # publish the updated selection payload without refreshing editors.
            self.on_node_mutated(self.selected_node_item, refresh_properties=False)
            return
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
        if getattr(self, '_syncing_table_ports', False):
            return
        self._syncing_table_ports = True
        try:
            captured_connections = self._connection_endpoints_for_node_rebuild(node_item)
            existing_columns = list(node_item.node_data.properties.get("columns", []))
            column_types = {str(col.get('name')): col.get('type', 'string') for col in existing_columns if isinstance(col, dict)}
            output_names = self._table_column_names(node_item)
            node_item.rebuild_ports(inputs=[], outputs=output_names)
            # Preserve existing type metadata. Do not drop rows/default data here;
            # this method is only responsible for keeping visual output ports in
            # sync with column definitions.
            node_item.node_data.properties["columns"] = [
                {"name": name, "type": column_types.get(name, "string")} for name in output_names
            ]
            self._restore_connections_after_node_rebuild(captured_connections)
            node_item.update()
            if hasattr(self, "scene") and self.scene is not None:
                self.scene.update()
        finally:
            self._syncing_table_ports = False

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
        # Keep the lightweight item path for direct edits; paste/structure edits
        # are reconciled by the table-level signals below.
        columns = self.selected_node_item.node_data.properties.get("columns", [])
        rows = self.selected_node_item.node_data.properties.setdefault("rows", [])
        row_index = item.row()
        column_index = item.column()
        if row_index < 0 or column_index < 0:
            return
        while column_index >= len(columns):
            columns.append({"name": f"Column {len(columns) + 1}", "type": "string"})
        while row_index >= len(rows):
            rows.append({})
        column_name = columns[column_index].get("name", f"column_{column_index + 1}")
        rows[row_index][column_name] = item.text()

    def _sync_table_node_from_widget(self, *, sync_ports=False):
        if self._table_editor_updating or self._updating_property_panel or self.selected_node_item is None:
            return
        if self.selected_node_item.node_data.node_type != "table.table_data":
            return
        headers = []
        seen = set()
        for column_index in range(self.tableWidget.columnCount()):
            item = self.tableWidget.horizontalHeaderItem(column_index)
            base = str(item.text() if item else f"Column {column_index + 1}").strip() or f"Column {column_index + 1}"
            name = base
            suffix = 2
            while name in seen:
                name = f"{base}_{suffix}"
                suffix += 1
            seen.add(name)
            headers.append(name)

        existing_columns = self.selected_node_item.node_data.properties.get("columns", [])
        type_by_name = {str(col.get("name")): col.get("type", "string") for col in existing_columns if isinstance(col, dict)}
        self.selected_node_item.node_data.properties["columns"] = [
            {"name": name, "type": type_by_name.get(name, "string")} for name in headers
        ]

        rows = []
        for row_index in range(self.tableWidget.rowCount()):
            row_data = {}
            for column_index, column_name in enumerate(headers):
                item = self.tableWidget.item(row_index, column_index)
                row_data[column_name] = item.text() if item else ""
            rows.append(row_data)
        self.selected_node_item.node_data.properties["rows"] = rows

        if sync_ports:
            self._sync_table_node_ports(self.selected_node_item)
        self.on_node_mutated(self.selected_node_item, refresh_properties=False)

    def on_table_widget_data_changed(self):
        self._sync_table_node_from_widget(sync_ports=False)

    def on_table_widget_structure_changed(self):
        self._sync_table_node_from_widget(sync_ports=True)

    def on_table_widget_column_renamed(self, column_index, old_name, new_name):
        # NexusTableEditor has already updated the header. Reconcile the graph
        # node schema and output ports from the table widget as source of truth.
        self._sync_table_node_from_widget(sync_ports=True)



    def table_editor_policy(self):
        return {
            'show_rename_button': True,
            'enable_sorting': True,
            'enable_filtering': True,
        }

    def message_schema_catalog_for_node(self, node_item):
        return {}

    def _node_uses_message_schema_editor(self, node_item):
        definition = getattr(node_item, "definition", None)
        metadata = getattr(definition, "metadata", {}) or {}
        return bool(metadata.get("message_schema_editor"))

    def _message_schema_tree_mode(self, node_item):
        definition = getattr(node_item, "definition", None)
        metadata = getattr(definition, "metadata", {}) or {}
        return str(metadata.get("message_schema_mode") or "expect")

    def _message_schema_selected_fields(self, node_item):
        raw = (node_item.node_data.properties or {}).get("field_selections", {})
        if isinstance(raw, dict):
            return raw
        try:
            return json.loads(raw or "{}")
        except Exception:
            return {}

    def _save_message_schema_selected_fields(self, node_item, selections):
        node_item.node_data.properties["field_selections"] = json.dumps(selections or {}, indent=2, sort_keys=True)
        editor_tuple = getattr(self, "_property_editors", {}).get("field_selections")
        if editor_tuple:
            prop_def, editor = editor_tuple
            self._set_editor_value(editor, prop_def, node_item.node_data.properties["field_selections"])

    def refresh_message_schema_editor(self, node_item):
        if not hasattr(self, "messageSchemaGroup"):
            return
        enabled = self._node_uses_message_schema_editor(node_item)
        self.messageSchemaGroup.setVisible(enabled)
        self.messageSchemaTree.clear()
        if not enabled:
            return
        message_type = str((node_item.node_data.properties or {}).get("message_type") or "RedundancyStatus")
        schema = self.message_schema_catalog_for_node(node_item).get(message_type) or {}
        mode = self._message_schema_tree_mode(node_item)
        self.messageSchemaHint.setText(
            "Set mode: check primitive fields and enter values to be assigned."
            if mode == "set" else
            "Expect mode: check primitive fields to verify later."
        )
        selections = self._message_schema_selected_fields(node_item)
        self._message_schema_tree_updating = True
        try:
            root = QtWidgets.QTreeWidgetItem([message_type, "class", ""])
            root.setData(0, QtCore.Qt.UserRole, "")
            root.setFlags(root.flags() | QtCore.Qt.ItemIsEnabled)
            self.messageSchemaTree.addTopLevelItem(root)
            self._populate_message_schema_tree(root, schema, "", selections, mode)
            root.setExpanded(True)
            self.messageSchemaTree.resizeColumnToContents(0)
            self.messageSchemaTree.resizeColumnToContents(1)
        finally:
            self._message_schema_tree_updating = False

    def _populate_message_schema_tree(self, parent_item, schema, prefix, selections, mode):
        if not isinstance(schema, dict):
            return
        for name, value in schema.items():
            path = f"{prefix}.{name}" if prefix else name
            if isinstance(value, dict):
                item = QtWidgets.QTreeWidgetItem([name, "class", ""])
                item.setData(0, QtCore.Qt.UserRole, path)
                parent_item.addChild(item)
                self._populate_message_schema_tree(item, value, path, selections, mode)
            else:
                item = QtWidgets.QTreeWidgetItem([name, str(value), ""])
                item.setData(0, QtCore.Qt.UserRole, path)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
                selected = selections.get(path)
                item.setCheckState(0, QtCore.Qt.Checked if selected is not None else QtCore.Qt.Unchecked)
                if mode == "set":
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                    if isinstance(selected, dict):
                        item.setText(2, str(selected.get("value", "")))
                    elif selected not in (None, True, False):
                        item.setText(2, str(selected))
                parent_item.addChild(item)

    def on_message_schema_tree_item_changed(self, item, column):
        if getattr(self, "_message_schema_tree_updating", False) or self.selected_node_item is None:
            return
        if not self._node_uses_message_schema_editor(self.selected_node_item):
            return
        path = item.data(0, QtCore.Qt.UserRole)
        if not path or item.childCount() > 0:
            return
        mode = self._message_schema_tree_mode(self.selected_node_item)
        selections = self._message_schema_selected_fields(self.selected_node_item)
        if item.checkState(0) == QtCore.Qt.Checked:
            if mode == "set":
                selections[path] = {"path": path, "value": item.text(2), "type": item.text(1)}
            else:
                selections[path] = {"path": path, "type": item.text(1)}
        else:
            selections.pop(path, None)
            if mode == "set":
                item.setText(2, "")
        self._save_message_schema_selected_fields(self.selected_node_item, selections)
        self.on_node_mutated(self.selected_node_item)

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
            self._refresh_node_view_ui()
            return None
        previous_view_id = self._active_node_view_id
        required_only_graph = self._graph_has_nodes() and not self._graph_has_user_nodes()
        view_definition = self._node_view_session.set_active_view_id(view_id)
        self._active_node_view_id = self._node_view_session.active_view_id()
        self._apply_active_node_view_registry()
        if required_only_graph and previous_view_id != self._active_node_view_id:
            self.scene._suspend_undo = True
            try:
                self.scene.load_graph(self._ensure_graph_control_flow_nodes({"nodes": [], "connections": []}))
            finally:
                self.scene._suspend_undo = False
            self.undo_stack.clear()
            self._initial_fit_pending = True
            QtCore.QTimer.singleShot(0, self._ensure_initial_fit)
        else:
            self._ensure_current_graph_control_flow_nodes()
        self._refresh_node_view_ui()
        self.schedule_validation_update()
        self.set_editor_title(self._editor_title)
        if announce:
            label = view_definition.name if view_definition is not None else "Not Selected"
            self._status_message(f"{self.graph_view_label}: %s" % label, 3500)
        return view_definition

    def prompt_select_node_view(self):
        views = self.available_node_views()
        if not views:
            self._status_message(f"{self.graph_view_label}: no views available", 3000)
            return False
        if not self._can_change_node_view(show_feedback=True):
            return False

        labels = [view.name for view in views]
        current_view = self.active_node_view()
        current_name = current_view.name if current_view is not None else labels[0]
        current_index = labels.index(current_name) if current_name in labels else 0

        selected_name, accepted = QtWidgets.QInputDialog.getItem(
            self,
            f"Select {self.graph_view_label}",
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
            self._node_view_session = NodeViewSession(NODE_REGISTRY, NODE_VIEW_REGISTRY, select_default_on_reset=False, allowed_view_ids=self.graph_allowed_node_view_ids, allowed_view_prefixes=self.graph_allowed_node_view_prefixes)
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
            self._status_message(f'{self.graph_tool_label} definitions refreshed.', 1800)
        except Exception as exc:
            self._refresh_definition_watch_paths()
            self._status_message(f'Failed to refresh {self.graph_tool_label} definitions: %s' % exc, 5000)

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


    def _selected_layout_items(self):
        """Return selected objects that participate in manual layout tools.

        Normal nodes are moved directly. Expanded inline subgraphs participate as
        their boundary item, which keeps the read-only internal projection moving
        as one group without making the child nodes editable.
        """
        ordered = []
        if hasattr(self.scene, 'ordered_selected_items'):
            ordered = self.scene.ordered_selected_items()
        else:
            ordered = self.scene.selectedItems()
        items = []
        for item in ordered:
            if isinstance(item, NodeItem):
                if getattr(item, '_inline_subgraph_display', False):
                    continue
                if not bool(item.flags() & QtWidgets.QGraphicsItem.ItemIsMovable):
                    continue
                items.append(item)
            elif isinstance(item, InlineSubgraphBoundaryItem):
                items.append(item)
        return items

    def _layout_item_pos(self, item):
        if isinstance(item, InlineSubgraphBoundaryItem):
            expansion = (getattr(self, '_inline_subgraph_expansions', {}) or {}).get(item.container_node_id)
            container = expansion.get('container_node') if expansion else None
            if container is not None:
                return QtCore.QPointF(container.pos())
        return QtCore.QPointF(item.pos())

    def _push_layout_moves(self, moves, label):
        if not moves:
            return False
        changed = [(item, old_pos, new_pos) for item, old_pos, new_pos in moves if old_pos != new_pos]
        if not changed:
            return False
        self._show_layout_ghost_preview([(item, new_pos) for item, _old, new_pos in changed])
        self.undo_stack.beginMacro(label)
        try:
            for item, old_pos, new_pos in changed:
                if isinstance(item, InlineSubgraphBoundaryItem):
                    self.undo_stack.push(MoveInlineExpansionCommand(self, item.container_node_id, old_pos, new_pos))
                elif isinstance(item, NodeItem):
                    self.undo_stack.push(MoveNodeCommand(item, old_pos, new_pos))
        finally:
            self.undo_stack.endMacro()
        self.scene.update()
        return True

    def _show_layout_ghost_preview(self, targets, duration_ms=550):
        """Briefly show translucent target boxes for manual layout operations."""
        existing = getattr(self, '_layout_ghost_items', []) or []
        for ghost in existing:
            try:
                self.scene.removeItem(ghost)
            except RuntimeError:
                pass
        self._layout_ghost_items = []
        theme = getattr(self.scene, 'theme', {}) or {}
        pen_color = QtGui.QColor(theme.get('node_selected', theme.get('accent', '#6aa9ff')))
        brush_color = QtGui.QColor(pen_color)
        brush_color.setAlpha(42)
        for item, new_pos in targets:
            try:
                rect = QtCore.QRectF(item.sceneBoundingRect())
                old_pos = self._layout_item_pos(item)
                delta = QtCore.QPointF(new_pos - old_pos)
                rect.translate(delta)
            except RuntimeError:
                continue
            ghost = QtWidgets.QGraphicsRectItem(rect)
            ghost.setZValue(5000)
            ghost.setPen(QtGui.QPen(pen_color, 1.6, QtCore.Qt.DashLine))
            ghost.setBrush(QtGui.QBrush(brush_color))
            ghost.setAcceptedMouseButtons(QtCore.Qt.NoButton)
            ghost._layout_ghost_preview = True
            self.scene.addItem(ghost)
            self._layout_ghost_items.append(ghost)
        if self._layout_ghost_items:
            QtCore.QTimer.singleShot(duration_ms, self._clear_layout_ghost_preview)

    def _clear_layout_ghost_preview(self):
        for ghost in list(getattr(self, '_layout_ghost_items', []) or []):
            try:
                self.scene.removeItem(ghost)
            except RuntimeError:
                pass
        self._layout_ghost_items = []

    def _layout_item_rect_at(self, item, new_pos):
        rect = QtCore.QRectF(item.sceneBoundingRect())
        old_pos = self._layout_item_pos(item)
        rect.translate(QtCore.QPointF(new_pos - old_pos))
        return rect

    def _prevent_alignment_overlap(self, items, proposed_positions, alignment, gap=24.0):
        """Keep manual alignment from stacking nodes on top of each other.

        Alignment still locks the requested edge/center to the anchor, but it
        also preserves a readable lane on the perpendicular axis.  This keeps
        the operation surgical and predictable without becoming auto-layout.
        """
        if not items:
            return proposed_positions
        anchor = items[0]
        alignment = str(alignment or '').lower()
        vertical_lane = alignment in ('left', 'right', 'center', 'center_x', 'horizontal_center')
        ordered = sorted(enumerate(items), key=lambda pair: (
            pair[1].sceneBoundingRect().center().y() if vertical_lane else pair[1].sceneBoundingRect().center().x(),
            pair[0],
        ))
        ordered_items = [item for _index, item in ordered]
        if anchor not in ordered_items:
            return proposed_positions
        anchor_index = ordered_items.index(anchor)

        rects = {item: self._layout_item_rect_at(item, proposed_positions[item]) for item in items}

        # Walk forward from the anchor.  Push later items down/right only when
        # the aligned result would overlap the previous item.
        previous = rects[anchor]
        for item in ordered_items[anchor_index + 1:]:
            rect = rects[item]
            if vertical_lane:
                delta = previous.bottom() + gap - rect.top()
                if delta > 0:
                    proposed_positions[item] = QtCore.QPointF(proposed_positions[item].x(), proposed_positions[item].y() + delta)
                    rect.translate(0.0, delta)
            else:
                delta = previous.right() + gap - rect.left()
                if delta > 0:
                    proposed_positions[item] = QtCore.QPointF(proposed_positions[item].x() + delta, proposed_positions[item].y())
                    rect.translate(delta, 0.0)
            rects[item] = rect
            previous = rect

        # Walk backward from the anchor.  Push earlier items up/left only when
        # the aligned result would overlap the next item.
        next_rect = rects[anchor]
        for item in reversed(ordered_items[:anchor_index]):
            rect = rects[item]
            if vertical_lane:
                delta = next_rect.top() - gap - rect.bottom()
                if delta < 0:
                    proposed_positions[item] = QtCore.QPointF(proposed_positions[item].x(), proposed_positions[item].y() + delta)
                    rect.translate(0.0, delta)
            else:
                delta = next_rect.left() - gap - rect.right()
                if delta < 0:
                    proposed_positions[item] = QtCore.QPointF(proposed_positions[item].x() + delta, proposed_positions[item].y())
                    rect.translate(delta, 0.0)
            rects[item] = rect
            next_rect = rect

        return proposed_positions

    def align_selected_nodes(self, alignment):
        items = self._selected_layout_items()
        if len(items) < 2:
            self._status_message('Select at least two movable nodes or expanded sub-graphs to align.', 2500)
            return False
        anchor = items[0]
        alignment = str(alignment or '').lower()
        anchor_rect = anchor.sceneBoundingRect()
        proposed = {anchor: self._layout_item_pos(anchor)}
        for item in items[1:]:
            rect = item.sceneBoundingRect()
            old = self._layout_item_pos(item)
            if alignment == 'left':
                new_pos = QtCore.QPointF(old.x() + (anchor_rect.left() - rect.left()), old.y())
            elif alignment == 'right':
                new_pos = QtCore.QPointF(old.x() + (anchor_rect.right() - rect.right()), old.y())
            elif alignment in ('center', 'center_x', 'horizontal_center'):
                new_pos = QtCore.QPointF(old.x() + (anchor_rect.center().x() - rect.center().x()), old.y())
            elif alignment == 'top':
                new_pos = QtCore.QPointF(old.x(), old.y() + (anchor_rect.top() - rect.top()))
            elif alignment == 'bottom':
                new_pos = QtCore.QPointF(old.x(), old.y() + (anchor_rect.bottom() - rect.bottom()))
            elif alignment in ('middle', 'center_y', 'vertical_center'):
                new_pos = QtCore.QPointF(old.x(), old.y() + (anchor_rect.center().y() - rect.center().y()))
            else:
                return False
            proposed[item] = new_pos

        proposed = self._prevent_alignment_overlap(items, proposed, alignment)
        moves = [(item, self._layout_item_pos(item), proposed[item]) for item in items[1:]]
        changed = self._push_layout_moves(moves, 'Align Layout Items')
        if changed:
            label = getattr(getattr(anchor, 'node_data', None), 'title', None) or getattr(anchor, 'title', 'anchor')
            self._status_message(f'Aligned selected items to anchor without stacking: {label}.', 1800)
        return changed

    def distribute_selected_nodes(self, orientation):
        items = self._selected_layout_items()
        if len(items) < 3:
            self._status_message('Select at least three movable nodes or expanded sub-graphs to distribute.', 2500)
            return False
        orientation = str(orientation or '').lower()
        if orientation == 'horizontal':
            ordered = sorted(items, key=lambda item: item.sceneBoundingRect().center().x())
            centers = [item.sceneBoundingRect().center().x() for item in ordered]
            start, end = centers[0], centers[-1]
            if abs(end - start) < 0.0001:
                return False
            step = (end - start) / float(len(ordered) - 1)
            moves = []
            for index, item in enumerate(ordered):
                rect = item.sceneBoundingRect()
                old = self._layout_item_pos(item)
                target_center = start + step * index
                moves.append((item, old, QtCore.QPointF(old.x() + (target_center - rect.center().x()), old.y())))
        elif orientation == 'vertical':
            ordered = sorted(items, key=lambda item: item.sceneBoundingRect().center().y())
            centers = [item.sceneBoundingRect().center().y() for item in ordered]
            start, end = centers[0], centers[-1]
            if abs(end - start) < 0.0001:
                return False
            step = (end - start) / float(len(ordered) - 1)
            moves = []
            for index, item in enumerate(ordered):
                rect = item.sceneBoundingRect()
                old = self._layout_item_pos(item)
                target_center = start + step * index
                moves.append((item, old, QtCore.QPointF(old.x(), old.y() + (target_center - rect.center().y()))))
        else:
            return False
        changed = self._push_layout_moves(moves, 'Distribute Layout Items')
        if changed:
            self._status_message('Distributed selected layout items.', 1800)
        return changed

    def add_node_from_toolbar(self):
        if self.active_node_view() is None:
            self._centralStack.setCurrentWidget(self._viewSelectionSurface)
            self._status_message(f"Select a {self.graph_view_label} before adding nodes.", 3500)
            self.focus_primary_surface()
            return
        center = self.graphView.mapToScene(self.graphView.viewport().rect().center())
        preferred_type = "action.click_button"
        if not self._node_type_allowed_in_registry(preferred_type):
            definitions = self.active_node_registry().all_definitions()
            if not definitions:
                self._status_message(f"No nodes are available in the active {self.graph_view_label}.", 3500)
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

    def rename_node_via_dialog(self, node_item=None):
        node_item = node_item or self.selected_node_item
        if node_item is None:
            return False
        if getattr(node_item, '_inline_subgraph_display', False):
            self._status_message("Expanded sub-graph previews are read-only. Open the sub-graph to rename nodes.", 3000)
            return False
        old_title = str(getattr(node_item.node_data, 'title', '') or '')
        new_title, ok = QtWidgets.QInputDialog.getText(
            self,
            "Rename Node",
            "Node name:",
            QtWidgets.QLineEdit.Normal,
            old_title,
        )
        new_title = str(new_title or '').strip()
        if not ok or not new_title or new_title == old_title:
            return False
        if not node_item.isSelected():
            self.scene.clearSelection()
            node_item.setSelected(True)
        self.selected_node_item = node_item
        self.undo_stack.push(RenameNodeCommand(node_item, old_title, new_title))
        return True

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
        try:
            return json.dumps(graph_json_safe(snapshot), indent=2)
        except Exception:
            # Copy should fail closed instead of placing a bad payload on the
            # clipboard. Callers treat an empty payload as no-copy.
            return ''

    def copy(self):
        snapshot = self._selected_graph_snapshot()
        if not snapshot:
            return False
        clipboard = QtWidgets.QApplication.clipboard()
        mime = QtCore.QMimeData()
        payload = self._serialize_clipboard_snapshot(snapshot)
        if not payload:
            self._status_message('Copy failed: selected graph data could not be serialized.', 4000)
            return False
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
            self._status_message(f"Skipped nodes blocked by the active {self.graph_view_label}: %s" % ", ".join(blocked_types), 5000)
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
        try:
            return GraphIdRewriter.rewrite_snapshot(snapshot, dx=dx, dy=dy)
        except Exception as exc:
            self._status_message(f'Paste failed while regenerating graph IDs: {exc}', 5000)
            return {'nodes': [], 'connections': []}

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
            self._status_message(f"Skipped nodes blocked by the active {self.graph_view_label}: %s" % ", ".join(blocked_types), 5000)
        if not pasted.get('nodes'):
            return False
        self.undo_stack.push(PasteItemsCommand(self.scene, pasted))
        return True


    # ------------------------------------------------------------------
    # Shared graph templates
    # ------------------------------------------------------------------
    def save_selection_as_template(self):
        snapshot = self._selected_graph_snapshot()
        if not snapshot or not snapshot.get('nodes'):
            self._status_message('Select one or more nodes to save as a template.', 4000)
            return False
        name, ok = QtWidgets.QInputDialog.getText(self, 'Save Graph Template', 'Template name:')
        if not ok:
            return False
        name = str(name or '').strip()
        if not name:
            self._status_message('Template was not saved: name is required.', 4000)
            return False
        try:
            summary = self.template_service.save_template(name, snapshot)
        except Exception as exc:
            self._status_message(f'Template save failed: {exc}', 6000)
            return False
        self._status_message(f'Saved template: {summary.name}', 4000)
        return True


    def configure_template_libraries(self):
        """Configure shared graph template repositories.

        The shared framework owns repository discovery/persistence. Domain
        plugins only constrain compatibility through active graph views and node
        registries.
        """
        service = getattr(self, 'template_service', None)
        if service is None:
            self._status_message('Template service is not available.', 4000)
            return False

        current_save = str(service.save_repository)
        save_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            'Select Template Save Repository',
            current_save,
        )
        if save_dir:
            try:
                service.set_save_repository(save_dir)
            except Exception as exc:
                self._status_message(f'Template repository update failed: {exc}', 6000)
                return False

        current_loads = '\n'.join(str(path) for path in service.load_repositories())
        load_text, ok = QtWidgets.QInputDialog.getMultiLineText(
            self,
            'Template Load Libraries',
            'Template library folders, one path per line:',
            current_loads,
        )
        if ok:
            paths = [line.strip() for line in str(load_text or '').splitlines() if line.strip()]
            try:
                service.set_load_repositories(paths)
            except Exception as exc:
                self._status_message(f'Template library update failed: {exc}', 6000)
                return False
        self._status_message(
            'Template libraries updated. Save: %s | Loaded paths: %d' % (service.save_repository, len(service.load_repositories())),
            5000,
        )
        return True

    def insert_template(self, template_id, scene_pos):
        if not template_id:
            return False
        try:
            snapshot = self.template_service.materialize_template(template_id, scene_pos)
        except Exception as exc:
            self._status_message(f'Template insert failed: {exc}', 6000)
            return False
        snapshot, blocked_types = self._filter_snapshot_to_active_view(snapshot)
        if blocked_types:
            self._status_message(f"Skipped nodes blocked by the active {self.graph_view_label}: %s" % ", ".join(blocked_types), 5000)
        if not snapshot.get('nodes'):
            return False
        self.undo_stack.push(PasteItemsCommand(self.scene, snapshot))
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

        locked_nodes = []
        for item in selected:
            if isinstance(item, NodeItem):
                props = getattr(getattr(item, 'node_data', None), 'properties', {}) or {}
                if props.get('__graph_locked') or props.get('__graph_required'):
                    locked_nodes.append(item)
        if locked_nodes:
            for item in locked_nodes:
                item.setSelected(False)
            self._status_message('Required graph boundary/control nodes cannot be deleted.', 3500)
            selected = self.scene.selectedItems()
            if not selected:
                return False

        snapshot = self.scene.snapshot_items_for_delete(selected)
        if not snapshot["nodes"] and not snapshot["connections"]:
            return False
        self.undo_stack.push(DeleteItemsCommand(self.scene, snapshot))
        return True


    # ------------------------------------------------------------------
    # Shared graph visual path highlighting
    # ------------------------------------------------------------------
    def clear_visual_path_highlighting(self):
        """Clear static authoring path highlights without touching runtime feedback."""
        if hasattr(self.scene, 'clear_path_highlighting'):
            self.scene.clear_path_highlighting()
        else:
            for item in self.scene.items():
                if hasattr(item, 'set_path_highlight_state'):
                    item.set_path_highlight_state('normal')

    def _visible_connection_items(self):
        items = []
        for item in self.scene.items():
            if not isinstance(item, ConnectionItem):
                continue
            if not item.isVisible():
                continue
            if getattr(item, 'preview_mode', False):
                continue
            if getattr(item, 'source_port', None) is None or getattr(item, 'target_port', None) is None:
                continue
            items.append(item)
        return items

    def _node_for_port(self, port):
        return getattr(port, 'parent_node', None) if port is not None else None

    def _apply_node_path_state(self, node, state):
        if node is None or not hasattr(node, 'set_path_highlight_state'):
            return
        current = getattr(node, 'path_highlight_state', 'normal')
        if current == 'path_origin':
            return
        if current == 'path_exec' and state == 'path_data':
            return
        node.set_path_highlight_state(state)

    def apply_visual_path_highlighting(self, origin_node):
        """Highlight static downstream execution flow and connected data flow.

        This is an authoring visualization only.  It does not evaluate node logic,
        mutate graph data, or invoke any domain/runtime behavior.  The shared
        framework uses generic connection kinds: ``exec`` is traversed forward,
        while ``data`` is traced as an undirected dependency network.
        """
        self.clear_visual_path_highlighting()
        if origin_node is None:
            return False
        if hasattr(origin_node, 'set_path_highlight_state'):
            origin_node.set_path_highlight_state('path_origin')

        exec_adjacency = {}
        data_adjacency = {}
        exec_connections = {}
        data_connections = {}

        for conn in self._visible_connection_items():
            source = self._node_for_port(getattr(conn, 'source_port', None))
            target = self._node_for_port(getattr(conn, 'target_port', None))
            if source is None or target is None:
                continue
            kind = str(conn.connection_kind() if hasattr(conn, 'connection_kind') else 'data').lower()
            if kind == 'exec':
                exec_adjacency.setdefault(source, []).append(target)
                exec_connections.setdefault(source, []).append(conn)
            else:
                data_adjacency.setdefault(source, []).append((target, conn))
                data_adjacency.setdefault(target, []).append((source, conn))
                data_connections.setdefault(source, []).append(conn)
                data_connections.setdefault(target, []).append(conn)

        # Execution is directional and should read like program flow.
        visited = set([origin_node])
        stack = list(exec_adjacency.get(origin_node, []))
        for conn in exec_connections.get(origin_node, []):
            conn.set_path_highlight_state('path_exec')
        while stack:
            node = stack.pop(0)
            if node in visited:
                continue
            visited.add(node)
            self._apply_node_path_state(node, 'path_exec')
            for conn in exec_connections.get(node, []):
                conn.set_path_highlight_state('path_exec')
            stack.extend(exec_adjacency.get(node, []))

        # Data is a dependency network, so trace it both upstream and downstream.
        visited_data = set([origin_node])
        stack = list(data_adjacency.get(origin_node, []))
        for conn in data_connections.get(origin_node, []):
            conn.set_path_highlight_state('path_data')
        while stack:
            node, via_conn = stack.pop(0)
            if via_conn is not None:
                via_conn.set_path_highlight_state('path_data')
            if node in visited_data:
                continue
            visited_data.add(node)
            self._apply_node_path_state(node, 'path_data')
            stack.extend(data_adjacency.get(node, []))

        self.scene.update()
        return True

    def on_selection_changed(self):
        items = self.scene.selectedItems()
        node_item = next((item for item in items if isinstance(item, NodeItem)), None)
        self.selected_node_item = node_item

        previous_width = self._property_dock_current_width()
        lock_state = self._begin_properties_dock_width_lock(previous_width)
        try:
            if node_item is None:
                self.clear_property_panel()
            else:
                self.populate_property_panel(node_item)
        finally:
            self._end_properties_dock_width_lock(lock_state, previous_width)
            self._stabilize_properties_dock_width(previous_width=previous_width)

        self._publish_selection_to_data_store(node_item)
        if node_item is None:
            self.clear_visual_path_highlighting()
        else:
            self.apply_visual_path_highlighting(node_item)
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
                'plugin_id': self.graph_plugin_id,
                'node_type': node_data.node_type,
                'definition_category': getattr(definition, 'category', None),
            },
            metadata={
                'source_plugin': self.graph_plugin_id,
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
        try:
            self.labelNodeIdValue.setText(node_item.node_data.node_id)
            self.labelNodeTypeValue.setText(node_item.node_data.node_type)
            self.editNodeTitle.setText(node_item.node_data.title)
            self._property_title_before_edit = node_item.node_data.title
            self.rebuild_dynamic_property_form(node_item)
            self.refresh_subgraph_source_editor(node_item)
            self._sync_dynamic_property_values(node_item)
        finally:
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
        if hasattr(self, 'messageSchemaGroup'):
            self.messageSchemaGroup.hide()
        if hasattr(self, 'dynamicPortsGroup'):
            self.dynamicPortsGroup.hide()
        if hasattr(self, 'subgraphSourceGroup'):
            self.subgraphSourceGroup.hide()
        self._updating_property_panel = False

    def open_properties_for_node(self, node_item):
        if node_item is None:
            return
        first_open = not self.dockProperties.isVisible() if getattr(self, 'dockProperties', None) is not None else True
        previous_width = int(getattr(self, '_properties_default_width', 300)) if first_open else self._property_dock_current_width()
        lock_state = self._begin_properties_dock_width_lock(previous_width)
        try:
            self.selected_node_item = node_item
            self.populate_property_panel(node_item)
            self.dockProperties.show()
        finally:
            self._end_properties_dock_width_lock(lock_state, previous_width)
            self._stabilize_properties_dock_width(previous_width=previous_width)
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


    def _view_id_from_graph_extension(self, graph_data=None, file_path=None):
        """Infer graph view from saved extension metadata or a file path."""
        ext = ""
        metadata = graph_data.get("metadata") if isinstance(graph_data, dict) else None
        if isinstance(metadata, dict):
            ext = str(metadata.get("graph_file_extension") or "").strip()
        if not ext and file_path:
            ext = Path(str(file_path)).suffix
        if not ext:
            return None
        if not ext.startswith("."):
            ext = "." + ext
        ext = ext.lower()
        for view in self.available_node_views():
            view_ext = self.graph_file_extension_for_view_id(view.view_id)
            if view_ext and not view_ext.startswith("."):
                view_ext = "." + view_ext
            if str(view_ext or "").lower() == ext:
                return view.view_id
        return None

    def _node_view_id_for_graph_payload(self, graph_data, file_path=None, fallback_view_id=None):
        """Return the node-view/graph-type that belongs to a graph payload.

        Session restore can occur while the user had an embedded sub-graph open
        at shutdown. In that case the visible/root graph payload and the active
        editor context can disagree. The graph payload is the source of truth.

        Older unsaved session payloads may be missing metadata. For those, infer
        from graph/file extension first, then from node compatibility using the
        tool-specific default before generic/alphabetic view order.
        """
        metadata = graph_data.get("metadata") if isinstance(graph_data, dict) else None
        if isinstance(metadata, dict):
            view_id = metadata.get("active_node_view_id")
            if view_id and self._view_id_allowed_for_tool(view_id):
                registry = self._registry_for_view_id(view_id)
                if not isinstance(graph_data, dict) or not graph_data.get("nodes") or not self._disallowed_node_types_in_graph_data(graph_data, registry=registry):
                    return view_id

        extension_view_id = self._view_id_from_graph_extension(graph_data, file_path=file_path)
        if extension_view_id:
            registry = self._registry_for_view_id(extension_view_id)
            if not isinstance(graph_data, dict) or not graph_data.get("nodes") or not self._disallowed_node_types_in_graph_data(graph_data, registry=registry):
                return extension_view_id

        if isinstance(graph_data, dict) and graph_data.get("nodes"):
            return self._find_compatible_view_id_for_graph_data(graph_data, preferred_view_id=fallback_view_id)
        if fallback_view_id and self._view_id_allowed_for_tool(fallback_view_id):
            return fallback_view_id
        if self._active_node_view_id and self._view_id_allowed_for_tool(self._active_node_view_id):
            return self._active_node_view_id
        return getattr(self, "graph_default_node_view_id", None)

    def save_state(self):
        graph_data = self._save_current_graph_context() if self._graph_context_stack else (self.collapse_all_inline_subgraphs() or self.scene.serialize_graph())
        if self._graph_context_stack and self._root_graph_data is not None:
            graph_data = self._root_graph_data
            root_view_id = None
            if self._graph_context_stack:
                root_view_id = self._graph_context_stack[0].get("parent_view_id")
            metadata = graph_data.setdefault("metadata", {}) if isinstance(graph_data, dict) else {}
            if isinstance(metadata, dict) and root_view_id:
                metadata["active_node_view_id"] = root_view_id
        self._write_bookmark_metadata_to_graph(graph_data)
        active_view_id = self._node_view_id_for_graph_payload(graph_data, file_path=self.current_file_path, fallback_view_id=self._active_node_view_id)
        if isinstance(graph_data, dict) and active_view_id:
            metadata = graph_data.setdefault("metadata", {})
            if isinstance(metadata, dict):
                metadata["active_node_view_id"] = active_view_id
                metadata["graph_file_extension"] = self.graph_file_extension_for_view_id(active_view_id)
        return {
            "editor_title": self.editor_title(),
            "current_file_path": self.current_file_path,
            "properties_visible": self.dockProperties.isVisible(),
            "graph": graph_data,
            "active_node_view_id": active_view_id,
        }

    def load_state(self, state):
        self._graph_context_stack = []
        self._root_graph_data = None
        self._inline_subgraph_expansions = {}
        if not state:
            self._refresh_node_view_ui()
            return
        graph_data = state.get("graph")
        # The restored graph payload is authoritative. The saved active view can
        # be stale when the application was closed from inside a sub-graph.
        active_view_id = self._node_view_id_for_graph_payload(graph_data, file_path=state.get("current_file_path"), fallback_view_id=state.get("active_node_view_id")) if graph_data else state.get("active_node_view_id")
        self.current_file_path = state.get("current_file_path")
        if active_view_id is not None:
            self.set_active_node_view(active_view_id, announce=False, ignore_lock=True)
        elif graph_data and graph_data.get("nodes") and self.available_node_views():
            default_view = self.available_node_views()[0]
            self.set_active_node_view(default_view.view_id, announce=False, ignore_lock=True)
        else:
            self._refresh_node_view_ui()
        if graph_data:
            metadata = graph_data.setdefault("metadata", {}) if isinstance(graph_data, dict) else {}
            if isinstance(metadata, dict) and active_view_id:
                metadata["active_node_view_id"] = active_view_id
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
                    f"{self.graph_view_label} Compatibility",
                    f"This graph contains node types that are not available in the selected {self.graph_view_label}\n\n%s" % "\n".join(disallowed_types),
                )
            self.scene._suspend_undo = True
            try:
                self.scene.load_graph(self._ensure_graph_control_flow_nodes(graph_data))
                self._set_graph_bookmarks_from_payload(graph_data)
            finally:
                self.scene._suspend_undo = False
            if self.active_node_view() is None and graph_data.get("nodes"):
                compatible_view_id = self._node_view_id_for_graph_payload(graph_data, file_path=self.current_file_path, fallback_view_id=active_view_id)
                if compatible_view_id:
                    self.set_active_node_view(compatible_view_id, announce=False, ignore_lock=True)
                    metadata = graph_data.setdefault("metadata", {}) if isinstance(graph_data, dict) else {}
                    if isinstance(metadata, dict):
                        metadata["active_node_view_id"] = compatible_view_id
                        metadata["graph_file_extension"] = self.graph_file_extension_for_view_id(compatible_view_id)
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

    # ------------------------------------------------------------------
    # Graph bookmarks / navigation
    # ------------------------------------------------------------------
    def _bookmark_metadata_from_graph(self, graph_data):
        metadata = graph_data.get("metadata") if isinstance(graph_data, dict) else {}
        bookmarks = metadata.get("bookmarks") if isinstance(metadata, dict) else []
        clean = []
        for entry in bookmarks or []:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "Bookmark").strip() or "Bookmark"
            try:
                rect = entry.get("rect") or {}
                clean.append({
                    "id": str(entry.get("id") or uuid.uuid4()),
                    "name": name,
                    "rect": {
                        "x": float(rect.get("x", entry.get("x", 0.0))),
                        "y": float(rect.get("y", entry.get("y", 0.0))),
                        "width": max(1.0, float(rect.get("width", entry.get("width", 800.0)))),
                        "height": max(1.0, float(rect.get("height", entry.get("height", 500.0)))),
                    },
                    "view_id": str(entry.get("view_id") or metadata.get("active_node_view_id") or self._active_node_view_id or ""),
                })
            except Exception:
                continue
        return clean

    def _write_bookmark_metadata_to_graph(self, graph_data):
        if not isinstance(graph_data, dict):
            return graph_data
        metadata = graph_data.setdefault("metadata", {})
        metadata["bookmarks"] = graph_json_safe(self._graph_bookmarks or [])
        return graph_data

    def _set_graph_bookmarks_from_payload(self, graph_data):
        self._graph_bookmarks = self._bookmark_metadata_from_graph(graph_data or {})
        self._refresh_bookmarks_menu()

    def _selected_or_visible_bookmark_rect(self):
        items = []
        if hasattr(self, '_selected_layout_items'):
            try:
                items = list(self._selected_layout_items() or [])
            except Exception:
                items = []
        if items:
            rect = QtCore.QRectF()
            for item in items:
                item_rect = item.sceneBoundingRect()
                rect = item_rect if rect.isNull() else rect.united(item_rect)
            return rect.adjusted(-80.0, -80.0, 80.0, 80.0)
        viewport_rect = self.graphView.viewport().rect()
        return self.graphView.mapToScene(viewport_rect).boundingRect()

    def add_graph_bookmark(self):
        rect = self._selected_or_visible_bookmark_rect()
        default_name = "Bookmark %d" % (len(self._graph_bookmarks) + 1)
        name, ok = QtWidgets.QInputDialog.getText(self, "Add Graph Bookmark", "Bookmark name:", text=default_name)
        if not ok:
            return False
        name = str(name or "").strip()
        if not name:
            self._status_message("Bookmark was not added: name is required.", 3500)
            return False
        self._graph_bookmarks.append({
            "id": str(uuid.uuid4()),
            "name": name,
            "rect": {
                "x": float(rect.x()),
                "y": float(rect.y()),
                "width": float(max(1.0, rect.width())),
                "height": float(max(1.0, rect.height())),
            },
            "view_id": str(self._active_node_view_id or ""),
        })
        self._refresh_bookmarks_menu()
        self._status_message("Added bookmark: %s" % name, 3500)
        return True

    def jump_to_graph_bookmark(self, bookmark_id):
        bookmark = next((b for b in self._graph_bookmarks if b.get("id") == bookmark_id), None)
        if not bookmark:
            self._status_message("Bookmark no longer exists.", 3000)
            return False
        rect_data = bookmark.get("rect") or {}
        rect = QtCore.QRectF(
            float(rect_data.get("x", 0.0)),
            float(rect_data.get("y", 0.0)),
            float(max(1.0, rect_data.get("width", 800.0))),
            float(max(1.0, rect_data.get("height", 500.0))),
        )
        self.graphView.fitInView(rect, QtCore.Qt.KeepAspectRatio)
        self._status_message("Jumped to bookmark: %s" % bookmark.get("name", "Bookmark"), 2500)
        return True

    def remove_graph_bookmark(self, bookmark_id):
        before = len(self._graph_bookmarks)
        self._graph_bookmarks = [b for b in self._graph_bookmarks if b.get("id") != bookmark_id]
        if len(self._graph_bookmarks) != before:
            self._refresh_bookmarks_menu()
            self._status_message("Removed bookmark.", 2500)
            return True
        return False

    def _refresh_bookmarks_menu(self):
        button = getattr(self, '_bookmarksButton', None)
        if button is None:
            return
        menu = QtWidgets.QMenu(button)
        if not self._graph_bookmarks:
            empty = menu.addAction("No bookmarks yet")
            empty.setEnabled(False)
        else:
            for bookmark in self._graph_bookmarks:
                bookmark_id = bookmark.get("id")
                name = bookmark.get("name") or "Bookmark"
                action = menu.addAction(name)
                action.triggered.connect(lambda _checked=False, bid=bookmark_id: self.jump_to_graph_bookmark(bid))
            menu.addSeparator()
            remove_menu = menu.addMenu("Remove Bookmark")
            for bookmark in self._graph_bookmarks:
                bookmark_id = bookmark.get("id")
                name = bookmark.get("name") or "Bookmark"
                action = remove_menu.addAction(name)
                action.triggered.connect(lambda _checked=False, bid=bookmark_id: self.remove_graph_bookmark(bid))
        button.setMenu(menu)

    def _status_message(self, message, timeout=5000):
        window = self.window()
        if hasattr(window, "statusbar"):
            window.statusbar.showMessage(message, timeout)

    def _current_context_file_path(self):
        """Return the file path owned by the active graph context.

        The root graph owns ``self.current_file_path``. A sub-graph view is a
        separate save context: saving from inside an embedded sub-graph must
        serialize that sub-graph as a standalone graph file, not the parent
        root graph. Linked/reference-only contexts use their linked path as the
        context file path.
        """
        if not self._graph_context_stack:
            return self.current_file_path or ""
        context = self._graph_context_stack[-1]
        if context.get("current_file_path"):
            return context.get("current_file_path") or ""
        if context.get("reference_only"):
            return context.get("linked_graph_path") or ""
        return ""

    def _default_file_name(self):
        context_path = self._current_context_file_path()
        if context_path:
            return context_path
        if self._graph_context_stack:
            context = self._graph_context_stack[-1]
            props = context.get("node_properties") or {}
            base = str(props.get("graph_name") or context.get("title") or self.editor_title() or "Untitled Graph").strip()
            base = base or "Untitled Graph"
            return f"{base}{self.graph_file_extension_for_view_id(self._active_node_view_id)}"
        return self.current_file_path or f"{self.editor_title()}.nexnode"

    def save_graph_to_file(self):
        context_path = self._current_context_file_path()
        if context_path:
            return self._save_graph_to_path(context_path)
        return self.save_graph_to_file_as()

    def save_graph_to_file_as(self):
        file_path, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Graph",
            self._default_file_name(),
            self.graph_file_filter_for_view_id(self._active_node_view_id, save=True)
        )
        if not file_path:
            return False
        if '.' not in os.path.basename(file_path):
            if selected_filter.startswith('Graph JSON'):
                file_path = f"{file_path}.json"
            else:
                file_path = f"{file_path}{self.graph_file_extension_for_view_id(self._active_node_view_id)}"
        return self._save_graph_to_path(file_path)

    def _save_payload_for_active_context(self):
        """Serialize the graph currently shown in the editor.

        This is intentionally different from session/state saving. File Save and
        Save As must honor the active graph context. If the user is editing a
        Sequence sub-graph, the file payload must be that Sequence graph only.
        """
        if self._graph_context_stack:
            return self._save_current_graph_context()
        return self.collapse_all_inline_subgraphs() or self.scene.serialize_graph()

    def _validate_save_path_for_graph(self, file_path, graph_data):
        metadata = graph_data.get("metadata") if isinstance(graph_data, dict) else {}
        view_id = metadata.get("active_node_view_id") if isinstance(metadata, dict) else self._active_node_view_id
        expected_ext = self.graph_file_extension_for_view_id(view_id or self._active_node_view_id)
        if expected_ext and not expected_ext.startswith('.'):
            expected_ext = '.' + expected_ext
        actual_ext = Path(file_path).suffix
        if expected_ext and actual_ext and actual_ext.lower() != expected_ext.lower():
            QtWidgets.QMessageBox.warning(
                self,
                "Save Extension Mismatch",
                f"This graph type must be saved as a {expected_ext} file."
            )
            return False
        return True

    # ------------------------------------------------------------------
    # File integrity / load-save validation
    # ------------------------------------------------------------------
    def _view_id_allowed_for_tool(self, view_id):
        if not view_id:
            return True
        if self.graph_allowed_node_view_ids is not None:
            return view_id in set(self.graph_allowed_node_view_ids or [])
        prefixes = self.graph_allowed_node_view_prefixes or []
        if prefixes:
            return any(str(view_id).startswith(str(prefix)) for prefix in prefixes)
        return True

    def _canonical_graph_payload_for_hash(self, graph_data):
        safe = graph_json_safe(graph_data if isinstance(graph_data, dict) else {})
        metadata = dict(safe.get('metadata') or {})
        metadata.pop('graph_integrity', None)
        metadata.pop('graph_sha256', None)
        safe['metadata'] = metadata
        return safe

    def _compute_graph_payload_hash(self, graph_data):
        canonical = self._canonical_graph_payload_for_hash(graph_data)
        encoded = json.dumps(canonical, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
        return hashlib.sha256(encoded).hexdigest()

    def _stamp_graph_integrity_hash(self, graph_data):
        if not isinstance(graph_data, dict):
            return graph_data
        metadata = graph_data.setdefault('metadata', {})
        metadata['graph_integrity'] = {
            'algorithm': 'sha256',
            'sha256': self._compute_graph_payload_hash(graph_data),
        }
        return graph_data

    def _verify_graph_integrity_hash(self, graph_data, *, show_feedback=True):
        if not isinstance(graph_data, dict):
            return False, 'Graph payload is not an object.'
        metadata = graph_data.get('metadata') if isinstance(graph_data.get('metadata'), dict) else {}
        integrity = metadata.get('graph_integrity') if isinstance(metadata, dict) else None
        if not isinstance(integrity, dict) or not integrity.get('sha256'):
            # Backward compatibility: older graph files do not have a hash yet.
            return True, ''
        expected = str(integrity.get('sha256') or '').strip().lower()
        actual = self._compute_graph_payload_hash(graph_data).lower()
        if expected != actual:
            reason = 'Graph file integrity check failed. The file may have been edited outside Nexus or corrupted.'
            if show_feedback:
                QtWidgets.QMessageBox.critical(self, 'Graph Integrity Check Failed', reason)
            return False, reason
        return True, ''

    def _graph_extension_matches_view(self, file_path, view_id):
        if not file_path or not view_id:
            return True, ''
        actual_ext = Path(file_path).suffix
        if not actual_ext or actual_ext.lower() in {'.json', '.nexnode'}:
            return True, ''
        expected_ext = self.graph_file_extension_for_view_id(view_id)
        if expected_ext and not expected_ext.startswith('.'):
            expected_ext = '.' + expected_ext
        if expected_ext and actual_ext.lower() != expected_ext.lower():
            return False, f'File extension {actual_ext} does not match graph type {view_id}; expected {expected_ext}.'
        return True, ''

    def _validate_graph_payload_for_view_id(self, graph_data, view_id):
        if not isinstance(graph_data, dict):
            return ['Graph payload is not an object.']
        messages = []
        if view_id and view_id not in NODE_VIEW_REGISTRY:
            messages.append(f'Unknown graph view id: {view_id}')
            return messages
        if view_id and not self._view_id_allowed_for_tool(view_id):
            messages.append(f'Graph view {view_id} is not valid for {self.graph_tool_label}.')
            return messages
        registry = self._registry_for_view_id(view_id) if view_id else self.active_node_registry()
        disallowed_types = self._disallowed_node_types_in_graph_data(graph_data, registry=registry)
        if disallowed_types:
            messages.append('Graph contains node types that are not allowed in this graph type: ' + ', '.join(disallowed_types))
        view_definition = NODE_VIEW_REGISTRY.get(view_id) if view_id else self.active_node_view()
        messages.extend(self._validate_graph_against_rules(graph_data=graph_data, view_definition=view_definition))
        return messages

    def _validate_graph_payload_for_load(self, graph_data, *, file_path='', expected_view_id=None, show_feedback=True):
        ok, reason = self._verify_graph_integrity_hash(graph_data, show_feedback=show_feedback)
        if not ok:
            return False, reason
        metadata = graph_data.get('metadata') if isinstance(graph_data, dict) else {}
        actual_view_id = metadata.get('active_node_view_id') if isinstance(metadata, dict) else None
        view_id = actual_view_id or expected_view_id
        if expected_view_id and actual_view_id and actual_view_id != expected_view_id:
            expected_name = getattr(NODE_VIEW_REGISTRY.get(expected_view_id), 'name', expected_view_id)
            actual_name = getattr(NODE_VIEW_REGISTRY.get(actual_view_id), 'name', actual_view_id)
            reason = f'This graph must be a {expected_name}; the file is a {actual_name}.'
            if show_feedback:
                QtWidgets.QMessageBox.warning(self, 'Invalid Graph Type', reason)
            return False, reason
        if view_id is None and isinstance(graph_data, dict) and graph_data.get('nodes'):
            view_id = self._find_compatible_view_id_for_graph_data(graph_data)
        ok, reason = self._graph_extension_matches_view(file_path, view_id)
        if not ok:
            if show_feedback:
                QtWidgets.QMessageBox.warning(self, 'Graph Extension Mismatch', reason)
            return False, reason
        messages = self._validate_graph_payload_for_view_id(graph_data, view_id)
        if messages:
            reason = '\n'.join(messages)
            if show_feedback:
                QtWidgets.QMessageBox.warning(self, f'{self.graph_view_label} Validation Failed', reason)
            return False, reason
        return True, ''

    def _save_graph_to_path(self, file_path):
        graph_data = self._save_payload_for_active_context()
        metadata = graph_data.setdefault("metadata", {})
        metadata["active_node_view_id"] = self._active_node_view_id
        metadata["graph_file_extension"] = self.graph_file_extension_for_view_id(self._active_node_view_id)
        self._write_bookmark_metadata_to_graph(graph_data)

        validation_messages = self._validate_graph_payload_for_view_id(graph_data, self._active_node_view_id)
        if validation_messages:
            QtWidgets.QMessageBox.warning(self, f'{self.graph_view_label} Validation Failed', '\n'.join(validation_messages))
            return False

        if not self._validate_save_path_for_graph(file_path, graph_data):
            return False

        self._stamp_graph_integrity_hash(graph_data)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(graph_data, f, indent=2)
            if self._graph_context_stack:
                # Do not replace the parent/root graph file path when saving a
                # sub-graph as its own standalone artifact.
                self._graph_context_stack[-1]["current_file_path"] = file_path
            else:
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
                self.graph_file_filter_for_view_id(self._active_node_view_id, save=False)
            )
        if not file_path:
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)

            ok, reason = self._validate_graph_payload_for_load(graph_data, file_path=file_path, show_feedback=True)
            if not ok:
                return False

            self._graph_context_stack = []
            self._root_graph_data = None
            self._inline_subgraph_expansions = {}
            metadata = graph_data.get("metadata") if isinstance(graph_data, dict) else None
            active_view_id = self._node_view_id_for_graph_payload(graph_data, file_path=file_path, fallback_view_id=(metadata.get("active_node_view_id") if isinstance(metadata, dict) else None))
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
                        f"{self.graph_view_label} Compatibility",
                        f"This graph contains node types that are not available in the selected {self.graph_view_label}\n\n%s" % "\n".join(disallowed_types),
                    )
                    return False

            self.scene._suspend_undo = True
            try:
                self.scene.load_graph(self._ensure_graph_control_flow_nodes(graph_data))
                self._set_graph_bookmarks_from_payload(graph_data)
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
