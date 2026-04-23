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
# File: drop_overlay.py
# Description: Implements drop target overlays used during pane docking and workspace rearrangement.
#============================================================================

from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, int(value)))


def build_drop_regions(pane_rect, tab_bar_rect):
    pane_rect = QtCore.QRect(pane_rect)
    tab_bar_rect = QtCore.QRect(tab_bar_rect)
    if pane_rect.isNull():
        return {
            "tab": QtCore.QRect(),
            "content": QtCore.QRect(),
            "center": QtCore.QRect(),
            "left": QtCore.QRect(),
            "right": QtCore.QRect(),
            "top": QtCore.QRect(),
            "bottom": QtCore.QRect(),
        }

    tab_rect = tab_bar_rect.adjusted(-24, -8, 24, 10) if not tab_bar_rect.isNull() else QtCore.QRect()

    content_top = pane_rect.top()
    if not tab_bar_rect.isNull():
        content_top = min(pane_rect.bottom(), tab_bar_rect.bottom() + 2)
    content_rect = QtCore.QRect(
        pane_rect.left() + 2,
        content_top + 2,
        max(0, pane_rect.width() - 4),
        max(0, pane_rect.bottom() - content_top - 1),
    )
    if content_rect.height() < 40:
        content_rect = pane_rect.adjusted(2, 2, -2, -2)

    # Make the blue split zones reach well into the pane so they feel easy to hit.
    edge_x = _clamp(content_rect.width() * 0.38, 96, 220)
    edge_y = _clamp(content_rect.height() * 0.36, 72, 180)

    if content_rect.width() <= edge_x * 2:
        edge_x = max(18, content_rect.width() // 3)
    if content_rect.height() <= edge_y * 2:
        edge_y = max(18, content_rect.height() // 3)

    center_inset_x = max(18, int(edge_x * 0.96))
    center_inset_y = max(18, int(edge_y * 0.96))
    center_rect = content_rect.adjusted(center_inset_x, center_inset_y, -center_inset_x, -center_inset_y)
    if center_rect.width() < 56 or center_rect.height() < 56:
        center_rect = content_rect.adjusted(
            max(12, content_rect.width() // 4),
            max(12, content_rect.height() // 4),
            -max(12, content_rect.width() // 4),
            -max(12, content_rect.height() // 4),
        )

    left_rect = QtCore.QRect(content_rect.left(), content_rect.top(), edge_x, content_rect.height())
    right_rect = QtCore.QRect(content_rect.right() - edge_x + 1, content_rect.top(), edge_x, content_rect.height())
    top_rect = QtCore.QRect(content_rect.left(), content_rect.top(), content_rect.width(), edge_y)
    bottom_rect = QtCore.QRect(content_rect.left(), content_rect.bottom() - edge_y + 1, content_rect.width(), edge_y)

    return {
        "tab": tab_rect,
        "content": content_rect,
        "center": center_rect,
        "left": left_rect,
        "right": right_rect,
        "top": top_rect,
        "bottom": bottom_rect,
    }


class WorkspaceDropOverlay(QtWidgets.QWidget):
    ZONES = ("center", "left", "right", "top", "bottom")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zone = None
        self._regions = None
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.hide()

    def set_zone(self, zone, regions=None):
        self._zone = zone
        self._regions = regions
        self.update()
        self.setVisible(bool(zone))
        if self.isVisible():
            self.raise_()

    def clear_zone(self):
        self._zone = None
        self._regions = None
        self.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.raise_()

    def _zone_rect(self):
        regions = self._regions or build_drop_regions(self.rect(), QtCore.QRect())
        if self._zone == "center":
            return QtCore.QRectF(regions["center"])
        if self._zone in ("left", "right", "top", "bottom"):
            return QtCore.QRectF(regions[self._zone])
        return QtCore.QRectF()

    def paintEvent(self, event):
        if not self._zone:
            return
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        regions = self._regions or build_drop_regions(self.rect(), QtCore.QRect())
        zone_rect = self._zone_rect()
        if zone_rect.isNull():
            return

        frame_pen = QtGui.QPen(QtGui.QColor(60, 120, 216, 140), 1)
        ghost_brush = QtGui.QBrush(QtGui.QColor(60, 120, 216, 28))
        active_pen = QtGui.QPen(QtGui.QColor(86, 156, 255, 235), 2)
        active_brush = QtGui.QBrush(QtGui.QColor(86, 156, 255, 88))

        painter.setPen(frame_pen)
        painter.setBrush(QtCore.Qt.NoBrush)
        content = regions.get("content")
        if content and not content.isNull():
            painter.drawRoundedRect(QtCore.QRectF(content), 8, 8)

        for key in ("left", "right", "top", "bottom", "center"):
            rect = regions.get(key)
            if not rect or rect.isNull():
                continue
            if key == self._zone:
                continue
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(ghost_brush)
            painter.drawRoundedRect(QtCore.QRectF(rect), 8, 8)

        painter.setPen(active_pen)
        painter.setBrush(active_brush)
        painter.drawRoundedRect(zone_rect, 8, 8)

        if self._zone == "center":
            tab_rect = regions.get("tab")
            if tab_rect and not tab_rect.isNull():
                painter.setPen(QtGui.QPen(QtGui.QColor(86, 156, 255, 200), 2))
                painter.setBrush(QtCore.Qt.NoBrush)
                painter.drawRoundedRect(QtCore.QRectF(tab_rect), 6, 6)