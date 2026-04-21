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
# File: surfaces.py
# Description: Provides shared surface, panel, and layout primitives for tool content areas.
#============================================================================

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets


class NexusSurface(QtWidgets.QFrame):
    """Reusable styled content surface for Nexus-owned tool layouts."""

    def __init__(self, parent=None, *, object_name='NexusSurface'):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)


class NexusPanel(NexusSurface):
    """Vertical surface with a default content layout."""

    def __init__(self, parent=None, *, object_name='NexusPanel', margins=(12, 12, 12, 12), spacing=10):
        super().__init__(parent, object_name=object_name)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)

    def layout_widget(self):
        return self._layout


class NexusToolbarRow(QtWidgets.QWidget):
    """Shared compact toolbar row used by Nexus tools."""

    def __init__(self, parent=None, *, object_name='NexusToolbarRow', margins=(12, 10, 12, 8), spacing=8):
        super().__init__(parent)
        self.setObjectName(object_name)
        self._layout = QtWidgets.QHBoxLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)

    def layout_widget(self):
        return self._layout

    def add_stretch(self):
        self._layout.addStretch(1)


class NexusToolHeader(QtWidgets.QWidget):
    """Standardized title/subtitle header for Nexus tools and inspectors."""

    def __init__(self, title='', subtitle='', parent=None):
        super().__init__(parent)
        self.setObjectName('NexusToolHeader')
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(4)

        self.titleLabel = QtWidgets.QLabel(title, self)
        self.titleLabel.setObjectName('NexusToolHeaderTitle')
        title_font = self.titleLabel.font()
        title_font.setBold(True)
        title_font.setPointSize(max(title_font.pointSize(), 11))
        self.titleLabel.setFont(title_font)

        self.subtitleLabel = QtWidgets.QLabel(subtitle, self)
        self.subtitleLabel.setObjectName('NexusToolHeaderSubtitle')
        self.subtitleLabel.setWordWrap(True)
        self.subtitleLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        layout.addWidget(self.titleLabel)
        layout.addWidget(self.subtitleLabel)

    def set_title(self, title):
        self.titleLabel.setText(str(title or ''))

    def set_subtitle(self, subtitle):
        self.subtitleLabel.setText(str(subtitle or ''))