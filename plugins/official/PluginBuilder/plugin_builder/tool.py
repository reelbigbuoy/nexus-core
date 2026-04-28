from __future__ import annotations

import json
import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nexus_workspace.framework import (
    NexusButton,
    NexusCheckBox,
    NexusComboBox,
    NexusFrame,
    NexusHierarchyView,
    NexusLabel,
    NexusListWidget,
    NexusProgressBar,
    NexusRadioButton,
    NexusScrollArea,
    NexusSection,
    NexusSlider,
    NexusSpinBox,
    NexusSplitter,
    NexusStackedWidget,
    NexusTabWidget,
    NexusTableEditor,
    NexusTableView,
    NexusTextEditor,
    NexusTextInput,
    QtCore,
    QtGui,
    QtWidgets,
)


@dataclass
class WidgetNode:
    uid: str
    widget_type: str
    object_name: str
    text: str = ""
    tooltip: str = ""
    x: int = 20
    y: int = 20
    width: int = 160
    height: int = 48
    parent_uid: Optional[str] = None
    children: List[str] = field(default_factory=list)
    locked: bool = False
    props: Dict[str, object] = field(default_factory=dict)


WIDGET_LIBRARY: List[dict] = [
    {"type": "Vertical Stack", "base": "vertical_stack", "category": "Layouts", "container": True, "layout": "vbox", "size": (420, 320)},
    {"type": "Horizontal Row", "base": "horizontal_row", "category": "Layouts", "container": True, "layout": "hbox", "size": (520, 180)},

    {"type": "Button", "base": "button", "category": "Inputs", "container": False, "size": (140, 34)},
    {"type": "Checkbox", "base": "checkbox", "category": "Inputs", "container": False, "size": (150, 26)},
    {"type": "Combo Box", "base": "combo_box", "category": "Inputs", "container": False, "size": (180, 28)},
    {"type": "Radio Button", "base": "radio_button", "category": "Inputs", "container": False, "size": (160, 26)},
    {"type": "Slider", "base": "slider", "category": "Inputs", "container": False, "size": (200, 28)},
    {"type": "Spinbox", "base": "spinbox", "category": "Inputs", "container": False, "size": (90, 28)},
    {"type": "Text Input", "base": "text_input", "category": "Inputs", "container": False, "size": (220, 28)},

    {"type": "Label", "base": "label", "category": "Display", "container": False, "size": (140, 24)},
    {"type": "Progress Bar", "base": "progress_bar", "category": "Display", "container": False, "size": (220, 24)},
    {"type": "Text Editor", "base": "text_editor", "category": "Display", "container": False, "size": (280, 180)},
    {"type": "Tooltip", "base": "tooltip", "category": "Display", "container": False, "size": (160, 24)},

    {"type": "Hierarchy View", "base": "hierarchy_view", "category": "Data Views", "container": False, "size": (240, 180)},
    {"type": "List View", "base": "list_view", "category": "Data Views", "container": False, "size": (220, 180)},
    {"type": "Table Editor", "base": "table_editor", "category": "Data Views", "container": False, "size": (320, 180)},
    {"type": "Table Viewer", "base": "table_viewer", "category": "Data Views", "container": False, "size": (320, 180)},

    {"type": "Context Menu", "base": "context_menu", "category": "Menus & Actions", "container": False, "size": (160, 90)},
    {"type": "Custom Toolbar", "base": "custom_toolbar", "category": "Menus & Actions", "container": True, "size": (320, 48)},
    {"type": "Menu", "base": "menu", "category": "Menus & Actions", "container": False, "size": (90, 24)},
    {"type": "Sub-Menu", "base": "sub_menu", "category": "Menus & Actions", "container": False, "size": (110, 24)},

    {"type": "Dialog Box", "base": "dialog_box", "category": "Containers", "container": True, "size": (360, 240)},
    {"type": "Frame", "base": "frame", "category": "Containers", "container": True, "size": (320, 220)},
    {"type": "Scroll Area", "base": "scroll_area", "category": "Containers", "container": True, "size": (320, 220)},
    {"type": "Stacked Widget", "base": "stacked_widget", "category": "Containers", "container": True, "size": (320, 220)},
    {"type": "Sub-Window", "base": "sub_window", "category": "Containers", "container": True, "size": (360, 240)},
    {"type": "Tab View", "base": "tab_view", "category": "Containers", "container": True, "size": (360, 240)},

    {"type": "Bar Graph", "base": "bar_graph", "category": "Charts", "container": False, "size": (300, 180)},
    {"type": "Line Graph", "base": "line_graph", "category": "Charts", "container": False, "size": (300, 180)},
    {"type": "Pie Graph", "base": "pie_graph", "category": "Charts", "container": False, "size": (260, 180)},
]

WIDGET_INDEX = {entry["type"]: entry for entry in WIDGET_LIBRARY}
CONTAINER_TYPES = {entry["type"] for entry in WIDGET_LIBRARY if entry["container"]}
CATEGORY_ORDER = ["Containers", "Inputs", "Display", "Data Views", "Menus & Actions", "Charts"]
LAYOUT_CONTAINER_TYPES = {entry["type"] for entry in WIDGET_LIBRARY if entry.get("layout")}
ROOT_UID = "__root__"
ROOT_OBJECT_NAME = "plugin_background_frame"
MIME_WIDGET = "application/x-pluginbuilder-widget"
MIME_NODE = "application/x-pluginbuilder-node"


def _event_pos(event):
    return event.position().toPoint() if hasattr(event, "position") else event.pos()

def _event_global_pos(event):
    return event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()

def _accept_drop(event, action=None):
    """Accept drag/drop with an explicit action so Qt does not keep the forbidden cursor."""
    if action is not None and hasattr(event, "setDropAction"):
        event.setDropAction(action)
    event.accept()

def _mime_text(event, mime_type):
    return bytes(event.mimeData().data(mime_type)).decode("utf-8")


