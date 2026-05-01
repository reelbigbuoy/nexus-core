# ============================================================================
# Nexus
# File: plugins/owner/NoDE/node_plugin/graphics_items.py
# Description: Source module for node plugin functionality.
# Part of: NoDE Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================

from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets
from nexus_workspace.core.themes import THEMES
from .constants import NODE_WIDTH, TITLE_HEIGHT, PORT_RADIUS, PORT_SPACING, NODE_CORNER_RADIUS, GRID_SIZE
from .definitions import TestNodeData, node_definition_for_type
from .models import GraphConnectionData
from .geometry import qrect, qpoint, px


def _pen_style_from_name(name):
    value = str(name or "solid").strip().lower()
    return {
        "dash": QtCore.Qt.DashLine,
        "dashed": QtCore.Qt.DashLine,
        "dot": QtCore.Qt.DotLine,
        "dotted": QtCore.Qt.DotLine,
        "dashdot": QtCore.Qt.DashDotLine,
    }.get(value, QtCore.Qt.SolidLine)


class PortItem(QtWidgets.QGraphicsItem):
    INPUT = "input"
    OUTPUT = "output"

    STATE_NORMAL = "normal"
    STATE_VALID = "valid"
    STATE_INVALID = "invalid"
    STATE_SNAP = "snap"

    def __init__(self, parent_node, name: str, port_type: str, index: int):
        super().__init__(parent_node)
        self.parent_node = parent_node
        self.name = name
        self.port_type = port_type
        self.index = index
        self.definition_port = None
        self.radius = PORT_RADIUS
        self.connections = []
        self.visual_state = self.STATE_NORMAL

        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges, True)
        self._reposition()

    def _reposition(self):
        y = TITLE_HEIGHT + 20 + self.index * PORT_SPACING
        node_width = getattr(self.parent_node, "width", NODE_WIDTH)
        x = 0 if self.port_type == self.INPUT else node_width
        self.setPos(x, y)

    def boundingRect(self):
        r = self.radius + 6
        return QtCore.QRectF(-r, -r, 2 * r, 2 * r)

    def set_visual_state(self, state):
        if self.visual_state != state:
            self.visual_state = state
            self.update()

    def _fill_color(self):
        scene = self.scene()
        theme = scene.theme if scene and hasattr(scene, "theme") else THEMES["Midnight"]
        base = QtGui.QColor(theme["port_output"] if self.port_type == self.OUTPUT else theme["port_input"])
        if self.visual_state == self.STATE_VALID:
            return QtGui.QColor(88, 214, 141)
        if self.visual_state == self.STATE_INVALID:
            return QtGui.QColor(231, 76, 60)
        if self.visual_state == self.STATE_SNAP:
            return QtGui.QColor(241, 196, 15)
        return base

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        theme = self.scene().theme if self.scene() and hasattr(self.scene(), "theme") else THEMES["Midnight"]
        fill = self._fill_color()
        border_width = 2.5 if self.visual_state != self.STATE_NORMAL else 1.5
        outer_radius = self.radius + (2 if self.visual_state == self.STATE_SNAP else 0)
        painter.setPen(QtGui.QPen(QtGui.QColor(theme["app_bg"]), border_width))
        painter.setBrush(QtGui.QBrush(fill))
        painter.drawEllipse(QtCore.QPointF(0, 0), outer_radius, outer_radius)

    def scene_center(self) -> QtCore.QPointF:
        return self.mapToScene(QtCore.QPointF(0, 0))

    def add_connection(self, connection):
        if connection not in self.connections:
            self.connections.append(connection)

    def remove_connection(self, connection):
        if connection in self.connections:
            self.connections.remove(connection)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemScenePositionHasChanged:
            for conn in list(self.connections):
                conn.update_path()
        return super().itemChange(change, value)


