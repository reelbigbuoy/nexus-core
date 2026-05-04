# ============================================================================
# Nexus
# File: plugins/owner/NoDELite/node_plugin/view.py
# Description: View layer and interaction handling for NoDE Plugin.
# Part of: NoDE Lite Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================

from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets
from .constants import ZOOM_MIN, ZOOM_MAX, ZOOM_STEP, FIT_PADDING
from .definitions import NODE_REGISTRY, NodeDefinitionRegistry
from .graphics_items import NodeItem, ConnectionItem, PortItem, ConnectionPinItem, InlineSubgraphBoundaryItem, _distance_to_segment
from .commands import AddNodeCommand, AddConnectionCommand
from .authoring import PaletteUsageStore
from .geometry import qpoint, qrect, px


class NodePalettePopup(QtWidgets.QDialog):
    def __init__(self, parent=None, registry=None, title="All Actions for this Graph", filter_fn=None, template_service=None):
        super().__init__(parent, QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self.setObjectName('NoDENodePalettePopup')
        self.setMinimumSize(360, 460)
        self._chosen_definition = None
        self._registry = registry or NODE_REGISTRY
        self._filter_fn = filter_fn
        self._template_service = template_service
        self._chosen_template_id = None
        if not isinstance(self._registry, NodeDefinitionRegistry):
            raise TypeError("NodePalettePopup requires a NodeDefinitionRegistry")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QtWidgets.QLabel(title, self)
        header.setObjectName('titleLabel')
        layout.addWidget(header)

        self.search_edit = QtWidgets.QLineEdit(self)
        self.search_edit.setPlaceholderText('Search')
        self.search_edit.textChanged.connect(self._rebuild_tree)
        self.search_edit.installEventFilter(self)
        layout.addWidget(self.search_edit)

        self.tree = QtWidgets.QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(14)
        self.tree.setUniformRowHeights(True)
        self.tree.setMouseTracking(True)
        self.tree.viewport().setMouseTracking(True)
        self.tree.itemEntered.connect(self._on_item_hovered)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_activated)
        self.tree.itemActivated.connect(self._on_item_activated)
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        layout.addWidget(self.tree, 1)

        self.hint_label = QtWidgets.QLabel("Right-click a node type to favorite it. Press Enter to insert.", self)
        self.hint_label.setObjectName("hintLabel")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        self.setStyleSheet("""
        QDialog#NoDENodePalettePopup {
            background: #161616;
            border: 1px solid #3a3a3a;
            border-radius: 6px;
        }
        QLabel#titleLabel {
            color: #d8d8d8;
            font-size: 14px;
            padding: 2px 2px 0 2px;
        }
        QLabel#hintLabel {
            color: #a8a8a8;
            font-size: 11px;
            padding: 0 2px 2px 2px;
        }
        QLineEdit {
            background: #0f0f0f;
            color: #e6e6e6;
            border: 1px solid #2a74ff;
            border-radius: 12px;
            padding: 6px 10px;
        }
        QTreeWidget {
            background: #121212;
            color: #d9d9d9;
            border: none;
            outline: none;
        }
        QTreeWidget::item {
            padding: 4px 4px;
        }
        QTreeWidget::item:selected {
            background: #2a74ff;
            color: white;
        }
        """)

        self._rebuild_tree()

    def show_at(self, global_pos):
        self.move(qpoint(global_pos))
        QtCore.QTimer.singleShot(0, self._focus_search)

    def _focus_search(self):
        self.raise_()
        self.activateWindow()
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def eventFilter(self, obj, event):
        if obj is self.search_edit and event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            if key in (QtCore.Qt.Key_Down, QtCore.Qt.Key_Up, QtCore.Qt.Key_PageDown, QtCore.Qt.Key_PageUp):
                QtWidgets.QApplication.sendEvent(self.tree, event)
                return True
            if key in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right):
                current = self.tree.currentItem()
                if current is None:
                    return True
                definition = current.data(0, QtCore.Qt.UserRole)
                if definition is None:
                    if key == QtCore.Qt.Key_Left:
                        current.setExpanded(False)
                    else:
                        current.setExpanded(True)
                else:
                    parent = current.parent()
                    if key == QtCore.Qt.Key_Left and parent is not None:
                        self.tree.setCurrentItem(parent)
                    elif key == QtCore.Qt.Key_Right:
                        self._on_item_activated(current, 0)
                return True
        return super().eventFilter(obj, event)

    def chosen_definition(self):
        return self._chosen_definition

    def chosen_template_id(self):
        return self._chosen_template_id

    def _search_text(self):
        return self.search_edit.text().strip()

    def _visible_definition(self, definition):
        metadata = getattr(definition, 'metadata', {}) or {}
        return not bool(metadata.get('hide_from_palette') or metadata.get('required_graph_node'))

    def _definition_by_type_id(self, type_id):
        return self._registry.get(type_id) if self._registry is not None else None

    def _passes_filter(self, definition):
        if self._filter_fn is None:
            return True
        try:
            return bool(self._filter_fn(definition))
        except Exception:
            return False

    def _definitions_by_category(self):
        query = self._search_text()
        definitions = [definition for definition in self._registry.search(query) if self._visible_definition(definition) and self._passes_filter(definition)]
        grouped = {}

        if not query:
            favorites = []
            for type_id in PaletteUsageStore.favorites():
                definition = self._definition_by_type_id(type_id)
                if definition is not None and self._visible_definition(definition) and self._passes_filter(definition):
                    favorites.append(definition)
            if favorites:
                grouped["★ Favorites"] = favorites

            recents = []
            favorite_ids = {definition.type_id for definition in favorites}
            for type_id in PaletteUsageStore.recents():
                definition = self._definition_by_type_id(type_id)
                if definition is not None and self._visible_definition(definition) and self._passes_filter(definition) and definition.type_id not in favorite_ids:
                    recents.append(definition)
            if recents:
                grouped["Recent"] = recents

        for definition in definitions:
            grouped.setdefault(definition.category, []).append(definition)

        # User graph templates are shared-framework artifacts.  They appear in
        # the same searchable authoring popup, but remain distinct from node
        # definitions so plugins can filter node types without owning template
        # storage or insertion behavior.
        if self._template_service is not None:
            try:
                template_query = query.lower()
                templates = []
                for summary in self._template_service.list_templates():
                    haystack = " ".join([summary.name, summary.description, summary.category]).lower()
                    if not template_query or template_query in haystack:
                        templates.append(summary)
                if templates:
                    grouped.setdefault("Templates", []).extend(templates)
            except Exception:
                pass
        return grouped

    def _rebuild_tree(self):
        self.tree.clear()
        first_leaf = None
        for category, definitions in self._definitions_by_category().items():
            if not definitions:
                continue
            cat_item = QtWidgets.QTreeWidgetItem([category])
            cat_item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.tree.addTopLevelItem(cat_item)
            for definition in definitions:
                if hasattr(definition, 'template_id'):
                    leaf = QtWidgets.QTreeWidgetItem(["▣ " + definition.name])
                    leaf.setData(0, QtCore.Qt.UserRole, {'kind': 'template', 'id': definition.template_id})
                    if definition.description:
                        leaf.setToolTip(0, definition.description)
                else:
                    prefix = "★ " if definition.type_id in PaletteUsageStore.favorites() else ""
                    leaf = QtWidgets.QTreeWidgetItem([prefix + definition.display_name])
                    leaf.setData(0, QtCore.Qt.UserRole, definition)
                    if definition.description:
                        leaf.setToolTip(0, definition.description)
                cat_item.addChild(leaf)
                if first_leaf is None:
                    first_leaf = leaf
            cat_item.setExpanded(True)
        if first_leaf is not None:
            self.tree.setCurrentItem(first_leaf)

    def _on_item_hovered(self, item, column=0):
        if item is not None:
            self.tree.setCurrentItem(item)

    def _on_item_clicked(self, item, column=0):
        definition = item.data(0, QtCore.Qt.UserRole)
        if definition is None:
            item.setExpanded(not item.isExpanded())
            self.tree.setCurrentItem(item)
            return
        self._on_item_activated(item, column)

    def _on_item_activated(self, item, column=0):
        definition = item.data(0, QtCore.Qt.UserRole)
        if definition is None:
            item.setExpanded(not item.isExpanded())
            self.tree.setCurrentItem(item)
            return
        if isinstance(definition, dict) and definition.get('kind') == 'template':
            self._chosen_template_id = definition.get('id')
            self._chosen_definition = None
            self.accept()
            return
        self._chosen_definition = definition
        self._chosen_template_id = None
        PaletteUsageStore.record_recent(definition.type_id)
        self.accept()


    def _show_tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if item is None:
            return
        definition = item.data(0, QtCore.Qt.UserRole)
        if definition is None or isinstance(definition, dict):
            return
        menu = QtWidgets.QMenu(self)
        is_favorite = definition.type_id in PaletteUsageStore.favorites()
        favorite_action = menu.addAction("Remove Favorite" if is_favorite else "Add to Favorites")
        chosen = menu.exec_(self.tree.viewport().mapToGlobal(pos))
        if chosen is favorite_action:
            PaletteUsageStore.toggle_favorite(definition.type_id)
            self._rebuild_tree()

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            current = self.tree.currentItem()
            if current is not None:
                self._on_item_activated(current, 0)
                if self.result() == QtWidgets.QDialog.Accepted:
                    event.accept()
                    return
        super().keyPressEvent(event)