class ToolboxTree(NexusHierarchyView):
    """Toolbox tree with explicit, deterministic QDrag creation.

    This avoids fragile item-view MIME behavior in wrapped Nexus tree widgets.
    Every toolbox drag now carries MIME_WIDGET directly.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self._press_pos = None
        self._press_item = None

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._press_pos = _event_pos(event)
            self._press_item = self.itemAt(self._press_pos)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & QtCore.Qt.LeftButton) or self._press_pos is None:
            super().mouseMoveEvent(event)
            return
        distance = (_event_pos(event) - self._press_pos).manhattanLength()
        if distance < QtWidgets.QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return
        item = self._press_item or self.currentItem()
        widget_type = item.data(0, QtCore.Qt.UserRole) if item is not None else None
        if not widget_type:
            return
        mime = QtCore.QMimeData()
        mime.setData(MIME_WIDGET, str(widget_type).encode("utf-8"))
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(QtCore.Qt.CopyAction)
        self._press_pos = None
        self._press_item = None


class HierarchyTree(NexusHierarchyView):
    structure_changed = QtCore.pyqtSignal()

    """Model-driven hierarchy tree reordering/nesting.

    This intentionally does NOT use Qt's built-in QTreeWidget drag/drop path.
    The previous item-view DnD path repeatedly produced the forbidden cursor
    because Qt rejected the drag before the Plugin Builder model could process
    the move. This class performs a controlled mouse-drag gesture and mutates
    the Plugin Builder node model on mouse release.
    """

    def __init__(self, builder, parent=None):
        super().__init__(parent)
        self.builder = builder
        self.setHeaderHidden(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(True)

        # Disable Qt item-view drag/drop completely. Hierarchy movement is
        # handled manually below so Qt cannot show the forbidden DnD cursor.
        self.setDragEnabled(False)
        # Keep Qt's built-in item-view reordering disabled, but allow external
        # toolbox drops so users can add widgets directly into the hierarchy.
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        self.setMouseTracking(True)

        self._press_pos = None
        self._press_item = None
        self._dragging_uid = None
        self._drag_active = False
        self._hover_target_uid = None
        self._hover_zone = None
        self._auto_expand_item = None
        self._auto_expand_timer = QtCore.QTimer(self)
        self._auto_expand_timer.setSingleShot(True)
        self._auto_expand_timer.timeout.connect(self._expand_hover_item)

    def _node_uid_from_item(self, item):
        return item.data(0, QtCore.Qt.UserRole) if item is not None else None

    def _drop_zone_for_pos(self, item, pos):
        if item is None:
            return "inside"
        rect = self.visualItemRect(item)
        if not rect.isValid() or rect.height() <= 0:
            return "inside"
        offset = pos.y() - rect.top()
        if offset < rect.height() * 0.25:
            return "before"
        if offset > rect.height() * 0.75:
            return "after"
        return "inside"

    def _normalize_drop_target(self, pos):
        item = self.itemAt(pos)
        target_uid = self._node_uid_from_item(item) if item is not None else ROOT_UID
        if not target_uid:
            target_uid = ROOT_UID
        zone = self._drop_zone_for_pos(item, pos)
        if item is None:
            target_uid = ROOT_UID
            zone = "inside"
        return target_uid, zone

    def _expand_hover_item(self):
        if self._auto_expand_item is not None:
            self.expandItem(self._auto_expand_item)

    def _update_auto_expand(self, item, zone):
        if item is not None and zone == "inside" and not item.isExpanded():
            if item is not self._auto_expand_item:
                self._auto_expand_item = item
                self._auto_expand_timer.start(500)
        else:
            self._auto_expand_item = None
            self._auto_expand_timer.stop()

    def _clear_drag_state(self):
        self._press_pos = None
        self._press_item = None
        self._dragging_uid = None
        self._drag_active = False
        self._hover_target_uid = None
        self._hover_zone = None
        self._auto_expand_item = None
        self._auto_expand_timer.stop()
        self.viewport().unsetCursor()
        self.viewport().update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._press_pos = _event_pos(event)
            self._press_item = self.itemAt(self._press_pos)
            self._dragging_uid = self._node_uid_from_item(self._press_item)
            self._drag_active = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & QtCore.Qt.LeftButton) or self._press_pos is None or not self._dragging_uid:
            super().mouseMoveEvent(event)
            return

        if self._dragging_uid == ROOT_UID:
            super().mouseMoveEvent(event)
            return

        distance = (_event_pos(event) - self._press_pos).manhattanLength()
        if not self._drag_active and distance < QtWidgets.QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        self._drag_active = True
        pos = _event_pos(event)
        item = self.itemAt(pos)
        target_uid, zone = self._normalize_drop_target(pos)
        self._hover_target_uid = target_uid
        self._hover_zone = zone
        self._update_auto_expand(item, zone)

        if self.builder.can_move_node_by_drop(self._dragging_uid, target_uid, zone):
            self.viewport().setCursor(QtCore.Qt.SizeAllCursor)
        else:
            self.viewport().setCursor(QtCore.Qt.ForbiddenCursor)
        self.viewport().update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self._drag_active and self._dragging_uid:
            pos = _event_pos(event)
            target_uid, zone = self._normalize_drop_target(pos)
            self.builder.move_node_by_drop(self._dragging_uid, target_uid, zone)
            self._clear_drag_state()
            event.accept()
            return
        self._clear_drag_state()
        super().mouseReleaseEvent(event)
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_WIDGET):
            _accept_drop(event, QtCore.Qt.CopyAction)
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_WIDGET):
            pos = _event_pos(event)
            item = self.itemAt(pos)
            target_uid, zone = self._normalize_drop_target(pos)
            self._hover_target_uid = target_uid
            self._hover_zone = zone
            self._update_auto_expand(item, zone)
            self.viewport().setCursor(QtCore.Qt.CrossCursor)
            self.viewport().update()
            _accept_drop(event, QtCore.Qt.CopyAction)
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._hover_target_uid = None
        self._hover_zone = None
        self.viewport().unsetCursor()
        self.viewport().update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(MIME_WIDGET):
            widget_type = _mime_text(event, MIME_WIDGET)
            target_uid, zone = self._normalize_drop_target(_event_pos(event))
            self.builder.add_widget_by_hierarchy_drop(widget_type, target_uid, zone)
            self._hover_target_uid = None
            self._hover_zone = None
            self.viewport().unsetCursor()
            self.viewport().update()
            _accept_drop(event, QtCore.Qt.CopyAction)
            return
        event.ignore()


    def leaveEvent(self, event):
        if not self._drag_active:
            self.viewport().unsetCursor()
        super().leaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._drag_active or not self._hover_target_uid or not self._hover_zone:
            return
        item = self._find_item_by_uid(self._hover_target_uid)
        painter = QtGui.QPainter(self.viewport())
        pen = QtGui.QPen(self.palette().color(QtGui.QPalette.Highlight), 2)
        painter.setPen(pen)
        if item is None:
            rect = self.viewport().rect().adjusted(8, 8, -8, -8)
            painter.drawRect(rect)
        else:
            rect = self.visualItemRect(item)
            if self._hover_zone == "before":
                y = rect.top()
                painter.drawLine(rect.left(), y, rect.right(), y)
            elif self._hover_zone == "after":
                y = rect.bottom()
                painter.drawLine(rect.left(), y, rect.right(), y)
            else:
                painter.drawRect(rect.adjusted(1, 1, -2, -2))
        painter.end()

    def _find_item_by_uid(self, uid):
        root = self.invisibleRootItem()
        queue = [root.child(i) for i in range(root.childCount())]
        while queue:
            item = queue.pop(0)
            if self._node_uid_from_item(item) == uid:
                return item
            for i in range(item.childCount()):
                queue.append(item.child(i))
        return None
class DesignerSurface(NexusFrame):
    widget_dropped = QtCore.pyqtSignal(str, QtCore.QPoint, object)
    empty_clicked = QtCore.pyqtSignal()
    resized = QtCore.pyqtSignal()

    def __init__(self, builder, parent=None, *, object_name="PluginBuilderSurface"):
        super().__init__(parent, object_name=object_name)
        self.builder = builder
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setMinimumSize(1100, 750)
        self._dock_target_uid = None
        self._dock_zone = None
        self.refresh_theme()

    def refresh_theme(self):
        pal = self.palette()
        base = pal.color(QtGui.QPalette.Base).name()
        alt = pal.color(QtGui.QPalette.AlternateBase).name()
        self.setStyleSheet(f"#{self.objectName()} {{ background:{base}; border:1px solid {alt}; border-radius:8px; }}")
        self.update()

    def _update_dock_preview(self, global_pos):
        target_item = self.builder.design_item_at_global(global_pos)
        if target_item is None or not target_item.can_host_children():
            target_item = self.builder.root_design_item
        if target_item is None:
            self._dock_target_uid = None
            self._dock_zone = None
        else:
            self._dock_target_uid = target_item.node.uid
            local = target_item.mapFromGlobal(global_pos)
            self._dock_zone = self.builder.dock_zone_for_item(target_item, local)
        self.update()
        return target_item, self._dock_zone

    def _clear_dock_preview(self):
        self._dock_target_uid = None
        self._dock_zone = None
        self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_WIDGET):
            self._update_dock_preview(self.mapToGlobal(_event_pos(event)))
            _accept_drop(event, QtCore.Qt.CopyAction)
            return
        if event.mimeData().hasFormat(MIME_NODE):
            self._update_dock_preview(self.mapToGlobal(_event_pos(event)))
            _accept_drop(event, QtCore.Qt.MoveAction)
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_WIDGET) or event.mimeData().hasFormat(MIME_NODE):
            self._update_dock_preview(self.mapToGlobal(_event_pos(event)))
            _accept_drop(event, QtCore.Qt.MoveAction if event.mimeData().hasFormat(MIME_NODE) else QtCore.Qt.CopyAction)
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._clear_dock_preview()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if not (event.mimeData().hasFormat(MIME_WIDGET) or event.mimeData().hasFormat(MIME_NODE)):
            event.ignore()
            return
        is_existing_node = event.mimeData().hasFormat(MIME_NODE)
        payload = _mime_text(event, MIME_NODE if is_existing_node else MIME_WIDGET)
        local_pos = _event_pos(event)
        global_pos = self.mapToGlobal(local_pos)
        target_item, zone = self._update_dock_preview(global_pos)
        parent_node = self.builder.nodes[ROOT_UID]
        drop_pos = local_pos
        if target_item is not None and target_item.can_host_children():
            parent_node = target_item.node
            drop_pos = target_item.child_host.mapFromGlobal(global_pos)
        else:
            drop_pos = self.builder.root_design_item.child_host.mapFromGlobal(global_pos)
        if is_existing_node:
            self.builder.move_node_with_dock(payload, parent_node.uid, zone or "center", pos=drop_pos)
        else:
            self.builder.add_widget_with_dock(payload, parent_node, zone or "center", drop_pos)
        self._clear_dock_preview()
        _accept_drop(event, QtCore.Qt.MoveAction if is_existing_node else QtCore.Qt.CopyAction)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.empty_clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._dock_target_uid or not self._dock_zone:
            return
        target = self.builder.previews.get(self._dock_target_uid)
        if target is None:
            return
        rect = QtCore.QRect(target.mapTo(self, QtCore.QPoint(0, 0)), target.size()).adjusted(2, 2, -2, -2)
        zone = self._dock_zone
        zone_rect = QtCore.QRect(rect)
        if zone == "left":
            zone_rect.setWidth(max(24, rect.width() // 3))
        elif zone == "right":
            zone_rect.setLeft(rect.right() - max(24, rect.width() // 3))
        elif zone == "top":
            zone_rect.setHeight(max(24, rect.height() // 3))
        elif zone == "bottom":
            zone_rect.setTop(rect.bottom() - max(24, rect.height() // 3))
        else:
            zone_rect = rect.adjusted(rect.width() // 4, rect.height() // 4, -rect.width() // 4, -rect.height() // 4)
        painter = QtGui.QPainter(self)
        color = self.palette().color(QtGui.QPalette.Highlight)
        fill = QtGui.QColor(color)
        fill.setAlpha(70)
        painter.fillRect(zone_rect, fill)
        pen = QtGui.QPen(color, 2)
        painter.setPen(pen)
        painter.drawRect(zone_rect)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()


class DesignItem(QtWidgets.QWidget):
    moved = QtCore.pyqtSignal(str)
    selected = QtCore.pyqtSignal(str)
    quick_action = QtCore.pyqtSignal(str, str)
    widget_dropped = QtCore.pyqtSignal(str, QtCore.QPoint, object)

    def __init__(self, builder, node: WidgetNode, parent_host: QtWidgets.QWidget):
        super().__init__(parent_host)
        self.builder = builder
        self.node = node
        self._drag_origin = None
        self._start_pos = None
        self.live_widget = None
        self.child_host = None
        self._title_label = None
        self.setObjectName("PluginBuilderDesignItem")
        # DesignItem is editor chrome only; it must not paint a background or
        # alter live widget styling.
        self.setAttribute(QtCore.Qt.WA_StyledBackground, False)
        self._is_selected = False
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self.setAcceptDrops(True)
        self.setGeometry(node.x, node.y, node.width, node.height)
        # Layout-managed items must let the parent Qt layout size them.
        # Freeform/legacy items keep explicit geometry.
        if builder._is_layout_managed(node.uid) or (node.widget_type in LAYOUT_CONTAINER_TYPES and bool(node.props.get("fill_parent", True))):
            self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            self.setMinimumSize(40, 40)
        else:
            self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setMouseTracking(True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.live_widget, self.child_host = self.builder.make_live_widget(node.widget_type, node.text, node.tooltip, parent=self, props=node.props)
        self.live_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.live_widget, 1)
        layout.setStretch(0, 1)
        self._install_handlers(self.live_widget)
        self.refresh_theme()
        self.set_selected(False)
        self.show()

    def _install_handlers(self, widget):
        if widget is None:
            return
        widget.setAcceptDrops(True)
        widget.installEventFilter(self)
        for child in widget.findChildren(QtWidgets.QWidget):
            child.setAcceptDrops(True)
            child.installEventFilter(self)

    def _is_interactive_child(self, watched):
        if watched is self:
            return False
        interactive_types = (
            QtWidgets.QAbstractButton,
            QtWidgets.QAbstractSpinBox,
            QtWidgets.QComboBox,
            QtWidgets.QLineEdit,
            QtWidgets.QPlainTextEdit,
            QtWidgets.QTextEdit,
            QtWidgets.QAbstractItemView,
            QtWidgets.QSlider,
        )
        return isinstance(watched, interactive_types)

    def refresh_theme(self):
        pal = self.palette()
        highlight = pal.color(QtGui.QPalette.Highlight).name()
        self._selected_border = highlight

    def can_host_children(self):
        return self.node.widget_type in CONTAINER_TYPES and self.child_host is not None

    def set_selected(self, selected: bool):
        """Draw builder selection chrome without cascading styles into preview widgets."""
        self._is_selected = bool(selected and self.node.uid != ROOT_UID and not getattr(self.builder, "_preview_mode", False))
        self.update()

    def set_preview_mode(self, enabled: bool):
        enabled = bool(enabled)
        self.setAcceptDrops(not enabled)
        self.set_selected(False if enabled else self.builder.selected_uid == self.node.uid)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not getattr(self, "_is_selected", False):
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        pen = QtGui.QPen(QtGui.QColor(getattr(self, "_selected_border", "#71b7ff")), 2)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 6, 6)
        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.live_widget is not None:
            self.live_widget.setGeometry(self.rect())
        if self.child_host is not None and self.node.widget_type == "Frame" and self.child_host is not self.live_widget:
            pad = self.builder._effective_frame_padding(self.node.props)
            self.child_host.setGeometry(pad, pad, max(40, self.width() - (pad * 2)), max(40, self.height() - (pad * 2)))
        elif self.child_host is not None and self.node.widget_type == "Sub-Window":
            self.child_host.setGeometry(8, 28, max(40, self.width() - 16), max(40, self.height() - 36))
        elif self.child_host is not None and self.node.widget_type == "Dialog Box":
            self.child_host.setGeometry(10, 34, max(40, self.width() - 20), max(40, self.height() - 44))
        self.builder._clamp_freeform_children(self.node.uid)

    def refresh(self):
        # Freeform items own their geometry. Layout-managed items are sized by
        # their parent layout, so do not reset them back to stale node geometry.
        if not self.builder._is_layout_managed(self.node.uid):
            self.setGeometry(self.node.x, self.node.y, self.node.width, self.node.height)
        self.builder.apply_live_properties(self.live_widget, self.node)
        self.builder._clamp_freeform_children(self.node.uid)

    def _begin_drag(self, global_pos):
        self._drag_origin = global_pos
        self._start_pos = self.pos()
        self.selected.emit(self.node.uid)

    def _handle_mouse_press(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.node.uid != ROOT_UID:
            self._begin_drag(event.globalPos())
            event.accept()
            return True
        return False

    def _handle_mouse_move(self, event):
        if self.node.uid == ROOT_UID or self._drag_origin is None or not (event.buttons() & QtCore.Qt.LeftButton):
            return False
        offset = event.globalPos() - self._drag_origin
        new_pos = self._start_pos + offset
        self.move(max(0, new_pos.x()), max(0, new_pos.y()))
        self.node.x = self.x()
        self.node.y = self.y()
        self.moved.emit(self.node.uid)
        event.accept()
        return True

    def _handle_mouse_release(self, event):
        self._drag_origin = None
        self._start_pos = None
        return False

    def mousePressEvent(self, event):
        if self._handle_mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._handle_mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._handle_mouse_release(event)
        super().mouseReleaseEvent(event)

    def _handle_drop_event(self, event, watched=None):
        if not (event.mimeData().hasFormat(MIME_WIDGET) or event.mimeData().hasFormat(MIME_NODE)):
            return False
        if not self.can_host_children():
            return False
        is_existing_node = event.mimeData().hasFormat(MIME_NODE)
        payload = bytes(event.mimeData().data(MIME_NODE if is_existing_node else MIME_WIDGET)).decode("utf-8")
        source_pos = _event_pos(event)
        global_pos = watched.mapToGlobal(source_pos) if watched is not None else _event_global_pos(event)
        local_pos = self.child_host.mapFromGlobal(global_pos)
        zone = self.builder.dock_zone_for_item(self, self.mapFromGlobal(global_pos))
        if is_existing_node:
            self.builder.move_node_with_dock(payload, self.node.uid, zone, pos=local_pos)
        else:
            self.builder.add_widget_with_dock(payload, self.node, zone, local_pos)
        if hasattr(self.builder, "surface"):
            self.builder.surface._clear_dock_preview()
        _accept_drop(event, QtCore.Qt.MoveAction if is_existing_node else QtCore.Qt.CopyAction)
        return True

    def dragEnterEvent(self, event):
        if (event.mimeData().hasFormat(MIME_WIDGET) or event.mimeData().hasFormat(MIME_NODE)) and self.can_host_children():
            _accept_drop(event, QtCore.Qt.MoveAction if event.mimeData().hasFormat(MIME_NODE) else QtCore.Qt.CopyAction)
            return
        event.ignore()

    def dragMoveEvent(self, event):
        if (event.mimeData().hasFormat(MIME_WIDGET) or event.mimeData().hasFormat(MIME_NODE)) and self.can_host_children():
            if hasattr(self.builder, "surface"):
                self.builder.surface._update_dock_preview(self.mapToGlobal(_event_pos(event)))
            _accept_drop(event, QtCore.Qt.MoveAction if event.mimeData().hasFormat(MIME_NODE) else QtCore.Qt.CopyAction)
            return
        event.ignore()

    def dropEvent(self, event):
        if self._handle_drop_event(event):
            return
        super().dropEvent(event)

    def contextMenuEvent(self, event):
        if self.node.uid == ROOT_UID:
            return
        self.selected.emit(self.node.uid)
        menu = QtWidgets.QMenu(self)
        bring_front = menu.addAction("Bring to Front")
        send_back = menu.addAction("Send to Back")
        if self.builder._is_layout_managed(self.node.uid):
            bring_front.setEnabled(False)
            send_back.setEnabled(False)
        menu.addSeparator()
        cut_action = menu.addAction("Cut")
        copy_action = menu.addAction("Copy")
        paste_action = menu.addAction("Paste")
        delete_action = menu.addAction("Delete")
        group_action = None
        if self.builder.selected_uid and self.builder.selected_uid != self.node.uid and self.can_host_children():
            menu.addSeparator()
            group_action = menu.addAction("Group Selected Into This")
        if not self.builder.has_clipboard():
            paste_action.setEnabled(False)
        chosen = menu.exec_(event.globalPos())
        if chosen == bring_front:
            self.quick_action.emit(self.node.uid, "bring_to_front")
        elif chosen == send_back:
            self.quick_action.emit(self.node.uid, "send_to_back")
        elif chosen == cut_action:
            self.quick_action.emit(self.node.uid, "cut")
        elif chosen == copy_action:
            self.quick_action.emit(self.node.uid, "copy")
        elif chosen == paste_action:
            self.quick_action.emit(self.node.uid, "paste_into")
        elif chosen == delete_action:
            self.quick_action.emit(self.node.uid, "delete")
        elif group_action is not None and chosen == group_action:
            self.quick_action.emit(self.node.uid, "group_selected_here")

    def eventFilter(self, watched, event):
        t = event.type()
        if getattr(self.builder, "_preview_mode", False):
            return False
        # Live controls inside the design wrapper must keep their native Qt behavior
        # (text editing, table selection, context menus, keyboard shortcuts, etc.).
        # The DesignItem still accepts drops on those widgets, but it no longer
        # steals mouse/context events that belong to the control itself.
        if self._is_interactive_child(watched) and t in {
            QtCore.QEvent.MouseButtonPress,
            QtCore.QEvent.MouseButtonDblClick,
            QtCore.QEvent.MouseMove,
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QEvent.ContextMenu,
            QtCore.QEvent.KeyPress,
            QtCore.QEvent.KeyRelease,
            QtCore.QEvent.Wheel,
        }:
            self.selected.emit(self.node.uid)
            return False
        if t == QtCore.QEvent.MouseButtonPress:
            return self._handle_mouse_press(event)
        if t == QtCore.QEvent.MouseMove:
            return self._handle_mouse_move(event)
        if t == QtCore.QEvent.MouseButtonRelease:
            self._handle_mouse_release(event)
            return False
        if t == QtCore.QEvent.DragEnter:
            if (event.mimeData().hasFormat(MIME_WIDGET) or event.mimeData().hasFormat(MIME_NODE)) and self.can_host_children():
                _accept_drop(event, QtCore.Qt.MoveAction if event.mimeData().hasFormat(MIME_NODE) else QtCore.Qt.CopyAction)
                return True
        if t == QtCore.QEvent.DragMove:
            if (event.mimeData().hasFormat(MIME_WIDGET) or event.mimeData().hasFormat(MIME_NODE)) and self.can_host_children():
                if hasattr(self.builder, "surface") and hasattr(watched, "mapToGlobal"):
                    self.builder.surface._update_dock_preview(watched.mapToGlobal(_event_pos(event)))
                _accept_drop(event, QtCore.Qt.MoveAction if event.mimeData().hasFormat(MIME_NODE) else QtCore.Qt.CopyAction)
                return True
        if t == QtCore.QEvent.Drop:
            if self._handle_drop_event(event, watched if hasattr(watched, "mapToGlobal") else None):
                return True
        if t == QtCore.QEvent.ContextMenu:
            self.contextMenuEvent(event)
            return True
        return False


class PluginBuilderWorkbench(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes: Dict[str, WidgetNode] = {}
        self.previews: Dict[str, DesignItem] = {}
        self.root_design_item: Optional[DesignItem] = None
        self.selected_uid: Optional[str] = None
        self._uid_counter = 0
        self._loading = False
        self.widget_prop_form = None
        self.widget_prop_host = None
        self.widget_prop_editors = {}
        self._history = []
        self._history_index = -1
        self._clipboard = None
        self._suspend_history = False
        self._preview_mode = False
        self._preview_refresh_queued = False
        self._pending_preview_refresh_uid = None
        self._build_ui()
        self._wire_events()
        self._ensure_root_node()
        self.rebuild_canvas()
        self.rebuild_tree()
        self.select_node(ROOT_UID)
        self._push_history()
        QtCore.QTimer.singleShot(0, self._sync_root_to_surface)

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        top_bar = QtWidgets.QHBoxLayout()
        self.plugin_name_edit = NexusTextInput(parent=self, placeholder="Plugin name")
        self.export_button = NexusButton("Export Plugin", self, variant="primary")
        self.remove_button = NexusButton("Remove Selected", self)
        self.preview_mode_check = NexusCheckBox("Preview Mode", self)
        self.preview_mode_check.setToolTip("Hide builder chrome and interact with the plugin as a user would.")
        top_bar.addWidget(NexusLabel("Plugin Name", self), 0)
        top_bar.addWidget(self.plugin_name_edit, 1)
        top_bar.addWidget(self.preview_mode_check, 0)
        top_bar.addWidget(self.export_button, 0)
        top_bar.addWidget(self.remove_button, 0)
        root.addLayout(top_bar)

        splitter = NexusSplitter(QtCore.Qt.Horizontal, self)
        root.addWidget(splitter, 1)

        toolbox_section = NexusSection("Widget Toolbox", self)
        self.toolbox = ToolboxTree(self)
        self._populate_toolbox()
        toolbox_section.body_layout().addWidget(self.toolbox, 1)
        self.add_selected_button = NexusButton("Add Selected Widget", self)
        toolbox_section.body_layout().addWidget(self.add_selected_button, 0)
        splitter.addWidget(toolbox_section)

        middle = NexusSplitter(QtCore.Qt.Vertical, self)
        splitter.addWidget(middle)

        tree_section = NexusSection("Hierarchy", self)
        self.tree = HierarchyTree(self)
        tree_section.body_layout().addWidget(self.tree, 1)
        middle.addWidget(tree_section)

        sandbox_section = NexusSection("Layout Editor", self)
        self.surface = DesignerSurface(self, self)
        scroll = NexusScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.surface)
        sandbox_section.body_layout().addWidget(scroll, 1)
        middle.addWidget(sandbox_section)
        middle.setSizes([240, 560])

        properties_section = NexusSection("Selected Widget", self)
        form = QtWidgets.QFormLayout()
        self.object_name_value = NexusLabel("-", self)
        self.widget_type_value = NexusLabel("-", self)
        self.text_edit = NexusTextInput(parent=self, placeholder="Display text")
        self.tooltip_edit = NexusTextInput(parent=self, placeholder="Tooltip")
        self.x_spin = NexusSpinBox(self)
        self.y_spin = NexusSpinBox(self)
        self.w_spin = NexusSpinBox(self)
        self.h_spin = NexusSpinBox(self)
        for spin in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            spin.setRange(0, 5000)
        form.addRow("Object Name", self.object_name_value)
        form.addRow("Widget Type", self.widget_type_value)
        form.addRow("Text", self.text_edit)
        form.addRow("Tooltip", self.tooltip_edit)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("Width", self.w_spin)
        form.addRow("Height", self.h_spin)
        properties_section.body_layout().addLayout(form)
        self.apply_button = NexusButton("Apply Properties", self)
        properties_section.body_layout().addWidget(self.apply_button, 0)
        properties_section.body_layout().addWidget(NexusLabel("Widget Properties", self), 0)
        self.widget_prop_host = QtWidgets.QWidget(self)
        self.widget_prop_form = QtWidgets.QFormLayout(self.widget_prop_host)
        self.widget_prop_form.setContentsMargins(0, 0, 0, 0)
        self.widget_prop_form.setSpacing(6)
        properties_section.body_layout().addWidget(self.widget_prop_host, 0)
        self.log = NexusTextEditor(self)
        self.log.setReadOnly(True)
        properties_section.body_layout().addWidget(self.log, 1)
        splitter.addWidget(properties_section)
        splitter.setSizes([240, 900, 300])

    def _wire_events(self):
        self.add_selected_button.clicked.connect(self.add_selected_widget)
        self.export_button.clicked.connect(self.export_plugin)
        self.remove_button.clicked.connect(self.remove_selected)
        self.apply_button.clicked.connect(self.apply_properties)
        self.preview_mode_check.toggled.connect(self.set_preview_mode)
        self.tree.currentItemChanged.connect(self._on_tree_selection_changed)
        self.tree.structure_changed.connect(self.rebuild_structure_from_tree)
        self.surface.widget_dropped.connect(self.add_widget_from_drop)
        self.surface.empty_clicked.connect(self.clear_selection)
        self.surface.resized.connect(self._sync_root_to_surface)
        self.toolbox.itemDoubleClicked.connect(self._on_toolbox_double_clicked)
        self.text_edit.textChanged.connect(self._sync_selected_text_from_editor)
        self.tooltip_edit.textChanged.connect(self._sync_selected_tooltip_from_editor)
        self.x_spin.valueChanged.connect(lambda value: self._sync_selected_geometry())
        self.y_spin.valueChanged.connect(lambda value: self._sync_selected_geometry())
        self.w_spin.valueChanged.connect(lambda value: self._sync_selected_geometry())
        self.h_spin.valueChanged.connect(lambda value: self._sync_selected_geometry())
        QtWidgets.QShortcut(QtGui.QKeySequence.Undo, self, activated=self.undo)
        QtWidgets.QShortcut(QtGui.QKeySequence.Redo, self, activated=self.redo)
        QtWidgets.QShortcut(QtGui.QKeySequence.Copy, self, activated=self.copy_selected)
        QtWidgets.QShortcut(QtGui.QKeySequence.Cut, self, activated=self.cut_selected)
        QtWidgets.QShortcut(QtGui.QKeySequence.Paste, self, activated=self.paste_selected)
        QtWidgets.QShortcut(QtGui.QKeySequence.Delete, self, activated=self.remove_selected)


    def set_preview_mode(self, enabled: bool, rebuild: bool = False):
        """Toggle between editable builder chrome and user-facing preview."""
        self._preview_mode = bool(enabled)
        if hasattr(self, "preview_mode_check") and self.preview_mode_check.isChecked() != self._preview_mode:
            self.preview_mode_check.blockSignals(True)
            self.preview_mode_check.setChecked(self._preview_mode)
            self.preview_mode_check.blockSignals(False)
        for preview in self.previews.values():
            preview.set_preview_mode(self._preview_mode)
        self.remove_button.setEnabled(not self._preview_mode)
        self.apply_button.setEnabled(not self._preview_mode)
        self.surface._clear_dock_preview()
        self.surface.setAcceptDrops(not self._preview_mode)
        self.tree.setEnabled(not self._preview_mode)
        self.toolbox.setEnabled(not self._preview_mode)
        self.add_selected_button.setEnabled(not self._preview_mode)
        if rebuild:
            self.rebuild_canvas()

    def _populate_toolbox(self):
        self.toolbox.clear()
        for category in CATEGORY_ORDER:
            # Layouts are now exposed as container properties rather than
            # draggable widgets. Keep the internal layout node types for
            # backwards compatibility, but do not show them in the toolbox.
            members = sorted(
                [entry for entry in WIDGET_LIBRARY if entry["category"] == category and not entry.get("layout")],
                key=lambda entry: entry["type"],
            )
            if not members:
                continue
            category_item = QtWidgets.QTreeWidgetItem([category])
            flags = category_item.flags()
            category_item.setFlags(flags & ~QtCore.Qt.ItemIsDragEnabled)
            self.toolbox.addTopLevelItem(category_item)
            for entry in members:
                child = QtWidgets.QTreeWidgetItem([entry["type"]])
                child.setData(0, QtCore.Qt.UserRole, entry["type"])
                child.setFlags(child.flags() | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                category_item.addChild(child)
            category_item.setExpanded(True)

    def _ensure_root_node(self):
        if ROOT_UID not in self.nodes:
            self.nodes[ROOT_UID] = WidgetNode(
                uid=ROOT_UID,
                widget_type="Frame",
                object_name=ROOT_OBJECT_NAME,
                text="",
                tooltip="",
                x=0,
                y=0,
                width=1000,
                height=680,
                parent_uid=None,
                locked=True,
            )

    def _sync_root_to_surface(self):
        if ROOT_UID not in self.nodes:
            return
        node = self.nodes[ROOT_UID]
        width = max(200, self.surface.width())
        height = max(200, self.surface.height())
        node.x = 0
        node.y = 0
        node.width = width
        node.height = height
        preview = self.previews.get(ROOT_UID)
        if preview is not None:
            preview.setGeometry(0, 0, width, height)
            preview.refresh()
            if preview.live_widget is not None:
                preview.live_widget.setGeometry(0, 0, width, height)
        self.update_properties_panel()

    def _next_uid(self):
        self._uid_counter += 1
        return f"node_{self._uid_counter:04d}"

    def _default_text_for_type(self, widget_type):
        return {
            "Label": "Label",
            "Button": "Button",
            "Checkbox": "Checkbox",
            "Radio Button": "Option",
            "Combo Box": "Option 1, Option 2",
            "Tooltip": "Tooltip text",
            "Menu": "Menu",
            "Sub-Menu": "Sub-Menu",
            "Context Menu": "Action 1\\nAction 2",
            "Custom Toolbar": "Toolbar",
            "Dialog Box": "Dialog",
            "Sub-Window": "Sub-Window",
            "Tab View": "Tab View",
            "Stacked Widget": "Stacked Widget",
            "Scroll Area": "Scroll Area",
            "Bar Graph": "Bar Graph",
            "Pie Graph": "Pie Graph",
            "Line Graph": "Line Graph",
            "Vertical Stack": "Vertical Stack",
            "Horizontal Row": "Horizontal Row",
        }.get(widget_type, widget_type)

    def _default_props_for_type(self, widget_type):
        defaults = {
            "Frame": {"layout": "Freeform", "frame_style": "Bordered", "spacing": 8, "margin": 8, "stretch": 1},
            "Text Input": {"placeholder": "Enter text"},
            "Combo Box": {"items": "Option 1, Option 2"},
            "Slider": {"minimum": 0, "maximum": 100, "value": 35, "orientation": "Horizontal"},
            "Spinbox": {"minimum": 0, "maximum": 100, "value": 5},
            "Progress Bar": {"minimum": 0, "maximum": 100, "value": 70},
            "List View": {"items": "Item 1\nItem 2\nItem 3"},
            "Hierarchy View": {"items": "Root\n  Child"},
            "Table Viewer": {"rows": 3, "columns": 3, "corner_style": "Square", "fill_cells": True, "multi_select": True, "enable_clipboard": True, "enable_context_menu": True, "allow_structure_edit": False, "editable_cells": False},
            "Table Editor": {"rows": 3, "columns": 3, "corner_style": "Square", "fill_cells": True, "multi_select": True, "enable_clipboard": True, "enable_context_menu": True, "allow_structure_edit": True, "editable_cells": True},
            "Tab View": {"tabs": "Page 1"},
            "Text Editor": {"placeholder": "Text editor preview", "show_toolbar": False, "enable_context_menu": True, "enable_clipboard": True, "enable_formatting": True, "enable_search": True, "word_wrap": True, "read_only": False, "auto_indent": False, "tab_width": 4, "font_size": 10, "alignment": "Left"},
            "Context Menu": {"actions": "Action 1\nAction 2"},
            "Button": {"style": "Primary"},
            "Vertical Stack": {"spacing": 8, "margin": 8, "fill_parent": True, "stretch": 1},
            "Horizontal Row": {"spacing": 8, "margin": 8, "fill_parent": True, "stretch": 1},
        }
        return dict(defaults.get(widget_type, {}))

    def _serialize_nodes(self):
        return [copy.deepcopy(node.__dict__) for node in self.nodes.values()]

    def _restore_snapshot(self, snapshot):
        self._suspend_history = True
        try:
            self.nodes.clear()
            for raw in snapshot.get("nodes", []):
                self.nodes[raw["uid"]] = WidgetNode(**copy.deepcopy(raw))
            self._uid_counter = int(snapshot.get("uid_counter", 0))
            self.selected_uid = snapshot.get("selected_uid") or ROOT_UID
            self.plugin_name_edit.setText(snapshot.get("plugin_name", self.plugin_name_edit.text()))
            self.rebuild_canvas()
            self.rebuild_tree()
            self.select_node(self.selected_uid if self.selected_uid in self.nodes else ROOT_UID)
        finally:
            self._suspend_history = False

    def _push_history(self):
        if self._suspend_history:
            return
        snapshot = {
            "plugin_name": self.plugin_name_edit.text(),
            "uid_counter": self._uid_counter,
            "selected_uid": self.selected_uid,
            "nodes": self._serialize_nodes(),
        }
        if self._history_index >= 0 and self._history[self._history_index] == snapshot:
            return
        self._history = self._history[: self._history_index + 1]
        self._history.append(snapshot)
        self._history_index = len(self._history) - 1

    def undo(self):
        if self._history_index <= 0:
            return
        self._history_index -= 1
        self._restore_snapshot(self._history[self._history_index])

    def redo(self):
        if self._history_index + 1 >= len(self._history):
            return
        self._history_index += 1
        self._restore_snapshot(self._history[self._history_index])

    def has_clipboard(self):
        return self._clipboard is not None

    def _copy_node_payload(self, uid):
        node = self.nodes.get(uid)
        if node is None or uid == ROOT_UID:
            return None
        def walk(node_uid):
            current = self.nodes[node_uid]
            return {
                "node": copy.deepcopy(current.__dict__),
                "children": [walk(child_uid) for child_uid in current.children],
            }
        return walk(uid)

    def copy_selected(self):
        if self.selected_uid and self.selected_uid != ROOT_UID:
            self._clipboard = self._copy_node_payload(self.selected_uid)

    def cut_selected(self):
        if self.selected_uid and self.selected_uid != ROOT_UID:
            self.copy_selected()
            self.remove_selected()

    def _paste_payload(self, payload, parent_uid, pos=None):
        raw = copy.deepcopy(payload["node"])
        old_uid = raw["uid"]
        new_uid = self._next_uid()
        raw["uid"] = new_uid
        raw["children"] = []
        raw["parent_uid"] = parent_uid
        if pos is not None:
            raw["x"] = max(0, pos.x())
            raw["y"] = max(0, pos.y())
        else:
            raw["x"] = int(raw.get("x", 0)) + 24
            raw["y"] = int(raw.get("y", 0)) + 24
        node = WidgetNode(**raw)
        self.nodes[new_uid] = node
        self.nodes[parent_uid].children.append(new_uid)
        for child in payload.get("children", []):
            # Recursive paste appends each child to the new parent exactly once.
            # The previous implementation appended here *and* in the recursive
            # call, which duplicated nested children in the model/tree.
            self._paste_payload(child, new_uid)
        return new_uid

    def paste_selected(self):
        if not self._clipboard:
            return
        target_uid = self.selected_uid or ROOT_UID
        target = self.nodes.get(target_uid, self.nodes[ROOT_UID])
        parent_uid = target_uid if target.widget_type in CONTAINER_TYPES else (target.parent_uid or ROOT_UID)
        new_uid = self._paste_payload(self._clipboard, parent_uid)
        self.renumber_object_names()
        self.rebuild_canvas()
        self._sync_root_to_surface()
        self.rebuild_tree()
        self.select_node(new_uid)
        self._push_history()

    def _on_toolbox_double_clicked(self, item, column=0):
        widget_type = item.data(0, QtCore.Qt.UserRole)
        if widget_type:
            self.add_widget(str(widget_type), parent_node=self.nodes[ROOT_UID], pos=QtCore.QPoint(24, 24))

    def add_selected_widget(self):
        item = self.toolbox.currentItem()
        if item is not None:
            widget_type = item.data(0, QtCore.Qt.UserRole)
            if widget_type:
                self.add_widget(str(widget_type), parent_node=self.nodes[ROOT_UID], pos=QtCore.QPoint(24, 24))

    def add_widget_from_drop(self, widget_type, pos, parent_node=None):
        self.add_widget(widget_type, parent_node=parent_node or self.nodes[ROOT_UID], pos=pos)

    def dock_zone_for_item(self, item, local_pos):
        if item is None:
            return "center"
        w = max(1, item.width())
        h = max(1, item.height())
        x = max(0, min(w, local_pos.x()))
        y = max(0, min(h, local_pos.y()))
        left = x
        right = w - x
        top = y
        bottom = h - y
        edge = min(left, right, top, bottom)
        center_margin_x = w * 0.28
        center_margin_y = h * 0.28
        if center_margin_x < x < w - center_margin_x and center_margin_y < y < h - center_margin_y:
            return "center"
        if edge == left:
            return "left"
        if edge == right:
            return "right"
        if edge == top:
            return "top"
        return "bottom"

    def _ensure_layout_node(self, parent_uid, orientation):
        layout_type = "Horizontal Row" if orientation == "horizontal" else "Vertical Stack"
        layout_uid = self._single_layout_child(parent_uid)
        if layout_uid and self.nodes[layout_uid].widget_type == layout_type:
            return layout_uid
        # Preserve an explicit existing layout. Edge drops should never
        # silently flip a container from vertical to horizontal, or vice versa.
        if layout_uid and self.nodes[layout_uid].widget_type in LAYOUT_CONTAINER_TYPES:
            return layout_uid
        layout_uid = self._next_uid()
        layout_node = WidgetNode(
            uid=layout_uid,
            widget_type=layout_type,
            object_name="",
            text=layout_type,
            x=0,
            y=0,
            width=max(40, self.nodes[parent_uid].width),
            height=max(40, self.nodes[parent_uid].height),
            parent_uid=parent_uid,
            props=self._default_props_for_type(layout_type),
        )
        existing = list(self.nodes[parent_uid].children)
        self.nodes[layout_uid] = layout_node
        self.nodes[parent_uid].children = [layout_uid]
        layout_node.children = []
        for child_uid in existing:
            if child_uid == layout_uid:
                continue
            self.nodes[child_uid].parent_uid = layout_uid
            layout_node.children.append(child_uid)
        return layout_uid

    def _insert_into_layout(self, uid, parent_uid, zone):
        orientation = "horizontal" if zone in {"left", "right"} else "vertical"
        layout_uid = self._ensure_layout_node(parent_uid, orientation)
        layout_node = self.nodes[layout_uid]
        siblings = layout_node.children
        if uid in siblings:
            siblings.remove(uid)
        self.nodes[uid].parent_uid = layout_uid

        # Respect the actual orientation once a layout exists. For an existing
        # Vertical Stack, left/right drops append to the stack instead of
        # changing it into a Horizontal Row; for an existing Horizontal Row,
        # top/bottom drops append to the row instead of changing it into a
        # Vertical Stack.
        if layout_node.widget_type == "Horizontal Row" and zone == "left":
            insert_index = 0
        elif layout_node.widget_type == "Vertical Stack" and zone == "top":
            insert_index = 0
        else:
            insert_index = len(siblings)
        siblings.insert(insert_index, uid)
        self.nodes[uid].props.setdefault("stretch", 1)
        return layout_uid

    def add_widget_with_dock(self, widget_type, parent_node, zone, pos):
        if zone == "center":
            self.add_widget(widget_type, parent_node=parent_node or self.nodes[ROOT_UID], pos=pos)
            return
        spec = WIDGET_INDEX.get(widget_type)
        if spec is None:
            return
        uid = self._next_uid()
        width, height = spec["size"]
        requested_parent_uid = parent_node.uid if parent_node else ROOT_UID
        node = WidgetNode(
            uid=uid,
            widget_type=widget_type,
            object_name="",
            text=self._default_text_for_type(widget_type),
            tooltip="",
            x=max(0, pos.x()),
            y=max(0, pos.y()),
            width=width,
            height=height,
            parent_uid=requested_parent_uid,
            props=self._default_props_for_type(widget_type),
        )
        node.props.setdefault("stretch", 1)
        self.nodes[uid] = node
        self._insert_into_layout(uid, requested_parent_uid, zone)
        self.renumber_object_names()
        self.rebuild_canvas()
        self.rebuild_tree()
        self.select_node(uid)
        self._push_history()

    def move_node_with_dock(self, uid, parent_uid, zone, pos=None):
        if zone == "center":
            return self.move_node_to_parent(uid, parent_uid, pos=pos)
        if uid not in self.nodes or uid == ROOT_UID or parent_uid not in self.nodes:
            return False
        old_parent = self.nodes.get(self.nodes[uid].parent_uid or ROOT_UID)
        if old_parent and uid in old_parent.children:
            old_parent.children.remove(uid)
        self._insert_into_layout(uid, parent_uid, zone)
        if pos is not None:
            self.nodes[uid].x = max(0, pos.x())
            self.nodes[uid].y = max(0, pos.y())
        self.renumber_object_names()
        self.rebuild_canvas()
        self.rebuild_tree()
        self.select_node(uid)
        self._push_history()
        return True

    def add_widget_by_hierarchy_drop(self, widget_type, target_uid, zone):
        spec = WIDGET_INDEX.get(widget_type)
        if spec is None:
            return

        # Dropping a layout type on a frame changes that frame's layout property.
        if widget_type in LAYOUT_CONTAINER_TYPES:
            target = self.nodes.get(target_uid)
            if target is None or target.widget_type not in CONTAINER_TYPES:
                target = self.nodes.get(self._visible_parent_uid(target_uid), self.nodes[ROOT_UID])
            if target is not None and target.widget_type == "Frame":
                target.props["layout"] = widget_type
                self._sync_frame_layout_property(target)
                self.rebuild_canvas()
                self.rebuild_tree()
                self.select_node(target.uid)
                self._push_history()
            return

        uid = self._next_uid()
        width, height = spec["size"]
        node = WidgetNode(
            uid=uid,
            widget_type=widget_type,
            object_name="",
            text=self._default_text_for_type(widget_type),
            tooltip="",
            x=24,
            y=24,
            width=width,
            height=height,
            parent_uid=ROOT_UID,
            props=self._default_props_for_type(widget_type),
        )
        self.nodes[uid] = node

        if zone == "inside":
            target = self.nodes.get(target_uid, self.nodes[ROOT_UID])
            parent_uid = target_uid if target.widget_type in CONTAINER_TYPES else self._visible_parent_uid(target_uid)
            actual_parent_uid = self._layout_child_or_self(parent_uid)
            node.parent_uid = actual_parent_uid
            self.nodes[actual_parent_uid].children.append(uid)
        else:
            target = self.nodes.get(target_uid)
            if target is None or target_uid == ROOT_UID:
                actual_parent_uid = self._layout_child_or_self(ROOT_UID)
                node.parent_uid = actual_parent_uid
                self.nodes[actual_parent_uid].children.append(uid)
            else:
                actual_parent_uid = target.parent_uid or ROOT_UID
                siblings = self.nodes[actual_parent_uid].children
                try:
                    target_index = siblings.index(target_uid)
                except ValueError:
                    target_index = len(siblings)
                insert_index = target_index if zone == "before" else target_index + 1
                node.parent_uid = actual_parent_uid
                siblings.insert(max(0, min(insert_index, len(siblings))), uid)

        self.renumber_object_names()
        self.rebuild_canvas()
        self.rebuild_tree()
        self.select_node(uid)
        self._push_history()

    def add_widget(self, widget_type, *, parent_node, pos):
        if widget_type in LAYOUT_CONTAINER_TYPES:
            # Layouts are no longer user-created widgets. Treat old callers as
            # a request to set the selected/target container's layout property.
            target = parent_node or self.nodes.get(ROOT_UID)
            if target is not None and target.widget_type == "Frame":
                target.props["layout"] = widget_type
                self._sync_frame_layout_property(target)
                self.rebuild_canvas()
                self.rebuild_tree()
                self.select_node(target.uid)
                self._push_history()
            return
        spec = WIDGET_INDEX.get(widget_type)
        if spec is None:
            return
        uid = self._next_uid()
        width, height = spec["size"]
        requested_parent_uid = parent_node.uid if parent_node else ROOT_UID
        actual_parent_uid = self._layout_child_or_self(requested_parent_uid)
        node = WidgetNode(
            uid=uid,
            widget_type=widget_type,
            object_name="",
            text=self._default_text_for_type(widget_type),
            tooltip="",
            x=max(0, pos.x()),
            y=max(0, pos.y()),
            width=width,
            height=height,
            parent_uid=actual_parent_uid,
            props=self._default_props_for_type(widget_type),
        )
        self.nodes[uid] = node
        parent = self.nodes[actual_parent_uid]
        parent.children.append(uid)
        self.renumber_object_names()
        self.rebuild_canvas()
        self.rebuild_tree()
        self.select_node(uid)
        self._push_history()

    def renumber_object_names(self):
        counters: Dict[str, int] = {}

        def walk(uid):
            for child_uid in self.nodes[uid].children:
                child = self.nodes[child_uid]
                if child.widget_type in LAYOUT_CONTAINER_TYPES:
                    walk(child_uid)
                    continue
                base = WIDGET_INDEX[child.widget_type]["base"]
                counters[base] = counters.get(base, 0) + 1
                child.object_name = f"{base}_{counters[base]}"
                walk(child_uid)

        self.nodes[ROOT_UID].object_name = ROOT_OBJECT_NAME
        walk(ROOT_UID)

    def _is_layout_container(self, uid_or_type):
        if uid_or_type in self.nodes:
            return self.nodes[uid_or_type].widget_type in LAYOUT_CONTAINER_TYPES
        return uid_or_type in LAYOUT_CONTAINER_TYPES

    def _is_layout_managed(self, uid):
        node = self.nodes.get(uid)
        if node is None or not node.parent_uid:
            return False
        parent = self.nodes.get(node.parent_uid)
        if parent is not None and parent.widget_type in LAYOUT_CONTAINER_TYPES:
            return True
        # Virtual layout nodes are interpreted as their parent container's layout.
        # Their children are therefore layout-managed even though their visible
        # parent widget is the grandparent container host.
        if parent is not None and parent.parent_uid:
            grand = self.nodes.get(parent.parent_uid)
            if grand is not None and parent.widget_type in LAYOUT_CONTAINER_TYPES:
                return True
        return False

    def _node_should_fill_parent(self, uid):
        node = self.nodes.get(uid)
        if node is None or uid == ROOT_UID:
            return False
        if node.widget_type in LAYOUT_CONTAINER_TYPES and bool(node.props.get("fill_parent", True)):
            return True
        return False

    def _apply_layout_properties(self, widget, node):
        layout = widget.layout() if widget is not None else None
        if layout is None:
            return
        margin = int(node.props.get("margin", 8) or 0)
        spacing = int(node.props.get("spacing", 8) or 0)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)

    def _single_layout_child_for_node(self, node):
        if node is None:
            return None
        children = list(getattr(node, "children", []))
        if len(children) == 1:
            child = self.nodes.get(children[0])
            if child is not None and child.widget_type in LAYOUT_CONTAINER_TYPES:
                return child.uid
        return None

    def _visible_children_for_tree(self, uid):
        """Return the children users should see in the hierarchy.

        Layout nodes are implementation details for now. The hierarchy presents
        layout as a property of the owning container and flattens the visual
        children under that container.
        """
        node = self.nodes.get(uid)
        if node is None:
            return []
        layout_uid = self._single_layout_child_for_node(node)
        if layout_uid:
            layout_node = self.nodes.get(layout_uid)
            if layout_node is not None:
                return list(layout_node.children)
        return [child_uid for child_uid in node.children if self.nodes.get(child_uid) is not None and self.nodes[child_uid].widget_type not in LAYOUT_CONTAINER_TYPES]

    def _layout_child_or_self(self, parent_uid):
        """Return the internal parent that should actually own children.

        If a container has a hidden layout declaration node, children live under
        that node so rendering/export can apply the correct Qt layout while the
        hierarchy remains clean.
        """
        layout_uid = self._single_layout_child(parent_uid)
        return layout_uid or parent_uid

    def _visible_parent_uid(self, uid):
        node = self.nodes.get(uid)
        if node is None:
            return ROOT_UID
        parent_uid = node.parent_uid or ROOT_UID
        parent = self.nodes.get(parent_uid)
        if parent is not None and parent.widget_type in LAYOUT_CONTAINER_TYPES:
            return parent.parent_uid or ROOT_UID
        return parent_uid

    def _populate_frame_layout_props(self, node):
        """Expose layout ownership on frames even though the model stores it
        as a virtual layout child for compatibility with the hierarchy/exporter.
        """
        if node is None or node.widget_type != "Frame":
            return
        layout_uid = self._single_layout_child_for_node(node)
        node.props.setdefault("frame_style", "Bordered")
        if layout_uid:
            layout_node = self.nodes[layout_uid]
            node.props["layout"] = layout_node.widget_type
            node.props["spacing"] = int(layout_node.props.get("spacing", node.props.get("spacing", 8)) or 0)
            node.props["margin"] = int(layout_node.props.get("margin", node.props.get("margin", 8)) or 0)
        else:
            node.props.setdefault("layout", "Freeform")
            node.props.setdefault("frame_style", "Bordered")
            node.props.setdefault("spacing", 8)
            node.props.setdefault("margin", 8)
            node.props.setdefault("stretch", 1)

    def _remove_frame_layout_node(self, frame_node):
        layout_uid = self._single_layout_child_for_node(frame_node)
        if not layout_uid:
            return
        layout_node = self.nodes.get(layout_uid)
        if layout_node is None:
            return
        promoted = list(layout_node.children)
        frame_node.children = promoted
        for child_uid in promoted:
            child = self.nodes.get(child_uid)
            if child is not None:
                child.parent_uid = frame_node.uid
        self.nodes.pop(layout_uid, None)

    def _sync_frame_layout_property(self, frame_node):
        if frame_node is None or frame_node.widget_type != "Frame":
            return
        layout_name = str(frame_node.props.get("layout", "Freeform") or "Freeform")
        if layout_name == "Freeform":
            self._remove_frame_layout_node(frame_node)
            return
        if layout_name not in LAYOUT_CONTAINER_TYPES:
            return
        orientation = "horizontal" if layout_name == "Horizontal Row" else "vertical"
        layout_uid = self._ensure_layout_node(frame_node.uid, orientation)
        layout_node = self.nodes[layout_uid]
        layout_node.widget_type = layout_name
        layout_node.text = layout_name
        layout_node.props["spacing"] = int(frame_node.props.get("spacing", layout_node.props.get("spacing", 8)) or 0)
        layout_node.props["margin"] = self._effective_frame_padding(frame_node.props)
        layout_node.props["fill_parent"] = True
        layout_node.props.setdefault("stretch", 1)

    def _clamp_freeform_children(self, parent_uid):
        """Keep freeform children visually contained inside their frame host.

        Layout-managed children are owned by Qt layouts. Freeform children still
        use x/y/w/h, but they should never be allowed to visually bleed past the
        right or bottom edge of the containing frame in the Layout Editor.
        """
        parent_item = self.previews.get(parent_uid)
        parent_node = self.nodes.get(parent_uid)
        if parent_item is None or parent_node is None:
            return
        if self._single_layout_child(parent_uid):
            return
        host = parent_item.child_host if parent_item.child_host is not None else parent_item
        if host is None:
            return
        max_w = max(1, host.width())
        max_h = max(1, host.height())
        for child_uid in list(parent_node.children):
            child = self.nodes.get(child_uid)
            preview = self.previews.get(child_uid)
            if child is None or preview is None or self._is_layout_managed(child_uid):
                continue
            x = max(0, min(child.x, max_w - 1))
            y = max(0, min(child.y, max_h - 1))
            w = max(20, min(child.width, max_w - x))
            h = max(20, min(child.height, max_h - y))
            if (x, y, w, h) != (child.x, child.y, child.width, child.height):
                child.x, child.y, child.width, child.height = x, y, w, h
            preview.setGeometry(x, y, w, h)

    def rebuild_canvas(self):
        """Rebuild the visual Layout Editor from the widget model.

        Do not disable updates around the whole surface during rebuild. That
        regression could leave freshly-created preview widgets without a paint
        pass on some Qt builds, causing a populated hierarchy with an empty
        Layout Editor.
        """
        seen_preview_ids = set()
        for preview in list(self.previews.values()):
            if preview is None:
                continue
            marker = id(preview)
            if marker in seen_preview_ids:
                continue
            seen_preview_ids.add(marker)
            preview.hide()
            preview.setParent(None)
            preview.deleteLater()

        self.previews.clear()
        self.surface.refresh_theme()
        self.root_design_item = DesignItem(self, self.nodes[ROOT_UID], self.surface)
        self.root_design_item.setGeometry(0, 0, max(40, self.surface.width()), max(40, self.surface.height()))
        self.root_design_item.selected.connect(self.select_node)
        self.root_design_item.moved.connect(self._on_preview_moved)
        self.root_design_item.quick_action.connect(self._handle_quick_action)
        self.root_design_item.widget_dropped.connect(self.add_widget_from_drop)
        self.previews[ROOT_UID] = self.root_design_item
        self._build_children(ROOT_UID)
        self._apply_designer_theme_styles()
        self._refresh_selection_styles()
        self._sync_root_to_surface()

        for preview in self.previews.values():
            if preview is not None:
                preview.show()
                preview.updateGeometry()
                preview.update()
        self.root_design_item.raise_()
        self.surface.updateGeometry()
        self.surface.update()

    def _connect_preview(self, preview):
        preview.selected.connect(self.select_node)
        preview.moved.connect(self._on_preview_moved)
        preview.quick_action.connect(self._handle_quick_action)
        preview.widget_dropped.connect(self.add_widget_from_drop)

    def _clear_layout(self, host):
        old = host.layout() if host is not None else None
        if old is not None:
            QtWidgets.QWidget().setLayout(old)

    def _ensure_host_layout(self, host, layout_node):
        self._clear_layout(host)
        layout = QtWidgets.QVBoxLayout(host) if layout_node.widget_type == "Vertical Stack" else QtWidgets.QHBoxLayout(host)
        margin = int(layout_node.props.get("margin", 8) or 0)
        spacing = int(layout_node.props.get("spacing", 8) or 0)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)
        host.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        return layout

    def _single_layout_child(self, parent_uid):
        parent = self.nodes.get(parent_uid)
        if parent is None:
            return None
        children = list(parent.children)
        if len(children) == 1:
            child = self.nodes.get(children[0])
            if child is not None and child.widget_type in LAYOUT_CONTAINER_TYPES:
                return child.uid
        return None

    def _build_children(self, parent_uid):
        parent_item = self.previews[parent_uid]
        host = parent_item.child_host if parent_item.child_host is not None else parent_item
        layout_uid = self._single_layout_child(parent_uid)
        if layout_uid:
            # Interpret layout nodes as parent behavior, not a visible nested widget.
            layout_node = self.nodes[layout_uid]
            # Do not map layout_uid to parent_item in self.previews. Layout
            # nodes are virtual declarations; aliasing the parent preview causes
            # duplicate QWidget lifecycle handling during rebuilds.
            layout = self._ensure_host_layout(host, layout_node)
            for child_uid in layout_node.children:
                self._build_child_preview(child_uid, host, layout)
            return
        for child_uid in self.nodes[parent_uid].children:
            self._build_child_preview(child_uid, host, host.layout())

    def _build_child_preview(self, child_uid, host, parent_layout=None):
        node = self.nodes[child_uid]
        if node.widget_type in LAYOUT_CONTAINER_TYPES:
            # A layout node only becomes visible when it is not the sole layout
            # declaration under a container. This preserves legacy/freeform files.
            preview = DesignItem(self, node, host)
        else:
            preview = DesignItem(self, node, host)
        self._connect_preview(preview)
        if parent_layout is not None:
            stretch = int(node.props.get("stretch", 1) or 1)
            preview.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            preview.setMinimumSize(40, 40)
            parent_layout.addWidget(preview, max(0, stretch))
        elif self._node_should_fill_parent(child_uid):
            preview.setGeometry(0, 0, max(40, host.width()), max(40, host.height()))
        self.previews[child_uid] = preview
        preview.show()
        preview.refresh()
        if parent_layout is not None:
            parent_layout.activate()
        self._build_children(child_uid)

    def _apply_designer_theme_styles(self):
        """Let Nexus Core theme styles own widget appearance.

        The builder may draw selection chrome around DesignItem wrappers, but it
        must not apply local styles to live preview widgets. Otherwise the
        sandbox drifts from actual plugin runtime rendering.
        """
        self._repolish_widget_tree(self.surface)

    def _repolish_widget_tree(self, root_widget):
        app = QtWidgets.QApplication.instance()
        if app is None or root_widget is None:
            return
        widgets = [root_widget] + list(root_widget.findChildren(QtWidgets.QWidget))
        for widget in widgets:
            style = widget.style()
            if style is not None:
                style.unpolish(widget)
                style.polish(widget)
            widget.update()

    def rebuild_tree(self):
        self._loading = True
        try:
            self.tree.clear()
            self._add_tree_item(self.tree.invisibleRootItem(), ROOT_UID, locked=True)
            self.tree.expandAll()
            if self.selected_uid and self.nodes.get(self.selected_uid) and self.nodes[self.selected_uid].widget_type in LAYOUT_CONTAINER_TYPES:
                self.selected_uid = self.nodes[self.selected_uid].parent_uid or ROOT_UID
            if self.selected_uid:
                item = self._find_tree_item(self.selected_uid)
                if item is not None:
                    self.tree.setCurrentItem(item)
        finally:
            self._loading = False

    def _add_tree_item(self, parent_item, uid, *, locked=False):
        node = self.nodes[uid]
        if node.widget_type in LAYOUT_CONTAINER_TYPES:
            # Layouts are hidden implementation details. Flatten their children
            # under the owning container in the hierarchy.
            for child_uid in node.children:
                self._add_tree_item(parent_item, child_uid)
            return
        layout_suffix = ""
        layout_uid = self._single_layout_child_for_node(node)
        if layout_uid:
            layout_suffix = f" [Layout: {self.nodes[layout_uid].widget_type}]"
        elif node.widget_type == "Frame":
            layout_value = str(node.props.get("layout", "Freeform") or "Freeform")
            if layout_value != "Freeform":
                layout_suffix = f" [Layout: {layout_value}]"
        title = f"{node.object_name} ({node.widget_type}){layout_suffix}"
        item = QtWidgets.QTreeWidgetItem([title])
        item.setData(0, QtCore.Qt.UserRole, uid)
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if not locked:
            flags |= QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled
        else:
            flags |= QtCore.Qt.ItemIsDropEnabled
        item.setFlags(flags)
        parent_item.addChild(item)
        for child_uid in self._visible_children_for_tree(uid):
            self._add_tree_item(item, child_uid)

    def _find_tree_item(self, uid):
        root = self.tree.invisibleRootItem()
        queue = [root.child(i) for i in range(root.childCount())]
        while queue:
            item = queue.pop(0)
            if item.data(0, QtCore.Qt.UserRole) == uid:
                return item
            for i in range(item.childCount()):
                queue.append(item.child(i))
        return None

    def _is_descendant(self, possible_parent_uid, uid):
        current = self.nodes.get(uid)
        while current is not None and current.parent_uid:
            if current.parent_uid == possible_parent_uid:
                return True
            current = self.nodes.get(current.parent_uid)
        return False

    def move_node_to_parent(self, uid, parent_uid, *, index=None, pos=None):
        if uid not in self.nodes or uid == ROOT_UID:
            return False
        if parent_uid not in self.nodes:
            parent_uid = ROOT_UID
        if parent_uid != ROOT_UID and self.nodes[parent_uid].widget_type not in CONTAINER_TYPES:
            parent_uid = self._visible_parent_uid(parent_uid)
        actual_parent_uid = self._layout_child_or_self(parent_uid)
        if actual_parent_uid == uid or self._is_descendant(uid, actual_parent_uid):
            return False
        node = self.nodes[uid]
        old_parent = self.nodes.get(node.parent_uid or ROOT_UID)
        if old_parent and uid in old_parent.children:
            old_parent.children.remove(uid)
        node.parent_uid = actual_parent_uid
        if pos is not None:
            node.x = max(0, pos.x())
            node.y = max(0, pos.y())
        siblings = self.nodes[actual_parent_uid].children
        if index is None or index < 0 or index > len(siblings):
            siblings.append(uid)
        else:
            siblings.insert(index, uid)
        self.renumber_object_names()
        self.rebuild_canvas()
        self.rebuild_tree()
        self.select_node(uid)
        self._push_history()
        return True

    def can_move_node_by_drop(self, moving_uid, target_uid, zone):
        """Validate a hierarchy drop without mutating the model."""
        if moving_uid not in self.nodes or moving_uid == ROOT_UID:
            return False
        if target_uid not in self.nodes:
            target_uid = ROOT_UID
        if target_uid == moving_uid:
            return False
        if self._is_descendant(moving_uid, target_uid):
            return False
        if zone == "inside":
            return target_uid == ROOT_UID or self.nodes[target_uid].widget_type in CONTAINER_TYPES
        target = self.nodes.get(target_uid)
        if target is None:
            return True
        parent_uid = target.parent_uid or ROOT_UID
        return parent_uid in self.nodes

    def move_node_by_drop(self, moving_uid, target_uid, zone):
        if moving_uid not in self.nodes or moving_uid == ROOT_UID:
            return False
        if target_uid not in self.nodes:
            target_uid = ROOT_UID
        if zone == "inside" and (target_uid == ROOT_UID or self.nodes[target_uid].widget_type in CONTAINER_TYPES):
            return self.move_node_to_parent(moving_uid, target_uid)
        target = self.nodes[target_uid]
        visible_parent_uid = self._visible_parent_uid(target_uid)
        actual_parent_uid = target.parent_uid or visible_parent_uid
        siblings = self.nodes[actual_parent_uid].children
        try:
            target_index = siblings.index(target_uid)
        except ValueError:
            target_index = len(siblings)
        insert_index = target_index if zone == "before" else target_index + 1
        if moving_uid in siblings and siblings.index(moving_uid) < insert_index:
            insert_index -= 1
        return self.move_node_to_parent(moving_uid, visible_parent_uid, index=insert_index)

    def rebuild_structure_from_tree(self):
        if self._loading:
            return
        root_item = self.tree.invisibleRootItem().child(0)
        if root_item is None:
            return
        for uid, node in self.nodes.items():
            node.children = []
        def walk(item, parent_uid):
            parent_node = self.nodes[parent_uid]
            for index in range(item.childCount()):
                child_item = item.child(index)
                uid = child_item.data(0, QtCore.Qt.UserRole)
                if uid not in self.nodes or uid == ROOT_UID:
                    continue
                node = self.nodes[uid]
                actual_parent_uid = parent_uid
                if parent_uid != ROOT_UID and parent_node.widget_type not in CONTAINER_TYPES:
                    actual_parent_uid = parent_node.parent_uid or ROOT_UID
                node.parent_uid = actual_parent_uid
                self.nodes[actual_parent_uid].children.append(uid)
                walk(child_item, uid)
        walk(root_item, ROOT_UID)
        self.renumber_object_names()
        self.rebuild_canvas()
        self.rebuild_tree()
        self._push_history()

    def select_node(self, uid):
        if uid not in self.nodes:
            return
        self.selected_uid = uid
        item = self._find_tree_item(uid)
        if item is not None and self.tree.currentItem() is not item:
            self.tree.setCurrentItem(item)
        self._refresh_selection_styles()
        self.update_properties_panel()

    def _refresh_selection_styles(self):
        for uid, preview in self.previews.items():
            preview.set_selected(uid == self.selected_uid)

    def clear_selection(self):
        self.selected_uid = None
        self.tree.clearSelection()
        self._refresh_selection_styles()
        self.update_properties_panel()

    def _on_tree_selection_changed(self, current, previous):
        if not self._loading and current is not None:
            uid = current.data(0, QtCore.Qt.UserRole)
            if uid:
                self.select_node(uid)

    def _on_preview_moved(self, uid):
        if uid == self.selected_uid:
            self.update_properties_panel()
            self._push_history()

    def _sync_selected_text_from_editor(self, value):
        node = self.nodes.get(self.selected_uid) if self.selected_uid else None
        if node is None or node.locked or self._loading:
            return
        node.text = value
        self._refresh_node_visuals(node.uid, preserve_selection=True)
        self._push_history()

    def _sync_selected_tooltip_from_editor(self, value):
        node = self.nodes.get(self.selected_uid) if self.selected_uid else None
        if node is None or node.locked or self._loading:
            return
        node.tooltip = value
        preview = self.previews.get(node.uid)
        if preview is not None:
            self.apply_live_properties(preview.live_widget, node)

    def _sync_selected_geometry(self):
        if self._loading:
            return
        node = self.nodes.get(self.selected_uid) if self.selected_uid else None
        if node is None:
            return
        if self._is_layout_managed(node.uid):
            node.width = max(80, self.w_spin.value())
            node.height = max(24, self.h_spin.value())
        else:
            node.x = self.x_spin.value()
            node.y = self.y_spin.value()
            node.width = max(80, self.w_spin.value())
            node.height = max(24, self.h_spin.value())
        preview = self.previews.get(node.uid)
        if preview is not None:
            preview.refresh()
        self._push_history()

    def _refresh_node_visuals(self, uid, preserve_selection=False):
        self.rebuild_canvas()
        self.rebuild_tree()
        if preserve_selection and uid in self.nodes:
            self.select_node(uid)

    def _handle_quick_action(self, uid, action):
        node = self.nodes.get(uid)
        if node is None or uid == ROOT_UID:
            return
        if action == "delete":
            self.select_node(uid)
            self.remove_selected()
            return
        if action == "copy":
            self.select_node(uid)
            self.copy_selected()
            return
        if action == "cut":
            self.select_node(uid)
            self.cut_selected()
            return
        if action == "paste_into":
            self.select_node(uid)
            target = self.nodes.get(uid)
            if self._clipboard and target and target.widget_type in CONTAINER_TYPES:
                new_uid = self._paste_payload(self._clipboard, uid, QtCore.QPoint(24, 24))
                self.renumber_object_names()
                self.rebuild_canvas()
                self.rebuild_tree()
                self.select_node(new_uid)
                self._push_history()
            return
        parent = self.nodes.get(node.parent_uid or ROOT_UID)
        if parent is None:
            return
        if action in {"bring_to_front", "send_to_back"} and self._is_layout_managed(uid):
            return
        siblings = parent.children
        if uid not in siblings:
            return
        siblings.remove(uid)
        if action == "bring_to_front":
            siblings.append(uid)
        elif action == "send_to_back":
            siblings.insert(0, uid)
        elif action == "group_selected_here":
            selected = self.selected_uid
            if not selected or selected == uid or selected == ROOT_UID:
                siblings.insert(0, uid)
                return
            target = self.nodes.get(uid)
            moving = self.nodes.get(selected)
            if target is None or moving is None or not (target.widget_type in CONTAINER_TYPES):
                siblings.insert(0, uid)
                return
            old_parent = self.nodes.get(moving.parent_uid or ROOT_UID)
            if old_parent and selected in old_parent.children:
                old_parent.children.remove(selected)
            moving.parent_uid = uid
            target.children.append(selected)
            siblings.append(uid)
            self.rebuild_canvas()
            self.rebuild_tree()
            self.select_node(selected)
            self._push_history()
            return
        self.rebuild_canvas()
        self.rebuild_tree()
        self.select_node(uid)
        self._push_history()

    def _clear_widget_prop_form(self):
        while self.widget_prop_form.rowCount():
            self.widget_prop_form.removeRow(0)
        self.widget_prop_editors = {}

    def _style_property_specs(self, node):
        specs = [
            ("corner_style", "Corner Style", "choice", ["Rounded", "Square"]),
            ("border_style", "Border Style", "choice", ["Default", "None", "Subtle", "Strong"]),
        ]
        if node and node.widget_type == "Frame":
            specs.append(("background_style", "Background", "choice", ["Default", "Panel", "Surface", "Transparent"]))
        return specs

    def _build_widget_prop_form(self, node):
        self._clear_widget_prop_form()
        if node is None:
            return
        wt = node.widget_type
        grouped_specs = []
        specs = []
        if wt == "Frame":
            self._populate_frame_layout_props(node)
            node.props.setdefault("frame_style", "Bordered")
            node.props.setdefault("corner_style", "Rounded")
            node.props.setdefault("border_style", "Default")
            node.props.setdefault("background_style", "Default")
            if not self._frame_is_borderless(node.props) and int(node.props.get("margin", 0) or 0) <= 0:
                node.props["margin"] = 8
            grouped_specs = [
                ("Layout", [
                    ("layout", "Layout", "choice", ["Freeform", "Vertical Stack", "Horizontal Row"]),
                    ("spacing", "Spacing", "int"),
                    ("margin", "Padding (Bordered)", "int"),
                    ("stretch", "Stretch", "int"),
                ]),
                ("Style", [
                    ("frame_style", "Frame Style", "choice", ["Bordered", "Borderless"]),
                    ("corner_style", "Corner Style", "choice", ["Rounded", "Square"]),
                    ("border_style", "Border Style", "choice", ["Default", "None", "Subtle", "Strong"]),
                    ("background_style", "Background", "choice", ["Default", "Panel", "Surface", "Transparent"]),
                ]),
            ]
        elif wt == "Text Input":
            specs = [("placeholder", "Placeholder", "text")]
        elif wt == "Combo Box":
            specs = [("items", "Items (comma separated)", "text")]
        elif wt == "Slider":
            specs = [("minimum", "Minimum", "int"), ("maximum", "Maximum", "int"), ("value", "Value", "int"), ("orientation", "Orientation", "choice", ["Horizontal", "Vertical"]) ]
        elif wt in {"Spinbox", "Progress Bar"}:
            specs = [("minimum", "Minimum", "int"), ("maximum", "Maximum", "int"), ("value", "Value", "int")]
        elif wt in {"List View", "Hierarchy View", "Context Menu"}:
            label = "Items" if wt != "Context Menu" else "Actions"
            specs = [("items" if wt != "Context Menu" else "actions", label, "multiline")]
        elif wt in {"Table Viewer", "Table Editor"}:
            node.props.setdefault("corner_style", "Square")
            node.props.setdefault("fill_cells", True)
            grouped_specs = [
                ("Data", [
                    ("rows", "Rows", "int"),
                    ("columns", "Columns", "int"),
                    ("fill_cells", "Fill Cell Area", "bool"),
                ]),
                ("Capabilities", [
                    ("multi_select", "Multi-select", "bool"),
                    ("enable_clipboard", "Clipboard Shortcuts", "bool"),
                    ("enable_context_menu", "Right-click Menu", "bool"),
                    ("allow_structure_edit", "Add/Delete Rows & Columns", "bool"),
                    ("editable_cells", "Editable Cells", "bool"),
                ]),
                ("Style", self._style_property_specs(node)),
            ]
        elif wt == "Tab View":
            specs = [("tabs", "Tabs", "text")]
        elif wt == "Text Editor":
            node.props.setdefault("show_toolbar", False)
            grouped_specs = [
                ("Content", [
                    ("placeholder", "Placeholder", "text"),
                    ("read_only", "Read Only", "bool"),
                    ("word_wrap", "Word Wrap", "bool"),
                    ("font_size", "Font Size", "int"),
                    ("alignment", "Alignment", "choice", ["Left", "Center", "Right", "Justify"]),
                ]),
                ("Capabilities", [
                    ("show_toolbar", "Show Editing Toolbar", "bool"),
                    ("enable_clipboard", "Clipboard Actions", "bool"),
                    ("enable_context_menu", "Right-click Menu", "bool"),
                    ("enable_formatting", "Formatting Actions", "bool"),
                    ("enable_search", "Find/Search", "bool"),
                    ("auto_indent", "Auto-indent", "bool"),
                    ("tab_width", "Tab Width", "int"),
                ]),
                ("Style", self._style_property_specs(node)),
            ]
        elif wt == "Button":
            specs = [("style", "Style", "choice", ["Primary", "Secondary", "Ghost"]) ]
        elif wt in LAYOUT_CONTAINER_TYPES:
            specs = [("spacing", "Spacing", "int"), ("margin", "Margin", "int"), ("fill_parent", "Fill Parent", "bool"), ("stretch", "Stretch", "int")]
        if wt not in LAYOUT_CONTAINER_TYPES and not grouped_specs:
            specs.extend(self._style_property_specs(node))

        def add_editor(target_form, key, label, kind, rest):
            if kind == "text":
                editor = NexusTextInput(parent=self)
                editor.setText(str(node.props.get(key, "")))
            elif kind == "multiline":
                editor = NexusTextEditor(self)
                editor.setMaximumHeight(80)
                editor.setPlainText(str(node.props.get(key, "")))
            elif kind == "int":
                editor = NexusSpinBox(self)
                editor.setRange(-999999, 999999)
                editor.setValue(int(node.props.get(key, 0) or 0))
            elif kind == "choice":
                editor = NexusComboBox(self)
                editor.addItems(rest[0])
                idx = editor.findText(str(node.props.get(key, rest[0][0])))
                editor.setCurrentIndex(max(0, idx))
            elif kind == "bool":
                editor = NexusCheckBox("", self)
                editor.setChecked(bool(node.props.get(key, False)))
            else:
                return
            self._wire_widget_prop_editor(key, kind, editor)
            self.widget_prop_editors[key] = (kind, editor)
            target_form.addRow(label, editor)

        def add_section(title, section_specs, expanded=True):
            header = NexusButton(("▾ " if expanded else "▸ ") + title, self)
            header.setCheckable(True)
            header.setChecked(bool(expanded))
            body = QtWidgets.QWidget(self)
            body_form = QtWidgets.QFormLayout(body)
            body_form.setContentsMargins(12, 2, 0, 8)
            body_form.setSpacing(6)
            body.setVisible(bool(expanded))
            def toggle(checked, h=header, b=body, t=title):
                h.setText(("▾ " if checked else "▸ ") + t)
                b.setVisible(bool(checked))
            header.toggled.connect(toggle)
            self.widget_prop_form.addRow(header)
            self.widget_prop_form.addRow(body)
            for spec in section_specs:
                key, label, kind, *rest = spec
                add_editor(body_form, key, label, kind, rest)

        if grouped_specs:
            for title, section_specs in grouped_specs:
                add_section(title, section_specs, expanded=True)
        else:
            for spec in specs:
                key, label, kind, *rest = spec
                add_editor(self.widget_prop_form, key, label, kind, rest)

    def _wire_widget_prop_editor(self, key, kind, editor):
        if kind == "text":
            editor.textChanged.connect(lambda value, k=key: self._sync_widget_prop(k, value))
        elif kind == "multiline":
            editor.textChanged.connect(lambda k=key, e=editor: self._sync_widget_prop(k, e.toPlainText()))
        elif kind == "int":
            editor.valueChanged.connect(lambda value, k=key: self._sync_widget_prop(k, value))
        elif kind == "choice":
            editor.currentTextChanged.connect(lambda value, k=key: self._sync_widget_prop(k, value))
        elif kind == "bool":
            editor.toggled.connect(lambda value, k=key: self._sync_widget_prop(k, bool(value)))

    def _sync_widget_prop(self, key, value):
        if self._loading:
            return
        node = self.nodes.get(self.selected_uid) if self.selected_uid else None
        if node is None:
            return
        node.props[key] = value

        # Some property changes touch QWidget internals that are fragile when
        # updated while the property editor's own signal is still unwinding
        # (notably QPlainTextEdit style repolish and QTableWidget row/column
        # resets).  Update the model immediately, but rebuild the preview on the
        # next event-loop tick so Qt never repolishes/resizes widgets reentrantly.
        deferred_keys = {
            "layout", "spacing", "margin", "frame_style",
            "corner_style", "border_style", "background_style",
            "rows", "columns", "fill_cells", "multi_select", "enable_clipboard", "enable_context_menu", "allow_structure_edit", "editable_cells", "show_toolbar", "read_only", "word_wrap", "enable_formatting", "enable_search", "auto_indent", "tab_width", "font_size", "alignment",
        }
        if key in deferred_keys or node.widget_type in LAYOUT_CONTAINER_TYPES:
            if node.widget_type == "Frame" and key in {"layout", "spacing", "margin", "frame_style"}:
                self._sync_frame_layout_property(node)
            self._defer_preview_refresh(node.uid)
            self._push_history()
            return

        preview = self.previews.get(node.uid)
        if preview is not None:
            self.apply_live_properties(preview.live_widget, node)
            preview.refresh()
            self._style_preview_widget(preview.live_widget, node.widget_type, node.props)
        self.rebuild_tree()
        self.select_node(node.uid)
        self._push_history()

    def _defer_preview_refresh(self, selected_uid=None):
        # Coalesce multiple property editor signals into one safe rebuild.
        self._pending_preview_refresh_uid = selected_uid
        if getattr(self, "_preview_refresh_queued", False):
            return
        self._preview_refresh_queued = True
        QtCore.QTimer.singleShot(0, self._run_deferred_preview_refresh)

    def _run_deferred_preview_refresh(self):
        self._preview_refresh_queued = False
        selected_uid = getattr(self, "_pending_preview_refresh_uid", None)
        self._pending_preview_refresh_uid = None
        self._finish_deferred_structure_refresh(selected_uid)

    def _finish_deferred_structure_refresh(self, selected_uid=None):
        if selected_uid is not None and selected_uid not in self.nodes:
            selected_uid = None
        self.setUpdatesEnabled(False)
        try:
            self.rebuild_canvas()
            self.rebuild_tree()
            if selected_uid is not None:
                self.select_node(selected_uid)
            self.set_preview_mode(self._preview_mode, rebuild=False)
        finally:
            self.setUpdatesEnabled(True)
            self.update()

    def _collect_widget_props(self, node):
        if node is None:
            return
        for key, (kind, editor) in self.widget_prop_editors.items():
            if kind == "text":
                node.props[key] = editor.text()
            elif kind == "multiline":
                node.props[key] = editor.toPlainText()
            elif kind == "int":
                node.props[key] = editor.value()
            elif kind == "choice":
                node.props[key] = editor.currentText()
            elif kind == "bool":
                node.props[key] = editor.isChecked()

    def update_properties_panel(self):
        if self.selected_uid and self.nodes.get(self.selected_uid) and self.nodes[self.selected_uid].widget_type in LAYOUT_CONTAINER_TYPES:
            self.selected_uid = self.nodes[self.selected_uid].parent_uid or ROOT_UID
        node = self.nodes.get(self.selected_uid) if self.selected_uid else None
        self._loading = True
        try:
            if node is None:
                self.object_name_value.setText("-")
                self.widget_type_value.setText("-")
                self.text_edit.setText("")
                self.tooltip_edit.setText("")
                for spin in (self.x_spin, self.y_spin, self.w_spin, self.h_spin):
                    spin.setValue(0)
                self._clear_widget_prop_form()
                return
            self.object_name_value.setText(node.object_name)
            self.widget_type_value.setText(node.widget_type)
            self.text_edit.setText(node.text)
            self.tooltip_edit.setText(node.tooltip)
            self.x_spin.setValue(node.x)
            self.y_spin.setValue(node.y)
            self.w_spin.setValue(node.width)
            self.h_spin.setValue(node.height)
            locked = node.locked
            self._build_widget_prop_form(node)
        finally:
            self._loading = False
        self.remove_button.setEnabled(not locked)
        for control in (self.text_edit, self.tooltip_edit, self.x_spin, self.y_spin, self.w_spin, self.h_spin):
            control.setEnabled(True)
        if locked:
            self.text_edit.setEnabled(False)
            self.tooltip_edit.setEnabled(False)

    def apply_properties(self):
        node = self.nodes.get(self.selected_uid) if self.selected_uid else None
        if node is None:
            return
        if not node.locked:
            node.text = self.text_edit.text()
            node.tooltip = self.tooltip_edit.text()
        self._collect_widget_props(node)
        if self._is_layout_managed(node.uid):
            node.width = max(80, self.w_spin.value())
            node.height = max(24, self.h_spin.value())
        else:
            node.x = self.x_spin.value()
            node.y = self.y_spin.value()
            node.width = max(80, self.w_spin.value())
            node.height = max(24, self.h_spin.value())
        self._refresh_node_visuals(node.uid, preserve_selection=True)

    def remove_selected(self):
        if not self.selected_uid or self.selected_uid == ROOT_UID:
            return
        if self.selected_uid in self.nodes:
            self._remove_node_recursive(self.selected_uid)
            self.selected_uid = ROOT_UID
            self.renumber_object_names()
            self.rebuild_canvas()
            self.rebuild_tree()
            self.update_properties_panel()

    def _remove_node_recursive(self, uid):
        node = self.nodes.get(uid)
        if node is None:
            return
        for child_uid in list(node.children):
            self._remove_node_recursive(child_uid)
        if node.parent_uid and node.parent_uid in self.nodes and uid in self.nodes[node.parent_uid].children:
            self.nodes[node.parent_uid].children.remove(uid)
        self.nodes.pop(uid, None)

    def design_item_at_global(self, global_pos):
        child = QtWidgets.QApplication.widgetAt(global_pos)
        while child is not None:
            if isinstance(child, DesignItem):
                return child
            child = child.parentWidget()
        return None

    def _design_style_value(self, props, key, default):
        return str((props or {}).get(key, default) or default)

    def _apply_nexus_design_style(self, widget, props):
        if widget is None:
            return
        props = props or {}
        default_corner = "Square" if isinstance(widget, (NexusTableEditor, NexusTableView)) else "Rounded"
        corner = self._design_style_value(props, "corner_style", default_corner).lower()
        border = self._design_style_value(props, "border_style", "Default").lower()
        background = self._design_style_value(props, "background_style", "Default").lower()
        if hasattr(widget, "apply_nexus_style_properties"):
            widget.apply_nexus_style_properties(
                corner_style=corner,
                border_style=border,
                background_style=background,
            )
        else:
            widget.setProperty("nexusCorner", corner if corner in {"rounded", "square"} else "rounded")
            widget.setProperty("nexusBorder", border if border in {"default", "none", "subtle", "strong"} else "default")
            widget.setProperty("nexusBackground", background if background in {"default", "panel", "surface", "transparent"} else "default")
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def _frame_style_name(self, props):
        return str((props or {}).get("frame_style", "Bordered") or "Bordered")

    def _frame_is_borderless(self, props):
        return self._frame_style_name(props).lower() == "borderless"

    def _effective_frame_padding(self, props):
        if self._frame_is_borderless(props):
            return 0
        # Bordered frames need breathing room so controls do not touch chrome.
        return max(8, int((props or {}).get("margin", 8) or 0))

    def _apply_frame_chrome(self, frame, props):
        if frame is None:
            return
        frame.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        frame.setProperty("nexusControl", "frame")
        if self._frame_is_borderless(props):
            frame.setFrameShape(QtWidgets.QFrame.NoFrame)
            frame.setLineWidth(0)
            frame.setProperty("nexusFrameStyle", "borderless")
            frame.set_nexus_theme_role("surface") if hasattr(frame, "set_nexus_theme_role") else None
        else:
            frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
            frame.setLineWidth(1)
            frame.setProperty("nexusFrameStyle", "bordered")
            frame.set_nexus_theme_role("surface") if hasattr(frame, "set_nexus_theme_role") else None
        self._apply_nexus_design_style(frame, props)
        frame.style().unpolish(frame)
        frame.style().polish(frame)
        frame.update()

    def _configure_table_design(self, widget, props):
        props = props or {}
        rows = int(props.get("rows", 3) or 3)
        columns = int(props.get("columns", 3) or 3)
        widget.setUpdatesEnabled(False)
        widget.setColumnCount(columns)
        widget.setRowCount(rows)
        widget.setHorizontalHeaderLabels([chr(ord("A") + i) for i in range(columns)])
        widget.setAlternatingRowColors(False)
        widget.setShowGrid(True)
        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        fill_cells = bool(props.get("fill_cells", True))
        h_mode = QtWidgets.QHeaderView.Stretch if fill_cells else QtWidgets.QHeaderView.Interactive
        v_mode = QtWidgets.QHeaderView.Stretch if fill_cells else QtWidgets.QHeaderView.Interactive
        widget.horizontalHeader().setSectionResizeMode(h_mode)
        widget.verticalHeader().setSectionResizeMode(v_mode)
        widget.verticalHeader().setVisible(False)
        widget.horizontalHeader().setHighlightSections(False)
        widget.setCornerButtonEnabled(False)
        widget.setFrameShape(QtWidgets.QFrame.StyledPanel)
        if hasattr(widget, "set_table_capabilities"):
            widget.set_table_capabilities(
                context_menu=bool(props.get("enable_context_menu", True)),
                clipboard=bool(props.get("enable_clipboard", True)),
                structure_edit=bool(props.get("allow_structure_edit", isinstance(widget, NexusTableEditor))),
                multi_select=bool(props.get("multi_select", True)),
                editable=bool(props.get("editable_cells", isinstance(widget, NexusTableEditor))),
            )
        widget.updateGeometry()
        widget.setUpdatesEnabled(True)
        widget.update()
        return widget

    def _configure_text_editor_design(self, editor, props, text=""):
        props = props or {}
        if text:
            editor.setPlainText(str(text))
        elif props.get("placeholder"):
            editor.setPlainText(str(props.get("placeholder")))
        editor.setPlaceholderText(str(props.get("placeholder", "")))
        editor.setReadOnly(bool(props.get("read_only", False)))
        if hasattr(editor, "set_text_capabilities"):
            editor.set_text_capabilities(
                context_menu=bool(props.get("enable_context_menu", True)),
                clipboard=bool(props.get("enable_clipboard", True)),
                formatting=bool(props.get("enable_formatting", True)),
                search=bool(props.get("enable_search", True)),
                auto_indent=bool(props.get("auto_indent", False)),
                tab_width=int(props.get("tab_width", 4) or 4),
                word_wrap=bool(props.get("word_wrap", True)),
            )
        if hasattr(editor, "set_text_font"):
            editor.set_text_font(size=int(props.get("font_size", 10) or 10))
        if hasattr(editor, "set_text_alignment"):
            editor.set_text_alignment(str(props.get("alignment", "Left")))
        return editor

    def _make_text_editor_with_optional_toolbar(self, parent, text, props):
        props = props or {}
        show_toolbar = bool(props.get("show_toolbar", False))
        if not show_toolbar:
            editor = NexusTextEditor(parent=parent)
            self._configure_text_editor_design(editor, props, text)
            return editor

        container = NexusFrame(parent, frame_shape=QtWidgets.QFrame.NoFrame, border_style="none", background_style="transparent")
        container.setProperty("nexusTextEditorContainer", True)
        outer = QtWidgets.QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        toolbar = NexusFrame(container, frame_shape=QtWidgets.QFrame.NoFrame, border_style="none", background_style="transparent")
        bar = QtWidgets.QHBoxLayout(toolbar)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(4)

        editor = NexusTextEditor(parent=container)
        self._configure_text_editor_design(editor, props, text)
        container._nexus_inner_text_editor = editor

        def add_button(label, callback, enabled=True):
            button = NexusButton(label, toolbar)
            button.setEnabled(bool(enabled))
            button.clicked.connect(callback)
            bar.addWidget(button, 0)
            return button

        if bool(props.get("enable_clipboard", True)):
            add_button("Cut", editor.cut)
            add_button("Copy", editor.copy)
            add_button("Paste", editor.paste)
        if bool(props.get("enable_search", True)):
            add_button("Find", editor._find_text_dialog if hasattr(editor, "_find_text_dialog") else lambda: None)
        if bool(props.get("enable_formatting", True)):
            add_button("Left", lambda: editor.set_text_alignment("Left"))
            add_button("Center", lambda: editor.set_text_alignment("Center"))
            add_button("Right", lambda: editor.set_text_alignment("Right"))
            size = NexusSpinBox(toolbar)
            size.setRange(6, 72)
            size.setValue(int(props.get("font_size", 10) or 10))
            size.valueChanged.connect(lambda value: editor.set_text_font(size=int(value)))
            bar.addWidget(NexusLabel("Size", toolbar), 0)
            bar.addWidget(size, 0)
        bar.addStretch(1)
        outer.addWidget(toolbar, 0)
        outer.addWidget(editor, 1)
        return container

    def make_live_widget(self, widget_type, text, tooltip, *, parent=None, props=None) -> Tuple[QtWidgets.QWidget, Optional[QtWidgets.QWidget]]:
        props = props or {}
        host = None
        if widget_type in LAYOUT_CONTAINER_TYPES:
            widget = NexusFrame(parent)
            widget.setObjectName("DesignerLayoutContainer")
            layout = QtWidgets.QVBoxLayout(widget) if widget_type == "Vertical Stack" else QtWidgets.QHBoxLayout(widget)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(8)
            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            widget.setMinimumSize(40, 40)
            host = widget
        elif widget_type == "Frame":
            widget = NexusFrame(parent)
            widget.setObjectName("DesignerFrame")
            self._apply_frame_chrome(widget, props)
            # Use the real NexusFrame as the host so preview and export share
            # identical background, border, corner, and layout margin behavior.
            host = widget
        elif widget_type == "Sub-Window":
            widget = NexusFrame(parent)
            widget.setObjectName("DesignerSubWindow")
            header = NexusLabel(text or "Sub-Window", widget)
            header.setGeometry(8, 4, 220, 20)
            header_font = header.font()
            header_font.setBold(True)
            header.setFont(header_font)
            host = QtWidgets.QWidget(widget)
            host.setGeometry(8, 28, max(40, parent.width() - 16 if parent else 200), max(40, parent.height() - 36 if parent else 120))
            host.setAutoFillBackground(False)
        elif widget_type == "Dialog Box":
            widget = NexusFrame(parent)
            widget.setObjectName("DesignerDialog")
            title = NexusLabel(text or "Dialog", widget)
            title.setGeometry(12, 8, 220, 20)
            title_font = title.font()
            title_font.setBold(True)
            title.setFont(title_font)
            host = QtWidgets.QWidget(widget)
            host.setGeometry(10, 34, max(40, parent.width() - 20 if parent else 200), max(40, parent.height() - 44 if parent else 120))
            host.setAutoFillBackground(False)
        elif widget_type == "Scroll Area":
            widget = NexusScrollArea(parent)
            widget.setWidgetResizable(False)
            inner = QtWidgets.QWidget()
            inner.setMinimumSize(260, 160)
            inner.setObjectName("DesignerScrollInner")
            widget.setWidget(inner)
            host = inner
        elif widget_type == "Tab View":
            widget = NexusTabWidget(parent)
            page = QtWidgets.QWidget()
            page.setObjectName("DesignerTabPage")
            widget.addTab(page, text or "Page 1")
            host = page
        elif widget_type == "Stacked Widget":
            widget = NexusStackedWidget(parent)
            page = QtWidgets.QWidget()
            page.setObjectName("DesignerTabPage")
            widget.addWidget(page)
            host = page
        elif widget_type == "Custom Toolbar":
            widget = NexusFrame(parent)
            widget.setObjectName("DesignerToolbar")
            row = QtWidgets.QHBoxLayout(widget)
            row.setContentsMargins(6, 6, 6, 6)
            row.setSpacing(6)
            row.addWidget(NexusButton("Action", widget))
            row.addWidget(NexusButton("Action", widget))
            row.addStretch(1)
        elif widget_type == "Label":
            widget = NexusLabel(text or "Label", parent)
        elif widget_type == "Text Input":
            widget = NexusTextInput(parent=parent, placeholder=str(props.get("placeholder", "Enter text")))
            widget.setText(text or "")
        elif widget_type == "Button":
            widget = NexusButton(text or "Button", parent)
        elif widget_type == "Checkbox":
            widget = NexusCheckBox(text or "Checkbox", parent)
        elif widget_type == "Radio Button":
            widget = NexusRadioButton(text or "Option", parent)
        elif widget_type == "Slider":
            orientation = QtCore.Qt.Vertical if str(props.get("orientation", "Horizontal")) == "Vertical" else QtCore.Qt.Horizontal
            widget = NexusSlider(orientation, parent)
            widget.setRange(int(props.get("minimum", 0)), int(props.get("maximum", 100)))
            widget.setValue(int(props.get("value", 35)))
        elif widget_type == "Combo Box":
            widget = NexusComboBox(parent)
            items_source = props.get("items", text or "Option 1, Option 2")
            widget.addItems([value.strip() for value in str(items_source).replace("\n", ",").split(",") if value.strip()])
        elif widget_type == "Spinbox":
            widget = NexusSpinBox(parent)
            widget.setRange(int(props.get("minimum", 0)), int(props.get("maximum", 100)))
            widget.setValue(int(props.get("value", 5)))
        elif widget_type == "Table Viewer":
            widget = NexusTableView(parent=parent)
            self._configure_table_design(widget, props)
        elif widget_type == "Table Editor":
            widget = NexusTableEditor(parent=parent)
            self._configure_table_design(widget, props)
        elif widget_type == "Text Editor":
            widget = self._make_text_editor_with_optional_toolbar(parent, text or str(props.get("placeholder", "Text editor preview")), props)
        elif widget_type == "Hierarchy View":
            widget = NexusHierarchyView(parent)
            widget.setHeaderHidden(True)
            lines = str(props.get("items", "Root\n  Child")).splitlines() or ["Root"]
            root = QtWidgets.QTreeWidgetItem([lines[0].strip() or "Root"])
            for line in lines[1:]:
                root.addChild(QtWidgets.QTreeWidgetItem([line.strip() or "Child"]))
            widget.addTopLevelItem(root)
            widget.expandAll()
        elif widget_type == "Progress Bar":
            widget = NexusProgressBar(parent)
            widget.setRange(int(props.get("minimum", 0)), int(props.get("maximum", 100)))
            widget.setValue(int(props.get("value", 70)))
        elif widget_type == "List View":
            widget = NexusListWidget(parent)
            widget.addItems([line for line in str(props.get("items", "Item 1\nItem 2\nItem 3")).splitlines() if line.strip()])
        elif widget_type == "Context Menu":
            widget = NexusTextEditor(parent, text=text or "Action 1\nAction 2", enable_context_menu=True)
            widget.setMaximumHeight(90)
        elif widget_type == "Menu":
            widget = NexusLabel(text or "Menu", parent)
            widget.setFrameStyle(QtWidgets.QFrame.Box)
            widget.setAlignment(QtCore.Qt.AlignCenter)
        elif widget_type == "Sub-Menu":
            widget = NexusLabel(text or "Sub-Menu", parent)
            widget.setFrameStyle(QtWidgets.QFrame.Box)
            widget.setAlignment(QtCore.Qt.AlignCenter)
        else:
            widget = NexusLabel(text or widget_type, parent)
        widget.setToolTip(tooltip or "")
        self._apply_nexus_design_style(widget, props)
        if widget_type == "Button" and hasattr(widget, "setProperty"):
            variant = str(props.get("style", "Primary") or "Primary").strip().lower()
            widget.setProperty("nexusVariant", "primary" if variant == "primary" else "secondary")
            widget.style().unpolish(widget); widget.style().polish(widget); widget.update()
        self._style_preview_widget(widget, widget_type, props)
        if widget_type in LAYOUT_CONTAINER_TYPES:
            pseudo_node = WidgetNode(uid="__preview__", widget_type=widget_type, object_name="", props=props)
            self._apply_layout_properties(widget, pseudo_node)
        return widget, host

    def _style_preview_widget(self, widget, widget_type, props=None):
        """Deprecated preview hook retained for compatibility.

        Live preview widgets inherit appearance from Nexus Core global theme
        styles. Do not apply local preview styles here.
        """
        return

    def apply_live_properties(self, live_widget, node):
        props = node.props or {}
        if hasattr(live_widget, 'setText') and node.widget_type not in {"Text Input", "Text Editor", "Context Menu", "Sub-Window", "Dialog Box"}:
            try:
                live_widget.setText(node.text)
            except Exception:
                pass
        if isinstance(live_widget, NexusTextInput):
            live_widget.setPlaceholderText(str(props.get("placeholder", "Enter text")))
            live_widget.setText(node.text)
        elif isinstance(live_widget, NexusTextEditor) or getattr(live_widget, "_nexus_inner_text_editor", None) is not None:
            editor = getattr(live_widget, "_nexus_inner_text_editor", live_widget)
            self._configure_text_editor_design(editor, props, node.text or str(props.get("placeholder", "")))
        elif isinstance(live_widget, NexusComboBox):
            live_widget.clear()
            items_source = props.get("items", node.text or "Option 1, Option 2")
            live_widget.addItems([value.strip() for value in str(items_source).replace("\n", ",").split(",") if value.strip()])
        elif isinstance(live_widget, NexusSlider):
            live_widget.setRange(int(props.get("minimum", 0)), int(props.get("maximum", 100)))
            live_widget.setValue(int(props.get("value", 35)))
        elif isinstance(live_widget, NexusSpinBox):
            live_widget.setRange(int(props.get("minimum", 0)), int(props.get("maximum", 100)))
            live_widget.setValue(int(props.get("value", 5)))
        elif isinstance(live_widget, NexusProgressBar):
            live_widget.setRange(int(props.get("minimum", 0)), int(props.get("maximum", 100)))
            live_widget.setValue(int(props.get("value", 70)))
        elif isinstance(live_widget, (NexusTableEditor, NexusTableView)):
            self._configure_table_design(live_widget, props)
        elif isinstance(live_widget, NexusListWidget):
            live_widget.clear(); live_widget.addItems([line for line in str(props.get("items", "")).splitlines() if line.strip()])
        if node.widget_type == "Frame":
            self._apply_frame_chrome(live_widget, props)
        else:
            self._apply_nexus_design_style(live_widget, props)
        if node.widget_type == "Button" and hasattr(live_widget, "setProperty"):
            variant = str(props.get("style", "Primary") or "Primary").strip().lower()
            live_widget.setProperty("nexusVariant", "primary" if variant == "primary" else "secondary")
            live_widget.style().unpolish(live_widget); live_widget.style().polish(live_widget); live_widget.update()
        if node.widget_type in LAYOUT_CONTAINER_TYPES:
            self._apply_layout_properties(live_widget, node)
        live_widget.setToolTip(node.tooltip or "")

    def _designer_container_style(self):
        pal = self.palette()
        base = pal.color(QtGui.QPalette.Base).name()
        alt = pal.color(QtGui.QPalette.AlternateBase).name()
        mid = pal.color(QtGui.QPalette.Mid).name()
        text = pal.color(QtGui.QPalette.Text).name()
        return f"background:{base}; border:1px solid {mid}; border-radius:10px; color:{text};"

    def event(self, event):
        theme_change = getattr(QtCore.QEvent, "ThemeChange", None)
        watched = {
            QtCore.QEvent.PaletteChange,
            QtCore.QEvent.ApplicationPaletteChange,
            QtCore.QEvent.StyleChange,
        }
        if theme_change is not None:
            watched.add(theme_change)
        if event.type() in watched:
            QtCore.QTimer.singleShot(0, self.refresh_theme)
        return super().event(event)

    def refresh_theme(self):
        self.surface.refresh_theme()
        for preview in self.previews.values():
            preview.refresh_theme()
        self._apply_designer_theme_styles()
        self._refresh_selection_styles()

    def save_state(self):
        return {
            "plugin_name": self.plugin_name_edit.text(),
            "uid_counter": self._uid_counter,
            "nodes": [node.__dict__ for node in self.nodes.values()],
            "selected_uid": self.selected_uid,
        }

    def load_state(self, state):
        self.nodes.clear()
        self.previews.clear()
        self.selected_uid = None
        self._uid_counter = int(state.get("uid_counter") or 0)
        self.plugin_name_edit.setText(state.get("plugin_name") or "")
        for payload in state.get("nodes") or []:
            self.nodes[payload["uid"]] = WidgetNode(**payload)
        self._ensure_root_node()
        self.renumber_object_names()
        self.rebuild_canvas()
        self.rebuild_tree()
        selected_uid = state.get("selected_uid")
        self.select_node(selected_uid if selected_uid in self.nodes else ROOT_UID)

    def export_plugin(self):
        plugin_name = (self.plugin_name_edit.text() or "Generated Plugin").strip()
        plugin_id = self._plugin_id_from_name(plugin_name)
        package_name = self._package_name(plugin_id)
        repo_root = self._repo_root()
        sandbox_root = repo_root / "plugins" / "plugin-sandbox"
        plugin_root = sandbox_root / plugin_id
        package_root = plugin_root / package_name
        package_root.mkdir(parents=True, exist_ok=True)

        manifest = {
            "schema": "nexus.plugin_manifest.v1",
            "plugin_id": plugin_id,
            "display_name": plugin_name,
            "version": "0.1.0",
            "type": "tool",
            "source": "sandbox",
            "module": f"{package_name}.plugin",
            "class": f"{plugin_id}Plugin",
            "import_root": ".",
            "enabled": True,
            "min_nexus_version": "1.0.0",
            "provider": {"name": "Reel Big Buoy Company", "id": "reelbigbuoy"},
            "distribution": {"channel": "sandbox", "source": "local", "trust": "generated"},
            "ownership": {"class": "generated"},
            "display_category": "Sandbox"
        }
        (plugin_root / "plugin.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        (package_root / "__init__.py").write_text('"""Generated Nexus plugin package."""\n', encoding="utf-8")
        (package_root / "plugin.py").write_text(self._generated_plugin_py(plugin_id, plugin_name), encoding="utf-8")
        (package_root / "tool_host.py").write_text(self._generated_tool_host_py(plugin_id, plugin_name), encoding="utf-8")
        (package_root / "tool.py").write_text(self._generated_tool_py(plugin_name), encoding="utf-8")
        (plugin_root / "README.md").write_text(f"# {plugin_name}\n\nGenerated by Plugin Builder.\n", encoding="utf-8")
        self.log.appendPlainText(f"Exported {plugin_name} to {plugin_root}")
        self._hot_reload_exported_plugin(plugin_root, plugin_name)

    def _hot_reload_exported_plugin(self, plugin_root, plugin_name):
        main_window = self._primary_workspace_window()
        reloader = getattr(main_window, "reload_plugin_from_path", None) if main_window is not None else None
        if reloader is None:
            self.log.appendPlainText("Export complete. Restart Nexus or reopen the workspace to load the plugin.")
            return
        try:
            record = reloader(plugin_root)
            status = getattr(record, "status", "") if record is not None else ""
            error = getattr(record, "error", "") if record is not None else ""
            if status == "loaded":
                self.log.appendPlainText(f"Loaded {plugin_name}; it is now available in the Tools menu.")
            elif error:
                self.log.appendPlainText(f"Exported {plugin_name}, but live load failed: {error}")
            else:
                self.log.appendPlainText(f"Exported {plugin_name}; live load status: {status or 'unknown'}")
        except Exception as exc:
            self.log.appendPlainText(f"Exported {plugin_name}, but live reload failed: {exc}")

    def _primary_workspace_window(self):
        widget = self
        while widget is not None:
            if hasattr(widget, "workspace_manager") and hasattr(widget, "reload_plugin_from_path"):
                return widget
            workspace_manager = getattr(widget, "workspace_manager", None)
            if workspace_manager is not None and hasattr(workspace_manager, "primary_window"):
                try:
                    primary = workspace_manager.primary_window()
                    if primary is not None:
                        return primary
                except Exception:
                    pass
            widget = widget.parent() if hasattr(widget, "parent") else None
        app = QtWidgets.QApplication.instance()
        if app is not None:
            for widget in app.topLevelWidgets():
                if hasattr(widget, "reload_plugin_from_path"):
                    return widget
        return None

    def _generated_plugin_py(self, plugin_id, plugin_name):
        return f'''from nexus_workspace.core import build_plugin_manifest, build_tool_contribution\nfrom nexus_workspace.plugins.base import ToolDescriptor, WorkspacePlugin\nfrom .tool_host import GeneratedToolHost\n\n\nclass {plugin_id}Plugin(WorkspacePlugin):\n    plugin_id = "{plugin_id}"\n    display_name = "{plugin_name}"\n    version = "0.1.0"\n    description = "Generated by Plugin Builder."\n\n    def manifest(self):\n        return build_plugin_manifest(\n            plugin_id=self.plugin_id,\n            display_name=self.display_name,\n            version=self.version,\n            description=self.description,\n            tools=[build_tool_contribution(\n                tool_type_id=self.plugin_id,\n                display_name=self.display_name,\n                description=self.description,\n                metadata={{"surface": "workspace", "menu": "tools"}},\n            )],\n            publishes=[],\n            persists=['plugin.tool_state.v1'],\n            consumes=[],\n            handles_actions=[],\n            commands=[],\n            capabilities=[],\n            metadata={{'category': 'sandbox'}}\n        )\n\n    def register(self, context):\n        context.register_tool(ToolDescriptor(\n            tool_type_id=self.plugin_id,\n            display_name=self.display_name,\n            create_instance=lambda **kwargs: GeneratedToolHost(**kwargs),\n            plugin_id=self.plugin_id,\n            description=self.description,\n            metadata={{'surface': 'workspace', 'category': 'sandbox'}},\n        ))\n'''

    def _generated_tool_host_py(self, plugin_id, plugin_name):
        return f'''from nexus_workspace.framework.tools import NexusToolBase\nfrom .tool import GeneratedTool\n\n\nclass GeneratedToolHost(NexusToolBase):\n    tool_type_id = "{plugin_id}"\n    display_name = "{plugin_name}"\n\n    def __init__(self, parent=None, *, theme_name="Midnight", editor_title="{plugin_name}", plugin_context=None):\n        super().__init__(parent=parent, theme_name=theme_name, editor_title=editor_title, plugin_context=plugin_context)\n        self.ensure_header(title="{plugin_name}", subtitle="Generated by Plugin Builder")\n        self._tool = GeneratedTool(parent=self)\n        self.content_layout().addWidget(self._tool, 1)\n'''

    def _generated_tool_py(self, plugin_name):
        def walk(uid):
            ordered = []
            for child_uid in self.nodes[uid].children:
                child = self.nodes.get(child_uid)
                if child is None:
                    continue
                ordered.append({
                    "uid": child.uid,
                    "widget_type": child.widget_type,
                    "object_name": child.object_name,
                    "text": child.text,
                    "tooltip": child.tooltip,
                    "x": child.x,
                    "y": child.y,
                    "width": child.width,
                    "height": child.height,
                    "parent_uid": child.parent_uid,
                    "props": child.props,
                })
                ordered.extend(walk(child_uid))
            return ordered

        nodes = walk(ROOT_UID)
        payload = repr(nodes)
        root = self.nodes[ROOT_UID]
        root_payload = repr({
            "uid": ROOT_UID,
            "x": root.x,
            "y": root.y,
            "width": root.width,
            "height": root.height,
            "props": root.props,
        })
        return f"""from nexus_workspace.framework import QtCore, QtWidgets, NexusButton, NexusCheckBox, NexusComboBox, NexusFrame, NexusHierarchyView, NexusListWidget, NexusLabel, NexusProgressBar, NexusRadioButton, NexusScrollArea, NexusSlider, NexusSpinBox, NexusStackedWidget, NexusTabWidget, NexusTableEditor, NexusTableView, NexusTextEditor, NexusTextInput\n\nPLUGIN_NAME = {json.dumps(plugin_name)}\nROOT_UID = "__root__"\nROOT_FRAME = {root_payload}\nGENERATED_WIDGETS = {payload}\nLAYOUT_TYPES = {{"Vertical Stack", "Horizontal Row"}}\n\n\nclass GeneratedTool(QtWidgets.QWidget):\n    def __init__(self, parent=None):\n        super().__init__(parent)\n        self._instances = {{}}\n        self._child_hosts = {{}}\n        self._build_ui()\n\n    def _build_ui(self):\n        root = QtWidgets.QVBoxLayout(self)\n        root.setContentsMargins(0, 0, 0, 0)\n        root.setSpacing(0)\n\n        self.plugin_background_frame = NexusFrame(self, object_name="plugin_background_frame")\n        self.plugin_background_frame.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)\n        root.addWidget(self.plugin_background_frame, 1)\n        self._apply_frame_chrome(self.plugin_background_frame, ROOT_FRAME.get("props", {{}}))\n        self._child_hosts[None] = self.plugin_background_frame\n        self._child_hosts[ROOT_UID] = self.plugin_background_frame\n\n        # Generated in hierarchy preorder so parent hosts/layouts exist before children.\n        # TODO: Wire data synchronization between widgets.\n        # TODO: Connect commands, actions, and persistence hooks.\n        for spec in GENERATED_WIDGETS:\n            kind = spec.get("widget_type")\n            parent = self._child_hosts.get(spec.get("parent_uid"), self.plugin_background_frame)\n            if kind in LAYOUT_TYPES:\n                self._apply_layout(parent, spec)\n                self._instances[spec["uid"]] = parent\n                self._child_hosts[spec["uid"]] = parent\n                continue\n\n            widget, child_host = self._create_widget(spec, parent)\n            widget.setObjectName(spec["object_name"])\n            widget.setToolTip(spec.get("tooltip") or "")\n            self._apply_nexus_design_style(widget, spec.get("props", {{}}) or {{}})\n            widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)\n            if parent.layout() is not None:\n                stretch = int(spec.get("props", {{}}).get("stretch", 1) or 1)\n                parent.layout().addWidget(widget, max(0, stretch))\n            else:\n                widget.setGeometry(spec["x"], spec["y"], spec["width"], spec["height"])\n            widget.show()\n            self._instances[spec["uid"]] = widget\n            if child_host is not None:\n                self._child_hosts[spec["uid"]] = child_host\n\n    def _apply_layout(self, host, spec):\n        old = host.layout()\n        if old is not None:\n            QtWidgets.QWidget().setLayout(old)\n        kind = spec.get("widget_type")\n        layout = QtWidgets.QVBoxLayout(host) if kind == "Vertical Stack" else QtWidgets.QHBoxLayout(host)\n        props = spec.get("props", {{}}) or {{}}\n        margin = int(props.get("margin", 0) or 0)\n        spacing = int(props.get("spacing", 8) or 0)\n        layout.setContentsMargins(margin, margin, margin, margin)\n        layout.setSpacing(spacing)\n        host.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)\n        return layout\n\n    def _apply_frame_chrome(self, frame, props):\n        props = props or {{}}\n        style = str(props.get("frame_style", "Bordered") or "Bordered")\n        frame.setAttribute(QtCore.Qt.WA_StyledBackground, True)\n        frame.setProperty("nexusControl", "frame")\n        if style == "Borderless":\n            frame.setFrameShape(QtWidgets.QFrame.NoFrame)\n            frame.setLineWidth(0)\n            frame.setProperty("nexusFrameStyle", "borderless")\n            frame.set_nexus_theme_role("surface") if hasattr(frame, "set_nexus_theme_role") else None\n        else:\n            frame.setFrameShape(QtWidgets.QFrame.StyledPanel)\n            frame.setLineWidth(1)\n            frame.setProperty("nexusFrameStyle", "bordered")\n            frame.set_nexus_theme_role("surface") if hasattr(frame, "set_nexus_theme_role") else None\n        self._apply_nexus_design_style(frame, props)\n        frame.style().unpolish(frame)\n        frame.style().polish(frame)\n        frame.update()\n\n    def _apply_nexus_design_style(self, widget, props):\n        props = props or {{}}\n        default_corner = "Square" if isinstance(widget, (NexusTableEditor, NexusTableView)) else "Rounded"\n        corner = str(props.get("corner_style", default_corner) or default_corner).lower()\n        border = str(props.get("border_style", "Default") or "Default").lower()\n        background = str(props.get("background_style", "Default") or "Default").lower()\n        if hasattr(widget, "apply_nexus_style_properties"):\n            widget.apply_nexus_style_properties(corner_style=corner, border_style=border, background_style=background)\n        else:\n            widget.setProperty("nexusCorner", corner if corner in {{"rounded", "square"}} else "rounded")\n            widget.setProperty("nexusBorder", border if border in {{"default", "none", "subtle", "strong"}} else "default")\n            widget.setProperty("nexusBackground", background if background in {{"default", "panel", "surface", "transparent"}} else "default")\n            widget.style().unpolish(widget)\n            widget.style().polish(widget)\n            widget.update()\n\n    def _configure_table_design(self, widget, props):\n        props = props or {{}}\n        rows = int(props.get("rows", 3) or 3)\n        columns = int(props.get("columns", 3) or 3)\n        widget.setColumnCount(columns)\n        widget.setRowCount(rows)\n        widget.setHorizontalHeaderLabels([chr(ord("A") + i) for i in range(columns)])\n        widget.setAlternatingRowColors(False)\n        widget.setShowGrid(True)\n        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)\n        fill_cells = bool(props.get("fill_cells", True))\n        mode = QtWidgets.QHeaderView.Stretch if fill_cells else QtWidgets.QHeaderView.Interactive\n        widget.horizontalHeader().setSectionResizeMode(mode)\n        widget.verticalHeader().setSectionResizeMode(mode)\n        widget.verticalHeader().setVisible(False)\n        widget.horizontalHeader().setHighlightSections(False)\n        widget.setCornerButtonEnabled(False)\n        widget.setFrameShape(QtWidgets.QFrame.StyledPanel)\n        if hasattr(widget, "set_table_capabilities"):\n            widget.set_table_capabilities(\n                context_menu=bool(props.get("enable_context_menu", True)),\n                clipboard=bool(props.get("enable_clipboard", True)),\n                structure_edit=bool(props.get("allow_structure_edit", isinstance(widget, NexusTableEditor))),\n                multi_select=bool(props.get("multi_select", True)),\n                editable=bool(props.get("editable_cells", isinstance(widget, NexusTableEditor))),\n            )\n        return widget\n\n    def _configure_text_editor_design(self, editor, props, text=""):\n        props = props or {{}}\n        editor.setPlainText(str(text or props.get("placeholder", "Text editor preview")))\n        editor.setPlaceholderText(str(props.get("placeholder", "")))\n        editor.setReadOnly(bool(props.get("read_only", False)))\n        if hasattr(editor, "set_text_capabilities"):\n            editor.set_text_capabilities(\n                context_menu=bool(props.get("enable_context_menu", True)),\n                clipboard=bool(props.get("enable_clipboard", True)),\n                formatting=bool(props.get("enable_formatting", True)),\n                search=bool(props.get("enable_search", True)),\n                auto_indent=bool(props.get("auto_indent", False)),\n                tab_width=int(props.get("tab_width", 4) or 4),\n                word_wrap=bool(props.get("word_wrap", True)),\n            )\n        if hasattr(editor, "set_text_font"):\n            editor.set_text_font(size=int(props.get("font_size", 10) or 10))\n        if hasattr(editor, "set_text_alignment"):\n            editor.set_text_alignment(str(props.get("alignment", "Left")))\n        return editor\n\n    def _make_text_editor_with_optional_toolbar(self, parent, text, props):\n        props = props or {{}}\n        if not bool(props.get("show_toolbar", False)):\n            editor = NexusTextEditor(parent=parent)\n            return self._configure_text_editor_design(editor, props, text)\n        container = NexusFrame(parent, frame_shape=QtWidgets.QFrame.NoFrame, border_style="none", background_style="transparent")\n        root = QtWidgets.QVBoxLayout(container)\n        root.setContentsMargins(0, 0, 0, 0)\n        root.setSpacing(4)\n        toolbar = NexusFrame(container, frame_shape=QtWidgets.QFrame.NoFrame, border_style="none", background_style="transparent")\n        bar = QtWidgets.QHBoxLayout(toolbar)\n        bar.setContentsMargins(0, 0, 0, 0)\n        bar.setSpacing(4)\n        editor = NexusTextEditor(parent=container)\n        self._configure_text_editor_design(editor, props, text)\n        if bool(props.get("enable_clipboard", True)):\n            for label, slot in [("Cut", editor.cut), ("Copy", editor.copy), ("Paste", editor.paste)]:\n                b = NexusButton(label, toolbar); b.clicked.connect(slot); bar.addWidget(b, 0)\n        if bool(props.get("enable_search", True)) and hasattr(editor, "_find_text_dialog"):\n            b = NexusButton("Find", toolbar); b.clicked.connect(editor._find_text_dialog); bar.addWidget(b, 0)\n        if bool(props.get("enable_formatting", True)):\n            for label, align in [("Left", "Left"), ("Center", "Center"), ("Right", "Right")]:\n                b = NexusButton(label, toolbar); b.clicked.connect(lambda checked=False, a=align: editor.set_text_alignment(a)); bar.addWidget(b, 0)\n            size = NexusSpinBox(toolbar); size.setRange(6, 72); size.setValue(int(props.get("font_size", 10) or 10)); size.valueChanged.connect(lambda value: editor.set_text_font(size=int(value)))\n            bar.addWidget(NexusLabel("Size", toolbar), 0); bar.addWidget(size, 0)\n        bar.addStretch(1)\n        root.addWidget(toolbar, 0)\n        root.addWidget(editor, 1)\n        return container\n\n    def _create_widget(self, spec, parent):\n        kind = spec["widget_type"]\n        text = spec.get("text") or ""\n        props = spec.get("props", {{}}) or {{}}\n        if kind == "Frame":\n            widget = NexusFrame(parent)\n            self._apply_frame_chrome(widget, props)\n            return widget, widget\n        if kind == "Sub-Window":\n            widget = NexusFrame(parent)\n            self._apply_frame_chrome(widget, props)\n            title = NexusLabel(text or "Sub-Window", widget)\n            title.setGeometry(8, 4, 220, 20)\n            title_font = title.font()\n            title_font.setBold(True)\n            title.setFont(title_font)\n            host = QtWidgets.QWidget(widget)\n            host.setGeometry(8, 28, max(40, spec["width"] - 16), max(40, spec["height"] - 36))\n            host.setAutoFillBackground(False)\n            return widget, host\n        if kind == "Dialog Box":\n            widget = NexusFrame(parent)\n            self._apply_frame_chrome(widget, props)\n            title = NexusLabel(text or "Dialog", widget)\n            title.setGeometry(12, 8, 220, 20)\n            title_font = title.font()\n            title_font.setBold(True)\n            title.setFont(title_font)\n            host = QtWidgets.QWidget(widget)\n            host.setGeometry(10, 34, max(40, spec["width"] - 20), max(40, spec["height"] - 44))\n            host.setAutoFillBackground(False)\n            return widget, host\n        if kind == "Scroll Area":\n            widget = NexusScrollArea(parent)\n            inner = QtWidgets.QWidget()\n            inner.setMinimumSize(max(220, spec["width"] - 24), max(160, spec["height"] - 24))\n            inner.setAutoFillBackground(False)\n            widget.setWidget(inner)\n            widget.setWidgetResizable(True)\n            return widget, inner\n        if kind == "Tab View":\n            widget = NexusTabWidget(parent)\n            page = QtWidgets.QWidget()\n            page.setAutoFillBackground(False)\n            widget.addTab(page, text or "Page 1")\n            return widget, page\n        if kind == "Stacked Widget":\n            widget = NexusStackedWidget(parent)\n            page = QtWidgets.QWidget()\n            page.setAutoFillBackground(False)\n            widget.addWidget(page)\n            return widget, page\n        if kind == "Custom Toolbar":\n            widget = NexusFrame(parent)\n            row = QtWidgets.QHBoxLayout(widget)\n            row.setContentsMargins(6, 6, 6, 6)\n            row.setSpacing(6)\n            row.addWidget(NexusButton("Action", widget))\n            row.addWidget(NexusButton("Action", widget))\n            row.addStretch(1)\n            return widget, None\n        if kind == "Label":\n            return NexusLabel(text or "Label", parent), None\n        if kind == "Text Input":\n            widget = NexusTextInput(parent=parent, placeholder=str(props.get("placeholder", "Enter text")))\n            widget.setText(text)\n            return widget, None\n        if kind == "Button":\n            return NexusButton(text or "Button", parent), None\n        if kind == "Checkbox":\n            return NexusCheckBox(text or "Checkbox", parent), None\n        if kind == "Radio Button":\n            return NexusRadioButton(text or "Option", parent), None\n        if kind == "Slider":\n            widget = NexusSlider(QtCore.Qt.Horizontal, parent)\n            widget.setValue(int(props.get("value", 35) or 35))\n            return widget, None\n        if kind == "Combo Box":\n            widget = NexusComboBox(parent)\n            items_source = str(props.get("items", text or "Option 1, Option 2"))\n            widget.addItems([part.strip() for part in items_source.replace("\\n", ",").split(",") if part.strip()])\n            return widget, None\n        if kind == "Spinbox":\n            widget = NexusSpinBox(parent)\n            widget.setValue(int(props.get("value", 5) or 5))\n            return widget, None\n        if kind == "Table Viewer":\n            widget = NexusTableView(parent=parent)\n            self._configure_table_design(widget, props)\n            return widget, None\n        if kind == "Table Editor":\n            widget = NexusTableEditor(parent=parent)\n            self._configure_table_design(widget, props)\n            return widget, None\n        if kind == "Text Editor":\n            widget = self._make_text_editor_with_optional_toolbar(parent, text, props)\n            return widget, None\n        if kind == "Hierarchy View":\n            widget = NexusHierarchyView(parent)\n            widget.setHeaderHidden(True)\n            root = QtWidgets.QTreeWidgetItem(["Root"])\n            root.addChild(QtWidgets.QTreeWidgetItem(["Child"]))\n            widget.addTopLevelItem(root)\n            widget.expandAll()\n            return widget, None\n        if kind == "Progress Bar":\n            widget = NexusProgressBar(parent)\n            widget.setRange(0, 100)\n            widget.setValue(int(props.get("value", 70) or 70))\n            return widget, None\n        if kind == "List View":\n            widget = NexusListWidget(parent)\n            items = [line for line in str(props.get("items", "Item 1\\nItem 2\\nItem 3")).splitlines() if line.strip()]\n            widget.addItems(items)\n            return widget, None\n        if kind == "Context Menu":\n            widget = NexusTextEditor(parent)\n            widget.setPlainText(text or "Action 1\\nAction 2")\n            return widget, None\n        if kind == "Menu" or kind == "Sub-Menu":\n            label = NexusLabel(text or kind, parent)\n            label.setFrameStyle(QtWidgets.QFrame.Box)\n            label.setAlignment(QtCore.Qt.AlignCenter)\n            return label, None\n        return NexusLabel(text or kind, parent), None\n"""

    def _repo_root(self):
        return Path(__file__).resolve().parents[4]

    def _plugin_id_from_name(self, name):
        cleaned = re.sub(r'[^0-9A-Za-z]+', ' ', str(name or '').strip())
        parts = [part for part in cleaned.split() if part]
        if not parts:
            return 'GeneratedPlugin'
        value = ''.join(part[:1].upper() + part[1:] for part in parts)
        if value and value[0].isdigit():
            value = f"Plugin{value}"
        return value

    def _package_name(self, plugin_id):
        parts = re.findall(r'[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+', plugin_id)
        if not parts:
            return 'generated_plugin'
        return '_'.join(part.lower() for part in parts)