class ConnectionPinItem(QtWidgets.QGraphicsItem):
    HIT_RECT = QtCore.QRectF(-12.0, -9.0, 24.0, 18.0)

    def __init__(self, connection_item, index, scene_pos):
        super().__init__()
        self.base_radius = 4.2
        self.connection_item = connection_item
        self.index = index
        self._drag_start_pos = None
        self._hovered = False
        self.setZValue(10)
        self.setPos(scene_pos)
        self.setAcceptHoverEvents(True)
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges
        )
        self.refresh_style()

    def boundingRect(self):
        return QtCore.QRectF(self.HIT_RECT)

    def shape(self):
        path = QtGui.QPainterPath()
        path.addRoundedRect(self.HIT_RECT, 5.0, 5.0)
        return path

    def set_execution_state(self, state='normal'):
        state = str(state or 'normal')
        if self.execution_state != state:
            self.execution_state = state
            self.update_path()
            self.refresh_style()

    def refresh_style(self):
        self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        selected = self.isSelected()
        hovered = self._hovered

        pin_fill = QtGui.QColor(241, 196, 15)
        pin_outline = QtGui.QColor(24, 24, 24)
        if selected:
            pin_fill = QtGui.QColor(255, 225, 95)
        elif hovered:
            pin_fill = QtGui.QColor(255, 214, 72)

        if selected:
            outline_color = QtGui.QColor(242, 155, 27, 255)
            box_rect = self.HIT_RECT.adjusted(1.0, 1.0, -1.0, -1.0)
            box_fill = QtGui.QColor(20, 20, 20, 78)
            painter.setPen(QtGui.QPen(outline_color, 1.7))
            painter.setBrush(box_fill)
            painter.drawRoundedRect(box_rect, 5.0, 5.0)

        painter.setPen(QtGui.QPen(pin_outline, 1.1))
        painter.setBrush(pin_fill)
        painter.drawEllipse(QtCore.QPointF(0.0, 0.0), self.base_radius, self.base_radius)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.setCursor(QtCore.Qt.OpenHandCursor)
        self.refresh_style()
        self.connection_item.sync_pin_items()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.refresh_style()
        self.connection_item.sync_pin_items()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            return QtCore.QPointF(value)
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            self.refresh_style()
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged and self.scene() is not None:
            self.connection_item.update_route_point_from_pin(self.index, QtCore.QPointF(self.pos()), from_pin=True)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = QtCore.QPointF(self.pos())
            self.setSelected(True)
            self.setCursor(QtCore.Qt.ClosedHandCursor)
            self.connection_item.setSelected(True)
            self.connection_item.sync_pin_items()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() != QtCore.Qt.LeftButton:
            return
        self.setCursor(QtCore.Qt.OpenHandCursor)
        scene = self.scene()
        if scene is None:
            self._drag_start_pos = None
            return
        if self._drag_start_pos is not None and self.pos() != self._drag_start_pos:
            scene.handle_pin_moved(self.connection_item, self.index, self._drag_start_pos, QtCore.QPointF(self.pos()))
        self._drag_start_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            scene = self.scene()
            if scene is not None:
                scene.remove_connection_pin(self.connection_item, self.index)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)