class GraphView(QtWidgets.QGraphicsView):
    @staticmethod
    def _is_inline_preview_item(item):
        if item is None:
            return False

        # Inline sub-graph previews are read-only, but the dashed boundary item
        # owns the collapse control and must continue to receive normal mouse
        # press/release events.  Treat only preview contents as blocked.
        if isinstance(item, InlineSubgraphBoundaryItem):
            return False

        if getattr(item, '_inline_subgraph_display', False):
            return True

        parent_node = getattr(item, 'parent_node', None)
        if parent_node is not None:
            if isinstance(parent_node, InlineSubgraphBoundaryItem):
                return False
            if getattr(parent_node, '_inline_subgraph_display', False):
                return True

        parent_item = item.parentItem() if hasattr(item, 'parentItem') else None
        if parent_item is not None:
            if isinstance(parent_item, InlineSubgraphBoundaryItem):
                return False
            if getattr(parent_item, '_inline_subgraph_display', False):
                return True

        return False

    def __init__(self, parent=None, editor=None):
        super().__init__(parent)
        self.editor = editor

        self.setRenderHints(
            QtGui.QPainter.Antialiasing |
            QtGui.QPainter.TextAntialiasing |
            QtGui.QPainter.SmoothPixmapTransform
        )

        self.setViewportUpdateMode(QtWidgets.QGraphicsView.BoundingRectViewportUpdate)
        self.setOptimizationFlag(QtWidgets.QGraphicsView.DontSavePainterState, True)
        self.setOptimizationFlag(QtWidgets.QGraphicsView.DontAdjustForAntialiasing, True)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._panning = False
        self._pan_start = QtCore.QPoint()
        self._pan_button = None
        self._right_pan_candidate = False
        self._right_press_pos = QtCore.QPoint()
        self._right_press_global = QtCore.QPoint()
        self._right_pan_threshold = 6
        self._suppress_next_context_menu = False


        self._selection_band = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self.viewport())
        self._selection_origin = None
        self._selection_active = False
        self._selection_modifiers = QtCore.Qt.NoModifier
        self._selection_threshold = 4

        self._current_zoom = 1.0
        self._zoom_min = ZOOM_MIN
        self._zoom_max = ZOOM_MAX

        self._auto_pan_margin = 44
        self._auto_pan_max_step = 26
        self._node_registry = NODE_REGISTRY

    def set_node_registry(self, registry):
        if registry is None:
            registry = NODE_REGISTRY
        if not isinstance(registry, NodeDefinitionRegistry):
            raise TypeError("GraphView requires a NodeDefinitionRegistry")
        self._node_registry = registry

    def node_registry(self):
        return self._node_registry

    def _set_zoom_message(self):
        window = self.window()
        if hasattr(window, "statusbar"):
            percent = int(self._current_zoom * 100)
            window.statusbar.showMessage(f"Zoom: {percent}%", 1500)

    def _apply_zoom_factor(self, factor):
        new_zoom = self._current_zoom * factor

        if new_zoom < self._zoom_min:
            factor = self._zoom_min / self._current_zoom
            new_zoom = self._zoom_min
        elif new_zoom > self._zoom_max:
            factor = self._zoom_max / self._current_zoom
            new_zoom = self._zoom_max

        if abs(factor - 1.0) < 0.0001:
            return

        self.scale(factor, factor)
        self._current_zoom = new_zoom
        self._set_zoom_message()

    def reset_zoom(self):
        self.resetTransform()
        self._current_zoom = 1.0
        self._set_zoom_message()

    def frame_scene_rect(self):
        scene = self.scene()
        if scene is None:
            return

        if hasattr(scene, "ensure_logical_scene_rect"):
            scene.ensure_logical_scene_rect()
        rect = scene.sceneRect()
        if not rect.isValid() or rect.isNull():
            return

        if hasattr(scene, "ensure_logical_scene_rect"):
            scene.ensure_logical_scene_rect(rect)
        rect = rect.adjusted(-FIT_PADDING, -FIT_PADDING, FIT_PADDING, FIT_PADDING)
        self.fitInView(rect, QtCore.Qt.KeepAspectRatio)
        self._current_zoom = max(self._zoom_min, min(self._zoom_max, self.transform().m11()))
        self._set_zoom_message()

    def frame_items(self, items):
        if not items:
            return

        rect = QtCore.QRectF()
        for item in items:
            rect = rect.united(item.sceneBoundingRect())

        if not rect.isValid() or rect.isNull():
            return

        rect = rect.adjusted(-FIT_PADDING, -FIT_PADDING, FIT_PADDING, FIT_PADDING)
        self.fitInView(rect, QtCore.Qt.KeepAspectRatio)
        self._current_zoom = max(self._zoom_min, min(self._zoom_max, self.transform().m11()))
        self._set_zoom_message()

    def frame_selected_or_all(self):
        scene = self.scene()
        if scene is None:
            return

        selected = [
            item for item in scene.selectedItems()
            if isinstance(item, (NodeItem, ConnectionItem, InlineSubgraphBoundaryItem)) and item.isVisible()
        ]
        # UX rule: a single selected item usually means the user wants to get
        # re-oriented, not zoom into that one node. Multiple selections frame
        # the selected working set.
        if len(selected) > 1:
            self.frame_items(selected)
            return

        self.frame_visible_graph()

    def frame_visible_graph(self):
        """Frame visible graph content, including inline sub-graph boundaries."""
        scene = self.scene()
        if scene is None:
            return

        graph_items = [
            item for item in scene.items()
            if isinstance(item, (NodeItem, ConnectionItem, InlineSubgraphBoundaryItem)) and item.isVisible()
        ]
        self.frame_items(graph_items)

    def frame_all_nodes(self):
        scene = self.scene()
        if scene is None:
            return

        nodes = [item for item in scene.items() if isinstance(item, NodeItem)]
        self.frame_items(nodes)

    def _spawn_node_definition(self, definition, scene_pos):
        if definition is None:
            return None
        scene = self.scene()
        if scene is None:
            return None
        was_empty_graph = not any(isinstance(item, NodeItem) for item in scene.items())
        editor = getattr(self, "editor", None)
        if editor is not None and hasattr(editor, '_can_add_node_type'):
            if not editor._can_add_node_type(definition.type_id, show_feedback=True):
                return None
        created_node_id = None
        undo_stack = getattr(editor, "undo_stack", None)
        if undo_stack is not None:
            command = AddNodeCommand(
                scene,
                definition.display_name,
                scene_pos,
                node_type=definition.type_id,
            )
            created_node_id = command.node_entry.get("node_data", {}).get("node_id")
            undo_stack.push(command)
        else:
            node = scene.add_node(
                definition.display_name,
                scene_pos,
                node_type=definition.type_id,
            )
            created_node_id = getattr(getattr(node, "node_data", None), "node_id", None)

        node_item = scene.find_node_by_id(created_node_id) if created_node_id and hasattr(scene, 'find_node_by_id') else None
        if was_empty_graph:
            self._frame_first_node_after_spawn(created_node_id)
        return node_item

    def _frame_first_node_after_spawn(self, node_id):
        """Zoom to a newly placed first node instead of leaving empty-graph zoom."""
        def _frame():
            scene = self.scene()
            if scene is None:
                return
            node = scene.find_node_by_id(node_id) if node_id and hasattr(scene, 'find_node_by_id') else None
            if node is None:
                nodes = [item for item in scene.items() if isinstance(item, NodeItem)]
                node = nodes[0] if len(nodes) == 1 else None
            if node is not None:
                self.frame_items([node])

        QtCore.QTimer.singleShot(0, _frame)

    def _show_graph_node_palette(self, local_pos, global_pos, title="All Actions for this Graph", filter_fn=None, connect_from_port=None):
        scene_pos = self.mapToScene(local_pos)
        editor = getattr(self, "editor", None)
        popup = NodePalettePopup(self, registry=self.node_registry(), title=title, filter_fn=filter_fn, template_service=getattr(editor, 'template_service', None))
        popup.show_at(global_pos)
        accepted = popup.exec_() == QtWidgets.QDialog.Accepted
        if accepted:
            # The palette is often opened from a right-button release.  When the
            # user chooses a node, Qt can deliver a follow-on context event from
            # the same pointer gesture.  Suppress that one re-entrant context
            # event so node insertion is a single, clean action.
            self._suppress_next_context_menu = True
            QtCore.QTimer.singleShot(250, lambda: setattr(self, '_suppress_next_context_menu', False))
            template_id = popup.chosen_template_id()
            if template_id and editor is not None and hasattr(editor, 'insert_template'):
                editor.insert_template(template_id, scene_pos)
                return
            node_item = self._spawn_node_definition(popup.chosen_definition(), scene_pos)
            if connect_from_port is not None and node_item is not None:
                self._connect_drag_source_to_new_node(connect_from_port, node_item)

    def _definition_has_compatible_port(self, source_port, definition):
        if source_port is None or definition is None:
            return False
        scene = self.scene()
        if scene is None:
            return False
        editor = getattr(self, "editor", None)
        if editor is not None and hasattr(editor, '_can_add_node_type'):
            try:
                if not editor._can_add_node_type(definition.type_id, show_feedback=False):
                    return False
            except TypeError:
                if not editor._can_add_node_type(definition.type_id):
                    return False
            except Exception:
                return False

        source_is_output = source_port.port_type == PortItem.OUTPUT
        candidate_defs = definition.inputs if source_is_output else definition.outputs
        for port_def in candidate_defs:
            if self._definition_port_compatible_with_source(source_port, port_def):
                return True
        return False

    def _definition_port_compatible_with_source(self, source_port, candidate_port_def):
        source_def = getattr(source_port, 'definition_port', None)

        def _kind(port_def):
            if port_def is None:
                return 'data'
            resolver = getattr(port_def, 'resolved_connection_kind', None)
            if callable(resolver):
                try:
                    return str(resolver() or 'data').strip().lower() or 'data'
                except Exception:
                    pass
            explicit = getattr(port_def, 'connection_kind', None)
            if explicit:
                return str(explicit).strip().lower() or 'data'
            return 'exec' if str(getattr(port_def, 'data_type', '')).strip().lower() == 'exec' else 'data'

        def _dtype(port_def):
            token = str(getattr(port_def, 'data_type', 'any') or 'any').strip().lower()
            aliases = {'string': 'str', 'boolean': 'bool', 'integer': 'int', 'double': 'float', 'object': 'complex'}
            return aliases.get(token, token)

        if _kind(source_def) != _kind(candidate_port_def):
            return False
        if _kind(source_def) != 'data':
            return True
        source_type = _dtype(source_def)
        target_type = _dtype(candidate_port_def)
        return source_type in ('', 'any', '*') or target_type in ('', 'any', '*') or source_type == target_type

    def _connect_drag_source_to_new_node(self, source_port, node_item):
        scene = self.scene()
        if scene is None or source_port is None or node_item is None:
            return False
        candidate_ports = node_item.inputs if source_port.port_type == PortItem.OUTPUT else node_item.outputs
        for candidate in candidate_ports:
            normalized_source, normalized_target = scene._normalized_connection_ports(source_port, candidate)
            if normalized_source is None or normalized_target is None:
                continue
            if not scene._editor_allows_connection(normalized_source, normalized_target):
                continue
            connection_kind = None
            editor = getattr(self, "editor", None)
            if editor is not None and hasattr(editor, "_connection_kind_for_ports"):
                try:
                    connection_kind = editor._connection_kind_for_ports(normalized_source, normalized_target)
                except Exception:
                    connection_kind = None
            connection_data = {
                "source_node_id": normalized_source.parent_node.node_data.node_id,
                "source_port": normalized_source.name,
                "target_node_id": normalized_target.parent_node.node_data.node_id,
                "target_port": normalized_target.name,
                "route_points": [],
                "connection_kind": connection_kind,
            }
            editor = getattr(self, "editor", None)
            undo_stack = getattr(editor, "undo_stack", None)
            if undo_stack is not None:
                undo_stack.push(AddConnectionCommand(scene, connection_data))
            else:
                scene.add_connection_from_dict(connection_data)
            return True
        return False


    def _selected_layout_item_count(self):
        editor = getattr(self, "editor", None)
        if editor is None or not hasattr(editor, '_selected_layout_items'):
            return 0
        try:
            return len(editor._selected_layout_items())
        except Exception:
            return 0

    def _add_layout_actions_to_menu(self, menu):
        editor = getattr(self, "editor", None)
        layout_menu = menu.addMenu("Layout")
        enabled_align = self._selected_layout_item_count() >= 2
        enabled_dist = self._selected_layout_item_count() >= 3
        actions = []
        for label, method, arg, enabled in [
            ("Align Left", 'align_selected_nodes', 'left', enabled_align),
            ("Align Center X", 'align_selected_nodes', 'center', enabled_align),
            ("Align Right", 'align_selected_nodes', 'right', enabled_align),
            ("Align Top", 'align_selected_nodes', 'top', enabled_align),
            ("Align Middle Y", 'align_selected_nodes', 'middle', enabled_align),
            ("Align Bottom", 'align_selected_nodes', 'bottom', enabled_align),
        ]:
            act = layout_menu.addAction(label)
            act.setEnabled(bool(editor is not None and hasattr(editor, method) and enabled))
            actions.append((act, method, arg))
        layout_menu.addSeparator()
        for label, method, arg, enabled in [
            ("Distribute Horizontally", 'distribute_selected_nodes', 'horizontal', enabled_dist),
            ("Distribute Vertically", 'distribute_selected_nodes', 'vertical', enabled_dist),
        ]:
            act = layout_menu.addAction(label)
            act.setEnabled(bool(editor is not None and hasattr(editor, method) and enabled))
            actions.append((act, method, arg))
        return actions

    def _dispatch_layout_action(self, chosen, layout_actions):
        if chosen is None:
            return False
        editor = getattr(self, "editor", None)
        if editor is None:
            return False
        for act, method, arg in layout_actions:
            if chosen is act and hasattr(editor, method):
                getattr(editor, method)(arg)
                return True
        return False

    def _show_canvas_context_menu(self, local_pos, global_pos):
        """Show searchable insertion palette for empty graph space.

        Blank-canvas right-click is graph authoring, regardless of current
        selection.  Node-specific menus are only shown when the actual click
        lands on a node item.
        """
        self._show_graph_node_palette(local_pos, global_pos)

    def _show_node_context_menu(self, node_item, global_pos):
        editor = getattr(self, "editor", None)
        menu = QtWidgets.QMenu(self)
        menu.setToolTipsVisible(True)
        layout_actions = self._add_layout_actions_to_menu(menu) if self._selected_layout_item_count() >= 2 else []
        if layout_actions:
            menu.addSeparator()

        is_subgraph = bool(editor is not None and hasattr(editor, 'is_subgraph_container_node') and editor.is_subgraph_container_node(node_item))
        if is_subgraph:
            act_open_subgraph = menu.addAction("Open Sub-Graph")
            act_expand_subgraph = menu.addAction("Expand Sub-Graph Here")
            menu.addSeparator()
        else:
            act_open_subgraph = None
            act_expand_subgraph = None

        act_rename = menu.addAction("Rename Node")
        act_rename.setShortcut(QtGui.QKeySequence("F2"))
        menu.addSeparator()
        act_delete = menu.addAction("Delete")
        act_delete.setShortcut(QtGui.QKeySequence.Delete)
        act_cut = menu.addAction("Cut")
        act_cut.setShortcut(QtGui.QKeySequence.Cut)
        act_copy = menu.addAction("Copy")
        act_copy.setShortcut(QtGui.QKeySequence.Copy)
        act_duplicate = menu.addAction("Duplicate")
        act_duplicate.setShortcut(QtGui.QKeySequence("Ctrl+D"))
        act_save_template = menu.addAction("Save Selection as Template…")
        act_save_template.setEnabled(bool(editor is not None and hasattr(editor, 'save_selection_as_template')))
        act_template_libs = menu.addAction("Template Libraries…")
        act_template_libs.setEnabled(bool(editor is not None and hasattr(editor, 'configure_template_libraries')))
        act_break_links = menu.addAction("Break Node Links")
        menu.addSeparator()
        act_properties = menu.addAction("Open Properties")

        chosen = menu.exec_(global_pos)
        if self._dispatch_layout_action(chosen, layout_actions):
            return
        if chosen is None or editor is None:
            return
        if chosen is act_open_subgraph:
            editor.open_subgraph_for_node(node_item)
        elif chosen is act_expand_subgraph:
            editor.expand_subgraph_node(node_item)
        elif chosen is act_rename:
            if hasattr(editor, 'rename_node_via_dialog'):
                editor.rename_node_via_dialog(node_item)
        elif chosen is act_delete:
            editor.delete_selected_items()
        elif chosen is act_cut:
            editor.cut()
        elif chosen is act_copy:
            editor.copy()
        elif chosen is act_duplicate:
            if hasattr(editor, 'duplicate_selection'):
                editor.duplicate_selection()
        elif chosen is act_save_template:
            if hasattr(editor, 'save_selection_as_template'):
                editor.save_selection_as_template()
        elif chosen is act_template_libs:
            if hasattr(editor, 'configure_template_libraries'):
                editor.configure_template_libraries()
        elif chosen is act_break_links:
            if hasattr(editor, 'break_node_links'):
                editor.break_node_links(node_item)
        elif chosen is act_properties:
            editor.open_properties_for_node(node_item)

    def _maybe_auto_pan_during_drag(self, view_pos):
        scene = self.scene()
        if scene is None:
            return False
        grabber = scene.mouseGrabberItem()
        if not isinstance(grabber, (NodeItem, ConnectionPinItem)):
            return False

        vp = self.viewport().rect()
        margin = max(8, int(self._auto_pan_margin))
        dx = 0
        dy = 0

        if view_pos.x() < margin:
            dx = -self._edge_scroll_step(view_pos.x(), margin)
        elif view_pos.x() > vp.width() - margin:
            dx = self._edge_scroll_step(vp.width() - view_pos.x(), margin)

        if view_pos.y() < margin:
            dy = -self._edge_scroll_step(view_pos.y(), margin)
        elif view_pos.y() > vp.height() - margin:
            dy = self._edge_scroll_step(vp.height() - view_pos.y(), margin)

        if dx == 0 and dy == 0:
            return False

        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + dx)
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() + dy)
        return True

    def _edge_scroll_step(self, distance_to_edge, margin):
        ratio = 1.0 - max(0.0, min(float(distance_to_edge), float(margin))) / float(max(1, margin))
        return max(1, int(round((ratio ** 1.5) * self._auto_pan_max_step)))

    def _begin_selection_band(self, origin, modifiers):
        self._selection_origin = qpoint(origin)
        self._selection_modifiers = modifiers
        self._selection_active = False
        self._selection_band.hide()

    def _update_selection_band(self, current_pos):
        rect = QtCore.QRect(self._selection_origin, qpoint(current_pos)).normalized()
        drag_distance = abs(rect.width()) + abs(rect.height())
        if not self._selection_active and drag_distance < self._selection_threshold:
            return False
        if not self._selection_active:
            self._selection_active = True
            self._selection_band.show()
        self._selection_band.setGeometry(qrect(rect))
        return True

    def _restore_view_after_selection_band(self):
        return

    def _finish_selection_band(self, end_pos):
        if self._selection_origin is None:
            return False
        if not self._selection_active:
            self._selection_band.hide()
            self._selection_modifiers = QtCore.Qt.NoModifier
            self._selection_origin = None
            return False

        rect = QtCore.QRect(self._selection_origin, qpoint(end_pos)).normalized()
        self._selection_band.hide()
        self._selection_active = False

        scene_rect = QtCore.QRectF(self.mapToScene(rect.topLeft()), self.mapToScene(rect.bottomRight())).normalized()
        scene = self.scene()
        if scene is None:
            self._selection_modifiers = QtCore.Qt.NoModifier
            self._selection_origin = None
            return False

        items = []
        for item in scene.items(scene_rect, QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder):
            if isinstance(item, (NodeItem, ConnectionItem, ConnectionPinItem, InlineSubgraphBoundaryItem)):
                items.append(item)

        modifiers = self._selection_modifiers
        if not (modifiers & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)):
            scene.clearSelection()

        if modifiers & QtCore.Qt.ControlModifier:
            for item in items:
                item.setSelected(not item.isSelected())
        else:
            for item in items:
                item.setSelected(True)

        self._restore_view_after_selection_band()
        self._selection_modifiers = QtCore.Qt.NoModifier
        self._selection_origin = None
        return True

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self._apply_zoom_factor(ZOOM_STEP)
        else:
            self._apply_zoom_factor(1 / ZOOM_STEP)

    def mousePressEvent(self, event):
        scene = self.scene()

        if event.button() == QtCore.Qt.RightButton:
            self._right_pan_candidate = True
            self._right_press_pos = event.pos()
            self._right_press_global = event.globalPos()
            event.accept()
            return

        if event.button() == QtCore.Qt.LeftButton and scene is not None:
            item = self.itemAt(event.pos())
            scene_pos = self.mapToScene(event.pos())

            if self._is_inline_preview_item(item):
                event.accept()
                return

            if isinstance(item, ConnectionItem):
                endpoint = item.endpoint_hit(scene_pos)
                if endpoint is not None:
                    scene.begin_endpoint_reconnect(item, endpoint, scene_pos)
                    event.accept()
                    return

            if isinstance(item, PortItem):
                reconnect_connection, reconnect_endpoint = scene.reconnect_candidate_for_port(item)
                if reconnect_connection is not None and reconnect_endpoint is not None:
                    scene.begin_endpoint_reconnect(reconnect_connection, reconnect_endpoint, scene_pos)
                    event.accept()
                    return
                scene.begin_connection_drag(item)
                event.accept()
                return

            if item is None:
                self._begin_selection_band(event.pos(), event.modifiers())
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene = self.scene()

        if self._right_pan_candidate and not self._panning:
            if (event.pos() - self._right_press_pos).manhattanLength() >= self._right_pan_threshold:
                self._panning = True
                self._pan_button = QtCore.Qt.RightButton
                self._pan_start = event.pos()
                self.setCursor(QtCore.Qt.ClosedHandCursor)

        if self._panning:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if self._selection_origin is not None and (event.buttons() & QtCore.Qt.LeftButton):
            if self._update_selection_band(event.pos()):
                event.accept()
                return

        if event.buttons() & QtCore.Qt.LeftButton:
            self._maybe_auto_pan_during_drag(event.pos())

        if scene is not None:
            scene_pos = self.mapToScene(event.pos())
            item = self.itemAt(event.pos())
            if scene.drag_connection:
                scene.update_connection_drag(scene_pos, hovered_item=item)
                event.accept()
                return
            if scene.reconnect_connection:
                scene.update_endpoint_reconnect(scene_pos, hovered_item=item)
                event.accept()
                return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        scene = self.scene()

        if event.button() == QtCore.Qt.RightButton:
            if getattr(self, '_suppress_next_context_menu', False):
                self._suppress_next_context_menu = False
                self._right_pan_candidate = False
                event.accept()
                return
            was_panning = self._panning
            release_pos = event.pos()
            global_pos = event.globalPos()

            self._panning = False
            self._pan_button = None
            self.setCursor(QtCore.Qt.ArrowCursor)

            if self._right_pan_candidate and not was_panning:
                self._right_pan_candidate = False
                item = self.itemAt(release_pos)
                if isinstance(item, PortItem):
                    item = item.parentItem()
                if self._is_inline_preview_item(item):
                    event.accept()
                    return
                if isinstance(item, NodeItem):
                    if scene is not None and not item.isSelected():
                        scene.clearSelection()
                        item.setSelected(True)
                    self._show_node_context_menu(item, global_pos)
                elif isinstance(item, InlineSubgraphBoundaryItem):
                    self._show_canvas_context_menu(release_pos, global_pos)
                else:
                    self._show_canvas_context_menu(release_pos, global_pos)
                event.accept()
                return

            self._right_pan_candidate = False
            event.accept()
            return

        if event.button() == QtCore.Qt.LeftButton:
            if self._finish_selection_band(event.pos()):
                event.accept()
                return
            if self._selection_origin is None and self._selection_modifiers == QtCore.Qt.NoModifier:
                pass

        if event.button() == QtCore.Qt.LeftButton and scene is not None:
            item = self.itemAt(event.pos())

            # Connection drags must be resolved before the generic empty-canvas
            # release handler clears selection. The preview wire itself can also
            # be returned by itemAt(), so treat the active preview connection as
            # an empty-canvas release when no compatible target port was snapped.
            if scene.drag_connection:
                drag_source_port = getattr(scene, 'drag_source_port', None)
                drag_target_port = getattr(scene, 'drag_target_port', None)
                drag_preview_item = getattr(scene, 'drag_connection', None)
                release_on_empty_canvas = item is None or item is drag_preview_item
                if drag_target_port is None and drag_source_port is not None and release_on_empty_canvas:
                    scene.cancel_connection_drag()
                    self._show_graph_node_palette(
                        event.pos(),
                        event.globalPos(),
                        title="Insert Compatible Node",
                        filter_fn=lambda definition, port=drag_source_port: self._definition_has_compatible_port(port, definition),
                        connect_from_port=drag_source_port,
                    )
                else:
                    scene.end_connection_drag(item)
                event.accept()
                return

            if item is None and self._selection_origin is None and not (event.modifiers() & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)):
                scene.clearSelection()
                event.accept()
                return
            if scene.reconnect_connection:
                scene.end_endpoint_reconnect(item)
                event.accept()
                return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        scene = self.scene()
        editor = getattr(self, "editor", None)

        if event.matches(QtGui.QKeySequence.Undo) and editor is not None:
            editor.undo_stack.undo()
            event.accept()
            return

        if event.matches(QtGui.QKeySequence.Redo) and editor is not None:
            editor.undo_stack.redo()
            event.accept()
            return

        if event.matches(QtGui.QKeySequence.Copy) and editor is not None:
            if editor.copy():
                event.accept()
                return

        if event.matches(QtGui.QKeySequence.Cut) and editor is not None:
            if editor.cut():
                event.accept()
                return

        if event.matches(QtGui.QKeySequence.Paste) and editor is not None:
            if editor.paste():
                event.accept()
                return

        if event.key() == QtCore.Qt.Key_Space and editor is not None:
            self._show_graph_node_palette(self.viewport().rect().center(), self.mapToGlobal(self.viewport().rect().center()))
            event.accept()
            return

        if editor is not None and event.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier):
            align_map = {
                QtCore.Qt.Key_Left: 'left',
                QtCore.Qt.Key_Right: 'right',
                QtCore.Qt.Key_Up: 'top',
                QtCore.Qt.Key_Down: 'bottom',
            }
            alignment = align_map.get(event.key())
            if alignment and hasattr(editor, 'align_selected_nodes'):
                if editor.align_selected_nodes(alignment):
                    event.accept()
                    return

        if editor is not None and event.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
            if event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right) and hasattr(editor, 'distribute_selected_nodes'):
                if editor.distribute_selected_nodes('horizontal'):
                    event.accept()
                    return
            if event.key() in (QtCore.Qt.Key_Up, QtCore.Qt.Key_Down) and hasattr(editor, 'distribute_selected_nodes'):
                if editor.distribute_selected_nodes('vertical'):
                    event.accept()
                    return

        if event.key() == QtCore.Qt.Key_Escape:
            if self._selection_active or self._selection_origin is not None:
                self._selection_band.hide()
                self._selection_active = False
                self._selection_origin = None
                self._selection_modifiers = QtCore.Qt.NoModifier
                event.accept()
                return
            if scene and scene.drag_connection:
                scene.cancel_connection_drag()
                event.accept()
                return
            if scene and scene.reconnect_connection:
                scene.cancel_endpoint_reconnect()
                event.accept()
                return
            if editor is not None and hasattr(editor, "close_properties_dock") and editor.close_properties_dock():
                event.accept()
                return

        if event.key() == QtCore.Qt.Key_F:
            self.frame_selected_or_all()
            event.accept()
            return

        if event.key() == QtCore.Qt.Key_Home:
            self.frame_all_nodes()
            event.accept()
            return

        if event.key() == QtCore.Qt.Key_Delete and editor is not None:
            if editor.delete_selected_items():
                event.accept()
                return

        super().keyPressEvent(event)

    def _nearest_connection_item(self, view_pos, radius=12):
        scene = self.scene()
        if scene is None:
            return None
        scene_pos = self.mapToScene(view_pos)
        search_rect = QtCore.QRectF(
            scene_pos.x() - radius,
            scene_pos.y() - radius,
            radius * 2,
            radius * 2,
        )
        best_item = None
        best_dist = None
        for item in scene.items(search_rect, QtCore.Qt.IntersectsItemShape, QtCore.Qt.DescendingOrder):
            if isinstance(item, ConnectionPinItem):
                return item
            if isinstance(item, ConnectionItem):
                if item.endpoint_hit(scene_pos, tolerance=max(10.0, float(radius))) is not None:
                    continue
                seg_index = item.segment_at(scene_pos, tolerance=max(14.0, radius + 4.0))
                if seg_index is None:
                    continue
                pts = item.polyline_points()
                if not (0 <= seg_index < len(pts) - 1):
                    continue
                dist = _distance_to_segment(scene_pos, pts[seg_index], pts[seg_index + 1])
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    best_item = item
        return best_item

    def _node_item_for_view_item(self, item):
        """Return the owning NodeItem for a clicked graphics item, if any."""
        while item is not None:
            if isinstance(item, NodeItem):
                return item
            try:
                item = item.parentItem()
            except Exception:
                return None
        return None

    def _node_title_bar_hit(self, node_item, scene_pos):
        """True when a scene position lands in the node title bar.

        Container sub-graphs should open only from the title bar. Double-clicking
        the body is reserved for opening the properties panel.
        """
        if node_item is None:
            return False
        try:
            local_pos = node_item.mapFromScene(scene_pos)
            return QtCore.QRectF(0.0, 0.0, float(node_item.boundingRect().width()), 34.0).contains(local_pos)
        except Exception:
            return False

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            item = self.itemAt(event.pos())
            scene = self.scene()
            scene_pos = self.mapToScene(event.pos())
            if not isinstance(item, (ConnectionItem, ConnectionPinItem)):
                near_item = self._nearest_connection_item(event.pos(), radius=12)
                if near_item is not None:
                    item = near_item
            if isinstance(item, ConnectionPinItem):
                if scene is not None:
                    scene.remove_connection_pin(item.connection_item, item.index)
                event.accept()
                return
            if isinstance(item, ConnectionItem):
                if scene is not None:
                    if item.endpoint_hit(scene_pos, tolerance=12.0) is not None:
                        event.accept()
                        return
                    scene.clearSelection()
                    item.setSelected(True)
                    scene.add_connection_pin(item, scene_pos)
                event.accept()
                return

            node_item = self._node_item_for_view_item(item)
            if node_item is not None:
                editor = getattr(self, "editor", None)
                if editor is not None:
                    is_container = getattr(editor, 'is_subgraph_container_node', lambda _item: False)(node_item)
                    if is_container and self._node_title_bar_hit(node_item, scene_pos):
                        editor.open_subgraph_for_node(node_item)
                    elif getattr(editor, 'is_runtime_breakpoint_toggle_active', lambda: False)() and getattr(editor, 'node_supports_runtime_breakpoint', lambda _item: False)(node_item):
                        editor.toggle_node_breakpoint(node_item)
                    else:
                        editor.open_properties_for_node(node_item)
                event.accept()
                return

        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        if getattr(self, '_suppress_next_context_menu', False):
            self._suppress_next_context_menu = False
            event.accept()
            return
        item = self.itemAt(event.pos())
        node_item = self._node_item_for_view_item(item)
        editor = getattr(self, 'editor', None)
        if node_item is not None and editor is not None:
            menu = QtWidgets.QMenu(self)
            layout_actions = self._add_layout_actions_to_menu(menu) if self._selected_layout_item_count() >= 2 else []
            if layout_actions:
                menu.addSeparator()
            rename_action = menu.addAction('Rename Node')
            rename_action.setShortcut(QtGui.QKeySequence('F2'))
            save_template_action = menu.addAction('Save Selection as Template…')
            save_template_action.setEnabled(hasattr(editor, 'save_selection_as_template'))
            action = menu.addAction('Open Properties')
            dock = getattr(editor, 'dockProperties', None)
            already_open = bool(dock is not None and dock.isVisible())
            action.setEnabled(not already_open)
            chosen = menu.exec_(event.globalPos())
            if self._dispatch_layout_action(chosen, layout_actions):
                event.accept()
                return
            if chosen is rename_action and hasattr(editor, 'rename_node_via_dialog'):
                editor.rename_node_via_dialog(node_item)
            elif chosen is save_template_action and hasattr(editor, 'save_selection_as_template'):
                editor.save_selection_as_template()
            elif chosen is action and not already_open:
                editor.open_properties_for_node(node_item)
            event.accept()
            return
        self._show_canvas_context_menu(event.pos(), event.globalPos())
        event.accept()
