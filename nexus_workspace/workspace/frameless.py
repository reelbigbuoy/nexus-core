# ============================================================================
#
#
# Copyright (c) 2026 Reel Big Buoy Company
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Nexus Core
# File: frameless.py
# Description: Provides frameless window behavior and custom drag-resize handling.
#============================================================================

from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets


class FrameInteractionEventFilter(QtCore.QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

    def eventFilter(self, obj, event):
        if not isinstance(obj, QtWidgets.QWidget):
            return False

        top = obj
        while top is not None and top.parentWidget() is not None:
            top = top.parentWidget()

        if top is not self.main_window:
            return False

        event_type = event.type()
        is_mouse_event = isinstance(event, QtGui.QMouseEvent)

        if event_type in (QtCore.QEvent.MouseMove, QtCore.QEvent.HoverMove):
            if self.main_window._resize_active and is_mouse_event:
                self.main_window._perform_resize(event.globalPos())
                return True

            if not self.main_window.isMaximized() and not self.main_window._drag_active:
                global_pos = None

                if is_mouse_event:
                    global_pos = event.globalPos()
                elif hasattr(event, "globalPos"):
                    global_pos = event.globalPos()

                if global_pos is not None:
                    mapped_pos = self.main_window.mapFromGlobal(global_pos)
                    self.main_window._update_cursor_for_position(mapped_pos)

            return False

        if event_type == QtCore.QEvent.MouseButtonPress and is_mouse_event:
            if event.button() == QtCore.Qt.LeftButton and not self.main_window.isMaximized():
                mapped_pos = self.main_window.mapFromGlobal(event.globalPos())
                edges = self.main_window._detect_resize_edges(mapped_pos)
                if edges:
                    self.main_window._resize_active = True
                    self.main_window._resize_edges = edges
                    self.main_window._resize_start_global = event.globalPos()
                    self.main_window._resize_start_geometry = self.main_window.geometry()
                    return True

        if event_type == QtCore.QEvent.MouseButtonRelease and is_mouse_event:
            if event.button() == QtCore.Qt.LeftButton and self.main_window._resize_active:
                self.main_window._resize_active = False
                self.main_window._resize_edges = set()
                self.main_window.setCursor(QtCore.Qt.ArrowCursor)
                return True

        return False


class TitleBarEventFilter(QtCore.QObject):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window

    def eventFilter(self, obj, event):
        if obj not in self.main_window._titlebar_drag_widgets:
            return False

        mouse_event_types = {
            QtCore.QEvent.MouseButtonPress,
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QEvent.MouseButtonDblClick,
            QtCore.QEvent.MouseMove,
        }
        if event.type() not in mouse_event_types or not isinstance(event, QtGui.QMouseEvent):
            return False

        mapped_pos = obj.mapTo(self.main_window.titleBar, event.pos())

        if event.type() == QtCore.QEvent.MouseButtonDblClick and event.button() == QtCore.Qt.LeftButton:
            if self.main_window._titlebar_can_drag(mapped_pos):
                self.main_window.toggle_maximize_restore()
                return True

        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            if self.main_window._titlebar_can_drag(mapped_pos):
                self.main_window._start_window_drag(event.globalPos())
                return True

        if event.type() == QtCore.QEvent.MouseMove and self.main_window._drag_active:
            self.main_window._perform_window_drag(event.globalPos())
            return True

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            self.main_window._stop_window_drag()
            return False

        return False


class FramelessWindowController:
    RESIZE_MARGIN = 10

    def install_titlebar_drag_filter(self):
        for widget in getattr(self, '_titlebar_drag_widgets', []):
            if widget is not None:
                widget.installEventFilter(self._titlebar_filter)

    def install_frame_interaction_filter(self):
        self.installEventFilter(self._frame_filter)
        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        for child in self.findChildren(QtWidgets.QWidget):
            child.setMouseTracking(True)
            child.setAttribute(QtCore.Qt.WA_Hover, True)
            child.installEventFilter(self._frame_filter)

    def titlebar_can_drag(self, pos):
        child = self.titleBar.childAt(pos)
        return not isinstance(child, QtWidgets.QAbstractButton)

    def start_window_drag(self, global_pos):
        self._drag_active = True
        self._drag_pos = global_pos - self.frameGeometry().topLeft()

    def perform_window_drag(self, global_pos):
        if self._drag_active and not self.isMaximized():
            self.move(global_pos - self._drag_pos)

    def stop_window_drag(self):
        self._drag_active = False

    def detect_resize_edges(self, pos):
        edges = set()
        rect = self.rect()
        margin = getattr(self, 'RESIZE_MARGIN', self.RESIZE_MARGIN)
        if pos.x() <= margin:
            edges.add('left')
        if pos.x() >= rect.width() - margin:
            edges.add('right')
        if pos.y() <= margin:
            edges.add('top')
        if pos.y() >= rect.height() - margin:
            edges.add('bottom')
        return edges

    def update_cursor_for_position(self, pos):
        edges = self.detect_resize_edges(pos)
        if edges == {'left'} or edges == {'right'} or edges == {'left', 'right'}:
            self.setCursor(QtCore.Qt.SizeHorCursor)
        elif edges == {'top'} or edges == {'bottom'} or edges == {'top', 'bottom'}:
            self.setCursor(QtCore.Qt.SizeVerCursor)
        elif edges in ({'top', 'left'}, {'bottom', 'right'}):
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif edges in ({'top', 'right'}, {'bottom', 'left'}):
            self.setCursor(QtCore.Qt.SizeBDiagCursor)
        else:
            self.setCursor(QtCore.Qt.ArrowCursor)

    def perform_resize(self, global_pos):
        if not self._resize_active:
            return
        geo = QtCore.QRect(self._resize_start_geometry)
        delta = global_pos - self._resize_start_global
        minimum = self.minimumSize()
        if 'right' in self._resize_edges:
            geo.setRight(max(geo.left() + minimum.width(), geo.right() + delta.x()))
        if 'bottom' in self._resize_edges:
            geo.setBottom(max(geo.top() + minimum.height(), geo.bottom() + delta.y()))
        if 'left' in self._resize_edges:
            geo.setLeft(min(geo.right() - minimum.width(), geo.left() + delta.x()))
        if 'top' in self._resize_edges:
            geo.setTop(min(geo.bottom() - minimum.height(), geo.top() + delta.y()))
        self.setGeometry(geo)