class ConnectionItem(QtWidgets.QGraphicsPathItem):
    ENDPOINT_SOURCE = "source"
    ENDPOINT_TARGET = "target"

    def __init__(self, source_port=None, target_port=None, temp_end_pos=None, route_points=None, preview_mode=False, connection_kind=None):
        super().__init__()
        self.source_port = source_port
        self.target_port = target_port
        self.temp_end_pos = QtCore.QPointF(temp_end_pos) if temp_end_pos is not None else QtCore.QPointF()
        self.route_points = [QtCore.QPointF(p) for p in (route_points or [])]
        self.preview_mode = preview_mode
        self.preview_valid = False
        self.preview_detached_endpoint = None
        self.pin_items = []
        self._hovered = False
        self._active_edit = False
        self._cached_connection_kind = (str(connection_kind).strip().lower() if connection_kind else None)
        self.execution_state = 'normal'


        self.setZValue(-1)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        if self.source_port:
            self.source_port.add_connection(self)
        if self.target_port:
            self.target_port.add_connection(self)

        self.refresh_style()
        self.update_path()
        self.sync_pin_items()

    def connection_kind(self):
        if self.source_port is not None and self.target_port is not None:
            source_def = getattr(self.source_port, "definition_port", None)
            target_def = getattr(self.target_port, "definition_port", None)
            source_kind = source_def.resolved_connection_kind() if source_def and hasattr(source_def, "resolved_connection_kind") else None
            target_kind = target_def.resolved_connection_kind() if target_def and hasattr(target_def, "resolved_connection_kind") else None
            if source_kind == target_kind and source_kind:
                self._cached_connection_kind = source_kind
            elif source_kind in (None, '', 'any', '*'):
                self._cached_connection_kind = target_kind or self._cached_connection_kind
            elif target_kind in (None, '', 'any', '*'):
                self._cached_connection_kind = source_kind or self._cached_connection_kind
        return self._cached_connection_kind or 'data'

    def _editor_connection_style(self):
        scene = self.scene()
        if scene is None:
            return None
        views = scene.views()
        if not views:
            return None
        editor = getattr(views[0], 'editor', None)
        if editor is None or not hasattr(editor, 'connection_style_for_kind'):
            return None
        return editor.connection_style_for_kind(self.connection_kind())

    def set_execution_state(self, state='normal'):
        state = str(state or 'normal')
        if self.execution_state != state:
            self.execution_state = state
            self.update_path()
            self.refresh_style()

    def refresh_style(self):
        scene = self.scene()
        theme = scene.theme if scene and hasattr(scene, "theme") else THEMES["Midnight"]
        connection_kind = self.connection_kind()
        style = self._editor_connection_style()
        role_defaults = {
            'exec': ('wire_exec', 3.0, QtCore.Qt.SolidLine),
            'data': ('connection', 2.15, QtCore.Qt.SolidLine),
            'requirement': ('wire_requirement', 2.6, QtCore.Qt.DashLine),
        }
        default_role, default_width, default_pen_style = role_defaults.get(connection_kind, ('connection', 2.15, QtCore.Qt.SolidLine))
        color_role = getattr(style, 'color_role', None) or default_role
        color = QtGui.QColor(theme.get(color_role, theme.get('connection')))
        width = getattr(style, 'width', None) or default_width
        pen_style = _pen_style_from_name(getattr(style, 'pen_style', None)) if style is not None else default_pen_style
        if self.preview_mode:
            color = QtGui.QColor(88, 214, 141) if self.preview_valid else QtGui.QColor(231, 76, 60)
            width = max(width, 2.8)
            pen_style = QtCore.Qt.SolidLine
        elif self._active_edit:
            color = QtGui.QColor(theme.get("wire_selected", theme.get("node_selected", theme.get("accent", theme["connection"]))))
            width = 3.6
        elif self.isSelected():
            color = QtGui.QColor(theme.get("wire_selected", theme.get("node_selected", theme.get("accent", theme["connection"]))))
            width = 4.0
        elif self._hovered:
            color = QtGui.QColor(theme.get("wire_selected", theme.get("node_selected", theme.get("accent", theme["connection"]))))
            color.setAlpha(230)
            width = 3.0
        if self.execution_state == 'active':
            color = QtGui.QColor(88, 214, 141)
            width = max(width, 4.2)
        elif self.execution_state == 'error':
            color = QtGui.QColor(231, 76, 60)
            width = max(width, 4.2)
        self.setPen(QtGui.QPen(color, width, pen_style, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        self.update()

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            self.refresh_style()
            self.sync_pin_items()
        return super().itemChange(change, value)

    def remove_from_ports(self):
        if self.source_port:
            self.source_port.remove_connection(self)
        if self.target_port:
            self.target_port.remove_connection(self)

    def source_scene_pos(self):
        if self.preview_detached_endpoint == self.ENDPOINT_SOURCE:
            return QtCore.QPointF(self.temp_end_pos)
        if self.source_port:
            return self.source_port.scene_center()
        return QtCore.QPointF(self.temp_end_pos)

    def target_scene_pos(self):
        if self.preview_detached_endpoint == self.ENDPOINT_TARGET:
            return QtCore.QPointF(self.temp_end_pos)
        if self.target_port:
            return self.target_port.scene_center()
        return QtCore.QPointF(self.temp_end_pos)

    def polyline_points(self):
        return [self.source_scene_pos()] + [QtCore.QPointF(p) for p in self.route_points] + [self.target_scene_pos()]

    def set_route_points(self, points):
        self.route_points = [QtCore.QPointF(p) for p in points]
        self.update_path()
        self.sync_pin_items()

    def update_route_point_from_pin(self, index, pos, from_pin=False):
        if 0 <= index < len(self.route_points):
            self.route_points[index] = QtCore.QPointF(pos)
            self.update_path()
            if not from_pin:
                self.sync_pin_items()

    def pins_should_be_visible(self):
        return not self.preview_mode

    def sync_pin_items(self):
        scene = self.scene()
        if scene is None:
            return
        while len(self.pin_items) > len(self.route_points):
            item = self.pin_items.pop()
            scene.removeItem(item)
        while len(self.pin_items) < len(self.route_points):
            pin = ConnectionPinItem(self, len(self.pin_items), QtCore.QPointF())
            self.pin_items.append(pin)
            scene.addItem(pin)
        visible = self.pins_should_be_visible()
        for index, point in enumerate(self.route_points):
            pin = self.pin_items[index]
            pin.index = index
            pin.setVisible(visible)
            pin.setPos(point)

    def update_path(self):
        points = self.polyline_points()
        if len(points) < 2:
            return
        path = _build_smoothed_polyline_path(points)
        self.setPath(path)
        visible = self.pins_should_be_visible()
        for pin in self.pin_items:
            pin.setVisible(visible)

    def connection_data(self):
        if not self.source_port or not self.target_port:
            return None
        return GraphConnectionData(
            self.source_port.parent_node.node_data.node_id,
            self.source_port.name,
            self.target_port.parent_node.node_data.node_id,
            self.target_port.name,
            self.route_points,
            self.connection_kind(),
        )

    def to_dict(self):
        data = self.connection_data()
        return data.to_dict() if data else None

    def endpoint_hit(self, scene_pos, tolerance=10.0):
        if QtCore.QLineF(scene_pos, self.source_scene_pos()).length() <= tolerance:
            return self.ENDPOINT_SOURCE
        if QtCore.QLineF(scene_pos, self.target_scene_pos()).length() <= tolerance:
            return self.ENDPOINT_TARGET
        return None

    def nearest_segment_index(self, scene_pos):
        points = self.polyline_points()
        best_index = None
        best_distance = None
        for idx in range(len(points) - 1):
            distance = _distance_to_segment(scene_pos, points[idx], points[idx + 1])
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_index = idx
        return best_index, best_distance

    def segment_at(self, scene_pos, tolerance=14.0):
        best_index, best_distance = self.nearest_segment_index(scene_pos)
        if best_index is None or best_distance is None or best_distance > tolerance:
            return None
        return best_index

    def insert_pin_index_for_segment(self, segment_index):
        return max(0, min(segment_index, len(self.route_points)))

    def begin_endpoint_drag(self, endpoint, scene_pos):
        self.preview_detached_endpoint = endpoint
        self.temp_end_pos = QtCore.QPointF(scene_pos)
        self.preview_mode = True
        self.preview_valid = False
        self._active_edit = True
        self.refresh_style()
        self.update_path()

    def update_endpoint_drag(self, scene_pos, valid=False):
        self.temp_end_pos = QtCore.QPointF(scene_pos)
        self.preview_valid = valid
        self.refresh_style()
        self.update_path()

    def restore_attached_state(self):
        self.preview_detached_endpoint = None
        self.preview_mode = False
        self.preview_valid = False
        self._active_edit = False
        self.refresh_style()
        self.update_path()

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.refresh_style()
        self.sync_pin_items()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.refresh_style()
        self.sync_pin_items()
        super().hoverLeaveEvent(event)


    def shape(self):
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(16.0)
        stroker.setCapStyle(QtCore.Qt.RoundCap)
        stroker.setJoinStyle(QtCore.Qt.RoundJoin)
        return stroker.createStroke(self.path())

    def paint(self, painter, option, widget=None):
        self.refresh_style()
        clean_option = QtWidgets.QStyleOptionGraphicsItem(option)
        clean_option.state &= ~QtWidgets.QStyle.State_Selected
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        if self.isSelected() or self._hovered or self._active_edit or self.preview_mode:
            scene = self.scene()
            theme = scene.theme if scene and hasattr(scene, "theme") else THEMES["Midnight"]
            base_color = QtGui.QColor(theme.get("wire_selected", theme.get("node_selected", theme.get("accent", theme["connection"]))))
            contrast = _contrasting_outline_color(base_color)
            halo_width = 7.0 if self.isSelected() else 5.5
            if self._active_edit or self.preview_mode:
                halo_width += 0.5
            painter.save()
            painter.setPen(QtGui.QPen(contrast, halo_width, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawPath(self.path())
            painter.restore()

        super().paint(painter, clean_option, widget)
        if not self.preview_mode:
            handle_pen = QtGui.QPen(QtGui.QColor(32, 32, 32), 1.0)
            handle_brush = QtGui.QBrush(QtGui.QColor(200, 200, 200) if self.isSelected() else QtGui.QColor(120, 120, 120))
            painter.setPen(handle_pen)
            painter.setBrush(handle_brush)
            for point in (self.source_scene_pos(), self.target_scene_pos()):
                local = self.mapFromScene(point)
                painter.drawEllipse(local, 3.0, 3.0)



class InlineSubgraphBoundaryItem(QtWidgets.QGraphicsItem):
    """Temporary dashed boundary used when a sub-graph is expanded inline."""
    TITLE_HEIGHT = 34.0

    def __init__(self, editor, container_node_id, rect, title='Sub-Graph'):
        super().__init__()
        self.editor = editor
        self.container_node_id = container_node_id
        self.title = str(title or 'Sub-Graph')
        self._rect = QtCore.QRectF(rect)
        self.setZValue(1000)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)

    def boundingRect(self):
        return self._rect.adjusted(-6, -6, 6, 6)

    def _title_rect(self):
        return QtCore.QRectF(self._rect.left(), self._rect.top(), self._rect.width(), self.TITLE_HEIGHT)

    def _button_rect(self):
        title_rect = self._title_rect()
        return QtCore.QRectF(title_rect.right() - 30, title_rect.top() + 6, 22, 22)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        scene = self.scene()
        theme = scene.theme if scene is not None and hasattr(scene, 'theme') else THEMES['Midnight']
        border = QtGui.QColor(theme.get('node_selected', '#6aa9ff'))
        fill = QtGui.QColor(theme.get('node_bg', '#20242b'))
        title_fill = QtGui.QColor(theme.get('node_title', '#2c3440'))
        text_color = QtGui.QColor(theme.get('text', '#ffffff'))
        fill.setAlpha(28)

        painter.setPen(QtGui.QPen(border, 2.0, QtCore.Qt.DashLine))
        painter.setBrush(QtGui.QBrush(fill))
        painter.drawRoundedRect(self._rect, 12, 12)

        title_rect = self._title_rect()
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(title_fill))
        painter.drawRoundedRect(title_rect, 12, 12)
        painter.drawRect(QtCore.QRectF(title_rect.left(), title_rect.bottom() - 12.0, title_rect.width(), 12.0))

        painter.setPen(QtGui.QPen(border, 2.0, QtCore.Qt.DashLine))
        painter.setBrush(QtCore.Qt.NoBrush)
        painter.drawRoundedRect(self._rect, 12, 12)

        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QtGui.QPen(text_color))
        painter.drawText(title_rect.adjusted(12, 0, -42, 0), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self.title)

        btn = self._button_rect()
        painter.setPen(QtGui.QPen(border, 1.4))
        painter.setBrush(QtGui.QBrush(title_fill.lighter(112)))
        painter.drawRoundedRect(btn, 5, 5)
        painter.setPen(QtGui.QPen(text_color, 2.0))
        painter.drawLine(QtCore.QLineF(btn.left() + 6.0, btn.center().y(), btn.right() - 6.0, btn.center().y()))

    def _event_in_collapse_button(self, event):
        # Keep the hit target a little forgiving so a normal single click on
        # the small collapse glyph does not require pixel-perfect placement.
        try:
            return self._button_rect().adjusted(-4, -4, 4, 4).contains(event.pos())
        except Exception:
            return False

    def _collapse_from_button_event(self, event):
        if event.button() == QtCore.Qt.LeftButton and self._event_in_collapse_button(event):
            if self.editor is not None and hasattr(self.editor, 'collapse_inline_subgraph'):
                self.editor.collapse_inline_subgraph(self.container_node_id)
            event.accept()
            return True
        return False

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self._event_in_collapse_button(event):
            # Accept the press so Qt delivers the release to this boundary item.
            # The actual collapse happens on release, matching normal button
            # behavior and avoiding dependence on double-click fallback.
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._collapse_from_button_event(event):
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._collapse_from_button_event(event):
            return
        super().mouseDoubleClickEvent(event)


class NodeItem(QtWidgets.QGraphicsItem):
    def __init__(self, node_data: TestNodeData, inputs=None, outputs=None):
        super().__init__()
        self.node_data = node_data
        self.inputs = []
        self.outputs = []

        # Empty lists are meaningful for data-only nodes. Do not fall back to
        # execution-style ports unless the caller omitted the interface entirely.
        self.input_names = ["In"] if inputs is None else list(inputs)
        self.output_names = ["Out"] if outputs is None else list(outputs)

        self.width = NODE_WIDTH
        self.height = 100
        self._recalculate_size()

        self.setFlags(
            QtWidgets.QGraphicsItem.ItemIsMovable |
            QtWidgets.QGraphicsItem.ItemIsSelectable |
            QtWidgets.QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setCacheMode(QtWidgets.QGraphicsItem.DeviceCoordinateCache)

        self._drag_start_pos = None
        self._drag_press_scene_pos = None
        self._drag_press_screen_pos = None
        self._drag_group_start_positions = {}
        self._drag_started = False
        self._interactive_drag_active = False
        self.execution_state = 'normal'
        self.execution_note = ''
        self.breakpoint_enabled = bool((self.node_data.properties or {}).get('__runtime_breakpoint', False))

        for i, name in enumerate(self.input_names):
            port = PortItem(self, name, "input", i)
            port.definition_port = self._definition_port_for_name(name, 'input')
            self.inputs.append(port)
        for i, name in enumerate(self.output_names):
            port = PortItem(self, name, "output", i)
            port.definition_port = self._definition_port_for_name(name, 'output')
            self.outputs.append(port)


    def _text_width(self, text, bold=False):
        font = QtWidgets.QApplication.font()
        font.setBold(bool(bold))
        metrics = QtGui.QFontMetrics(font)
        return metrics.horizontalAdvance(str(text or ""))

    def _recalculate_size(self):
        title_width = self._text_width(self.title, bold=True) + 64
        left_width = max([self._text_width(name) for name in self.input_names], default=0)
        right_width = max([self._text_width(name) for name in self.output_names], default=0)

        if self.input_names and self.output_names:
            port_width = 34 + left_width + 24 + right_width + 34
        elif self.output_names:
            port_width = 42 + right_width + 34
        elif self.input_names:
            port_width = 34 + left_width + 42
        else:
            port_width = 120

        self.width = float(max(NODE_WIDTH, title_width, port_width))
        row_count = max(len(self.input_names), len(self.output_names))
        self.height = float(max(72 if row_count == 0 else 100, TITLE_HEIGHT + 40 + row_count * PORT_SPACING))

    def _reposition_ports(self):
        for port in list(self.inputs) + list(self.outputs):
            port._reposition()
            for conn in list(getattr(port, "connections", [])):
                conn.update_path()

    def _dynamic_port_specs(self):
        props = getattr(self.node_data, 'properties', {}) or {}
        specs = props.get('__dynamic_ports', [])
        return [spec for spec in specs if isinstance(spec, dict)] if isinstance(specs, list) else []

    def _definition_port_for_name(self, name, direction):
        definition = self.definition
        static_ports = list(definition.inputs if direction == 'input' else definition.outputs) if definition is not None else []
        for port_def in static_ports:
            if getattr(port_def, 'name', None) == name:
                return port_def
        for spec in self._dynamic_port_specs():
            if spec.get('direction') == direction and spec.get('name') == name:
                return self._make_dynamic_definition_port(name, direction, spec.get('data_type', 'any'), spec.get('connection_kind', 'data'))
        return self._make_dynamic_definition_port(name, direction, 'any', 'data')

    def _make_dynamic_definition_port(self, name, direction, data_type='any', connection_kind='data'):
        try:
            from .definitions import NodePortDefinition
            return NodePortDefinition(
                id=str(name).strip().lower().replace(' ', '_') or 'port',
                name=str(name),
                direction=direction,
                data_type=data_type,
                connection_kind=connection_kind,
                multi_connection=True if direction == 'output' else False,
            )
        except Exception:
            return None

    def rebuild_ports(self, inputs=None, outputs=None):
        """Rebuild visual ports after a dynamic node changes its interface."""
        scene = self.scene()
        old_ports = list(self.inputs) + list(self.outputs)
        for port in old_ports:
            for conn in list(getattr(port, 'connections', [])):
                try:
                    if scene is not None:
                        scene.removeItem(conn)
                    conn.remove_from_ports()
                except Exception:
                    pass
            try:
                port.setParentItem(None)
                if scene is not None:
                    scene.removeItem(port)
            except Exception:
                pass

        self.inputs = []
        self.outputs = []
        self.input_names = list(inputs or [])
        self.output_names = list(outputs or [])

        for i, name in enumerate(self.input_names):
            port = PortItem(self, name, "input", i)
            port.definition_port = self._definition_port_for_name(name, 'input')
            self.inputs.append(port)

        for i, name in enumerate(self.output_names):
            port = PortItem(self, name, "output", i)
            port.definition_port = self._definition_port_for_name(name, 'output')
            self.outputs.append(port)

        self.prepareGeometryChange()
        self._recalculate_size()
        self._reposition_ports()
        self.update()
        if scene is not None and hasattr(scene, "ensure_logical_scene_rect"):
            scene.ensure_logical_scene_rect(self.sceneBoundingRect())

    @property
    def definition(self):
        return node_definition_for_type(self.node_data.node_type)

    @property
    def title(self):
        return self.node_data.title

    @title.setter
    def title(self, value):
        self.node_data.title = value
        self.update()

    def boundingRect(self):
        return QtCore.QRectF(0, 0, self.width, self.height)

    def is_subgraph_container(self):
        definition = self.definition
        metadata = getattr(definition, 'metadata', {}) if definition is not None else {}
        return bool(metadata.get('is_subgraph_container') or self.node_data.node_type == 'flow.subgraph_container')

    def _inline_expand_button_rect(self):
        return QtCore.QRectF(self.width - 28, 5, 22, 22)

    def set_execution_state(self, state='normal', note=''):
        state = str(state or 'normal')
        if self.execution_state != state or self.execution_note != note:
            self.execution_state = state
            self.execution_note = str(note or '')
            self.setToolTip(self.execution_note)
            self.update()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.boundingRect()
        theme = self.scene().theme if self.scene() and hasattr(self.scene(), "theme") else THEMES["Midnight"]

        body_color = QtGui.QColor(theme["node_bg"])
        title_color = QtGui.QColor(theme["node_title"])
        border_color = QtGui.QColor(theme["node_selected"] if self.isSelected() else theme["node_border"])
        text_color = QtGui.QColor(theme["text"])

        if self.execution_state == 'current':
            border_color = QtGui.QColor(88, 214, 141)
            body_color = body_color.lighter(118)
            title_color = title_color.lighter(135)
        elif self.execution_state == 'evaluated':
            border_color = QtGui.QColor(52, 152, 219)
            body_color = body_color.lighter(108)
        elif self.execution_state == 'error':
            border_color = QtGui.QColor(231, 76, 60)
            body_color = body_color.lighter(110)
        elif self.execution_state == 'halted':
            border_color = QtGui.QColor(241, 196, 15)
            body_color = body_color.lighter(112)

        painter.setPen(QtGui.QPen(border_color, 2))
        painter.setBrush(QtGui.QBrush(body_color))
        painter.drawRoundedRect(rect, NODE_CORNER_RADIUS, NODE_CORNER_RADIUS)

        title_rect = QtCore.QRectF(0, 0, self.width, TITLE_HEIGHT)
        painter.setBrush(QtGui.QBrush(title_color))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(title_rect, NODE_CORNER_RADIUS, NODE_CORNER_RADIUS)
        painter.drawRect(QtCore.QRectF(0.0, TITLE_HEIGHT - NODE_CORNER_RADIUS, self.width, NODE_CORNER_RADIUS))

        painter.setPen(QtGui.QPen(text_color))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            title_rect.adjusted(10, 0, -36, 0),
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            self.title
        )

        if self.is_subgraph_container() and not getattr(self, '_inline_subgraph_display', False):
            btn = self._inline_expand_button_rect()
            painter.setPen(QtGui.QPen(text_color, 1.3))
            painter.setBrush(QtGui.QBrush(body_color.lighter(120)))
            painter.drawRoundedRect(btn, 5, 5)
            painter.setPen(QtGui.QPen(text_color, 2.0))
            painter.drawLine(QtCore.QLineF(btn.left() + 6.0, btn.center().y(), btn.right() - 6.0, btn.center().y()))
            painter.drawLine(QtCore.QLineF(btn.center().x(), btn.top() + 6.0, btn.center().x(), btn.bottom() - 6.0))

        font.setBold(False)
        painter.setFont(font)

        for port in self.inputs:
            y = port.y()
            painter.drawText(
                QtCore.QRectF(14, y - 10, 70, 20),
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                port.name
            )

        for port in self.outputs:
            y = port.y()
            label_rect = QtCore.QRectF(14, y - 10, self.width - 28, 20) if not self.inputs else QtCore.QRectF(self.width - 124, y - 10, 110, 20)
            painter.drawText(
                label_rect,
                QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight,
                port.name
            )

        if self.breakpoint_enabled:
            badge_rect = QtCore.QRectF(self.width - 22, 6, 12, 12)
            painter.setPen(QtGui.QPen(QtGui.QColor(120, 24, 24), 1.0))
            painter.setBrush(QtGui.QBrush(QtGui.QColor(231, 76, 60)))
            painter.drawEllipse(badge_rect)
            inner_rect = badge_rect.adjusted(3.0, 3.0, -3.0, -3.0)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 235, 235)))
            painter.drawEllipse(inner_rect)

    def mousePressEvent(self, event):
        if (event.button() == QtCore.Qt.LeftButton and self.is_subgraph_container()
                and not getattr(self, '_inline_subgraph_display', False)
                and self._inline_expand_button_rect().contains(event.pos())):
            scene = self.scene()
            views = scene.views() if scene is not None else []
            editor = getattr(views[0], 'editor', None) if views else None
            if editor is not None and hasattr(editor, 'toggle_inline_subgraph_node'):
                editor.toggle_inline_subgraph_node(self)
                event.accept()
                return
        if event.button() == QtCore.Qt.LeftButton:
            scene = self.scene()
            if scene is not None and not self.isSelected() and not (event.modifiers() & (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier)):
                scene.clearSelection()
                self.setSelected(True)
            selected_nodes = []
            if scene is not None:
                selected_nodes = [item for item in scene.selectedItems() if isinstance(item, NodeItem)]
            if self not in selected_nodes:
                selected_nodes.append(self)
            self._drag_start_pos = QtCore.QPointF(self.pos())
            self._drag_press_scene_pos = QtCore.QPointF(event.scenePos())
            self._drag_press_screen_pos = QtCore.QPointF(event.screenPos())
            self._drag_group_start_positions = {node: QtCore.QPointF(node.pos()) for node in selected_nodes}
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (event.buttons() & QtCore.Qt.LeftButton) and self._drag_press_scene_pos is not None:
            if not self._drag_started:
                # Use screen coordinates for drag intent. Showing or resizing a
                # dock can change scenePos under a stationary cursor; that must
                # not move the node.
                press_screen = self._drag_press_screen_pos or QtCore.QPointF(event.screenPos())
                screen_distance = QtCore.QLineF(press_screen, QtCore.QPointF(event.screenPos())).length()
                if screen_distance < QtWidgets.QApplication.startDragDistance():
                    event.accept()
                    return

                # Begin from the current scene/node state so a viewport resize
                # between mouse press and actual drag cannot create a jump.
                self._drag_started = True
                self._drag_press_scene_pos = QtCore.QPointF(event.scenePos())
                self._drag_group_start_positions = {
                    node: QtCore.QPointF(node.pos())
                    for node in list(self._drag_group_start_positions.keys())
                }
                for node in list(self._drag_group_start_positions.keys()):
                    try:
                        node._interactive_drag_active = True
                    except RuntimeError:
                        pass

            delta = QtCore.QPointF(event.scenePos() - self._drag_press_scene_pos)
            for node, start_pos in list(self._drag_group_start_positions.items()):
                try:
                    node.setPos(start_pos + delta)
                except RuntimeError:
                    pass
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            super().mouseReleaseEvent(event)
            return

        scene = self.scene()
        start_positions = dict(self._drag_group_start_positions)
        dragged_nodes = list(start_positions.keys())
        was_dragging = self._drag_started

        self._drag_start_pos = None
        self._drag_press_scene_pos = None
        self._drag_press_screen_pos = None
        self._drag_group_start_positions = {}
        self._drag_started = False

        # Re-enable grid snapping after the interactive drag is complete. During
        # the drag, the node follows the cursor exactly; on release, it settles
        # onto the grid without creating a press-time jump.
        for node in dragged_nodes:
            try:
                node._interactive_drag_active = False
                if was_dragging:
                    node.setPos(node.pos())
            except RuntimeError:
                pass

        moved_nodes = []
        if scene is not None and not getattr(scene, "_suspend_undo", False):
            for node, old_pos in list(start_positions.items()):
                try:
                    new_pos = QtCore.QPointF(node.pos())
                except RuntimeError:
                    continue
                if new_pos != old_pos:
                    moved_nodes.append((node, old_pos, new_pos))

        if moved_nodes and scene is not None and scene.undo_stack is not None:
            if len(moved_nodes) > 1:
                scene.undo_stack.beginMacro("Move Nodes")
            try:
                for node, old_pos, new_pos in moved_nodes:
                    scene.handle_node_moved(node, old_pos, new_pos)
            finally:
                if len(moved_nodes) > 1:
                    scene.undo_stack.endMacro()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionChange:
            if getattr(self, '_interactive_drag_active', False):
                return QtCore.QPointF(value)
            x = round(value.x() / GRID_SIZE) * GRID_SIZE
            y = round(value.y() / GRID_SIZE) * GRID_SIZE
            return QtCore.QPointF(x, y)

        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            self.node_data.x = self.pos().x()
            self.node_data.y = self.pos().y()
            scene = self.scene()
            for port in self.inputs + self.outputs:
                for conn in list(port.connections):
                    conn.update_path()
            if scene is not None and hasattr(scene, "ensure_logical_scene_rect"):
                scene.ensure_logical_scene_rect(self.sceneBoundingRect())

        return super().itemChange(change, value)

    def to_dict(self):
        return {
            "node_data": self.node_data.to_dict(),
            "inputs": self.input_names,
            "outputs": self.output_names,
        }


