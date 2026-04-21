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

from PyQt5 import QtCore, QtGui, QtWidgets
from .constants import ZOOM_MIN, ZOOM_MAX, ZOOM_STEP, FIT_PADDING
from .definitions import NODE_REGISTRY, NodeDefinitionRegistry
from .graphics_items import NodeItem, ConnectionItem, PortItem, ConnectionPinItem, _distance_to_segment
from .commands import AddNodeCommand


class NodePalettePopup(QtWidgets.QDialog):
    def __init__(self, parent=None, registry=None, title="All Actions for this Graph"):
        super().__init__(parent, QtCore.Qt.Popup | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self.setObjectName('NoDENodePalettePopup')
        self.setMinimumSize(360, 460)
        self._chosen_definition = None
        self._registry = registry or NODE_REGISTRY
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
        layout.addWidget(self.tree, 1)

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
        self.move(global_pos)
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

    def _search_text(self):
        return self.search_edit.text().strip()

    def _definitions_by_category(self):
        query = self._search_text()
        if not query:
            return self._registry.grouped_definitions()

        grouped = {}
        for definition in self._registry.search(query):
            grouped.setdefault(definition.category, []).append(definition)
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
                leaf = QtWidgets.QTreeWidgetItem([definition.display_name])
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
        self._chosen_definition = definition
        self.accept()

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

        selected = scene.selectedItems()
        if selected:
            self.frame_items(selected)
            return

        graph_items = [
            item for item in scene.items()
            if isinstance(item, (NodeItem, ConnectionItem))
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
            return
        editor = getattr(self, "editor", None)
        if editor is not None and hasattr(editor, '_can_add_node_type'):
            if not editor._can_add_node_type(definition.type_id, show_feedback=True):
                return
        undo_stack = getattr(editor, "undo_stack", None)
        if undo_stack is not None:
            undo_stack.push(AddNodeCommand(
                self.scene(),
                definition.display_name,
                scene_pos,
                node_type=definition.type_id,
            ))
        else:
            self.scene().add_node(
                definition.display_name,
                scene_pos,
                node_type=definition.type_id,
            )

    def _show_graph_node_palette(self, local_pos, global_pos):
        scene_pos = self.mapToScene(local_pos)
        popup = NodePalettePopup(self, registry=self.node_registry(), title="All Actions for this Graph")
        popup.show_at(global_pos)
        if popup.exec_() == QtWidgets.QDialog.Accepted:
            self._spawn_node_definition(popup.chosen_definition(), scene_pos)

    def _show_node_context_menu(self, node_item, global_pos):
        editor = getattr(self, "editor", None)
        menu = QtWidgets.QMenu(self)
        menu.setToolTipsVisible(True)

        act_delete = menu.addAction("Delete")
        act_delete.setShortcut(QtGui.QKeySequence.Delete)
        act_cut = menu.addAction("Cut")
        act_cut.setShortcut(QtGui.QKeySequence.Cut)
        act_copy = menu.addAction("Copy")
        act_copy.setShortcut(QtGui.QKeySequence.Copy)
        act_duplicate = menu.addAction("Duplicate")
        act_duplicate.setShortcut(QtGui.QKeySequence("Ctrl+D"))
        act_break_links = menu.addAction("Break Node Links")
        menu.addSeparator()
        act_properties = menu.addAction("Open Properties")

        chosen = menu.exec_(global_pos)
        if chosen is None or editor is None:
            return
        if chosen is act_delete:
            editor.delete_selected_items()
        elif chosen is act_cut:
            editor.cut()
        elif chosen is act_copy:
            editor.copy()
        elif chosen is act_duplicate:
            if hasattr(editor, 'duplicate_selection'):
                editor.duplicate_selection()
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
        self._selection_origin = QtCore.QPoint(origin)
        self._selection_modifiers = modifiers
        self._selection_active = False
        self._selection_band.hide()

    def _update_selection_band(self, current_pos):
        rect = QtCore.QRect(self._selection_origin, current_pos).normalized()
        drag_distance = abs(rect.width()) + abs(rect.height())
        if not self._selection_active and drag_distance < self._selection_threshold:
            return False
        if not self._selection_active:
            self._selection_active = True
            self._selection_band.show()
        self._selection_band.setGeometry(rect)
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

        rect = QtCore.QRect(self._selection_origin, end_pos).normalized()
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
            if isinstance(item, (NodeItem, ConnectionItem, ConnectionPinItem)):
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
                if item.port_type == PortItem.OUTPUT:
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
                if isinstance(item, NodeItem):
                    if scene is not None and not item.isSelected():
                        scene.clearSelection()
                        item.setSelected(True)
                    self._show_node_context_menu(item, global_pos)
                else:
                    self._show_graph_node_palette(release_pos, global_pos)
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
            if item is None and self._selection_origin is None and not (event.modifiers() & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)):
                scene.clearSelection()
                event.accept()
                return
            if scene.drag_connection:
                scene.end_connection_drag(item)
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
            if isinstance(item, NodeItem):
                editor = getattr(self, "editor", None)
                if editor is not None:
                    if getattr(editor, 'is_runtime_breakpoint_toggle_active', lambda: False)() and getattr(editor, 'node_supports_runtime_breakpoint', lambda _item: False)(item):
                        editor.toggle_node_breakpoint(item)
                    else:
                        editor.open_properties_for_node(item)
                event.accept()
                return

        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        event.accept()
