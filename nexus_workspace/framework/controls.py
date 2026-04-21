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
# File: controls.py
# Description: Defines reusable Qt controls and section widgets used throughout Nexus Core.
#============================================================================

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets


class NexusSection(QtWidgets.QFrame):
    """Reusable framed section with an optional title and owned body layout."""

    def __init__(self, title='', parent=None, *, object_name='NexusSection', margins=(12, 12, 12, 12), spacing=8):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(*margins)
        root.setSpacing(spacing)
        self._title_label = None
        if title:
            self._title_label = QtWidgets.QLabel(str(title), self)
            self._title_label.setObjectName('NexusSectionTitle')
            font = self._title_label.font()
            font.setBold(True)
            self._title_label.setFont(font)
            root.addWidget(self._title_label, 0)
        self._body = QtWidgets.QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(spacing)
        root.addLayout(self._body, 1)

    def body_layout(self):
        return self._body

    def set_title(self, title):
        if self._title_label is None:
            self._title_label = QtWidgets.QLabel(self)
            self._title_label.setObjectName('NexusSectionTitle')
            font = self._title_label.font()
            font.setBold(True)
            self._title_label.setFont(font)
            self.layout().insertWidget(0, self._title_label, 0)
        self._title_label.setText(str(title or ''))


class NexusTabWidget(QtWidgets.QTabWidget):
    def __init__(self, parent=None, *, object_name='NexusTabWidget'):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setDocumentMode(True)


class NexusListWidget(QtWidgets.QListWidget):
    def __init__(self, parent=None, *, object_name='NexusListWidget'):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setAlternatingRowColors(True)
        self.setUniformItemSizes(True)


class NexusTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, parent=None, *, object_name='NexusTreeWidget'):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)


class NexusTableWidget(QtWidgets.QTableWidget):
    def __init__(self, rows=0, columns=0, parent=None, *, object_name='NexusTableWidget'):
        super().__init__(rows, columns, parent)
        self.setObjectName(object_name)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)


class NexusSplitter(QtWidgets.QSplitter):
    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None, *, object_name='NexusSplitter'):
        super().__init__(orientation, parent)
        self.setObjectName(object_name)
        self.setChildrenCollapsible(False)