def _build_smoothed_polyline_path(
    points,
    endpoint_buffer=2.0,
    bend_buffer=1.0,
    corner_radius=10.0,
):
    """Build a flowing Unreal-style cubic Bezier connection path.

    The hard rule is preserved: every segment leaves and enters each point
    horizontally. Tangent handles, not straight buffer segments, create the
    curve. Route points therefore behave like horizontal bend anchors.

    A key Blueprint-style behavior is preserved here as well: when a target is
    moved behind the source, the wire should *loop* instead of flipping its
    endpoint tangents. To do that, endpoint tangent directions stay stable and
    only the handle length adapts.
    """
    path = QtGui.QPainterPath()
    raw = [_pointf(point) for point in points]
    if not raw:
        return path

    path.moveTo(raw[0])
    if len(raw) == 1:
        return path

    tangent_dirs = _compute_anchor_tangent_dirs(raw)

    for index in range(len(raw) - 1):
        start = raw[index]
        end = raw[index + 1]
        start_dir = tangent_dirs[index]
        end_dir = tangent_dirs[index + 1]
        c1, c2 = _bezier_controls_for_segment(start, end, start_dir, end_dir)
        path.cubicTo(c1, c2, end)

    return path


def _compute_anchor_tangent_dirs(points):
    """Return horizontal tangent directions for each anchor in the wire.

    Endpoints remain stable in the Blueprint style: source exits to the right
    and target enters from the left, which means both endpoint tangents point
    in the +X direction. Intermediate bend anchors pick a direction from the
    surrounding X travel so user-routed wires still feel intentional.
    """
    if not points:
        return []

    dirs = [1.0] * len(points)
    if len(points) <= 2:
        return dirs

    previous_dir = 1.0
    for index in range(1, len(points) - 1):
        prev_pt = points[index - 1]
        point = points[index]
        next_pt = points[index + 1]
        composite_dx = next_pt.x() - prev_pt.x()
        local_dx = next_pt.x() - point.x()
        incoming_dx = point.x() - prev_pt.x()

        if abs(composite_dx) > 1e-3:
            direction = 1.0 if composite_dx >= 0.0 else -1.0
        elif abs(local_dx) > 1e-3:
            direction = 1.0 if local_dx >= 0.0 else -1.0
        elif abs(incoming_dx) > 1e-3:
            direction = 1.0 if incoming_dx >= 0.0 else -1.0
        else:
            direction = previous_dir

        dirs[index] = direction
        previous_dir = direction

    return dirs


def _bezier_controls_for_segment(start, end, start_dir=1.0, end_dir=1.0):
    """Compute Unreal-like horizontal tangents for a connection segment.

    The curve must always leave and enter horizontally, but its handle length
    should still feel expressive when nodes are stacked vertically or when the
    connection folds backward. Tangent *direction* is now explicit so backward
    links loop naturally instead of flipping and kinking.
    """
    dx = end.x() - start.x()
    dy = end.y() - start.y()
    abs_dx = abs(dx)
    abs_dy = abs(dy)

    # Use both horizontal and vertical separation so near-vertical links still
    # get a strong sweeping arc instead of a weak almost-straight rise.
    euclid = (abs_dx ** 2 + abs_dy ** 2) ** 0.5
    strength = (abs_dx * 0.22) + (abs_dy * 0.40) + (euclid * 0.12)

    # When endpoints keep pushing to the right but the destination lies behind
    # the source, exaggerate the horizontal handles so the wire loops instead
    # of flipping direction at the ports.
    is_backward_loop = (dx < 0.0) and (start_dir > 0.0) and (end_dir > 0.0)

    if is_backward_loop:
        min_strength = 90.0
        max_strength = 320.0
        strength += 40.0 + (abs_dx * 0.28)
    elif dx >= 0.0:
        min_strength = 52.0
        max_strength = 190.0
    else:
        min_strength = 72.0
        max_strength = 240.0
        strength += 22.0

    # When the segment is almost vertical, push the tangents a bit harder so
    # the wire keeps that signature Unreal-style sweep.
    if abs_dx < 60.0 and abs_dy > 24.0:
        vertical_floor = 60.0 + (abs_dy * (0.26 if is_backward_loop else 0.20))
        strength = max(strength, vertical_floor)

    # When the segment is nearly horizontal and short, keep the curve tighter
    # so it does not feel over-inflated.
    if abs_dy < 18.0 and abs_dx < 120.0 and not is_backward_loop:
        strength *= 0.82

    strength = max(min_strength, min(max_strength, strength))

    c1 = QtCore.QPointF(start.x() + (start_dir * strength), start.y())
    c2 = QtCore.QPointF(end.x() - (end_dir * strength), end.y())
    return c1, c2


def _pointf(point):
    return QtCore.QPointF(point)


def _dedupe_points(points, epsilon=0.05):
    if not points:
        return []
    deduped = [QtCore.QPointF(points[0])]
    for point in points[1:]:
        if _segment_len(deduped[-1], point) > epsilon:
            deduped.append(QtCore.QPointF(point))
    return deduped


def _horizontal_sign(dx):
    if dx > 1e-6:
        return 1.0
    if dx < -1e-6:
        return -1.0
    return 1.0


def _contrasting_outline_color(color):
    luminance = (0.299 * color.red()) + (0.587 * color.green()) + (0.114 * color.blue())
    outline = QtGui.QColor(12, 12, 12, 180) if luminance > 140 else QtGui.QColor(255, 255, 255, 170)
    return outline


def _length(vec):
    return (vec.x() ** 2 + vec.y() ** 2) ** 0.5


def _normalized(vec):
    length = _length(vec)
    if length < 1e-9:
        return QtCore.QPointF(0.0, 0.0)
    return QtCore.QPointF(vec.x() / length, vec.y() / length)


def _scale(vec, scalar):
    return QtCore.QPointF(vec.x() * scalar, vec.y() * scalar)


def _add(a, b):
    return QtCore.QPointF(a.x() + b.x(), a.y() + b.y())


def _sub(a, b):
    return QtCore.QPointF(a.x() - b.x(), a.y() - b.y())


def _segment_len(a, b):
    return _length(_sub(b, a))


def _distance_to_segment(point, a, b):
    ab = _sub(b, a)
    ab_len2 = ab.x() * ab.x() + ab.y() * ab.y()
    if ab_len2 <= 1e-12:
        return _segment_len(point, a)

    ap = _sub(point, a)
    t = (ap.x() * ab.x() + ap.y() * ab.y()) / ab_len2
    t = max(0.0, min(1.0, t))
    closest = QtCore.QPointF(a.x() + ab.x() * t, a.y() + ab.y() * t)
    return _segment_len(point, closest)

