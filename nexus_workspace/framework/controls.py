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
# Description: Defines reusable Nexus UI controls that wrap common Qt widgets.
#============================================================================

from __future__ import annotations

from typing import Iterable, Optional

from PyQt5 import QtCore, QtGui, QtWidgets


class NexusFrame(QtWidgets.QFrame):
    """Base frame wrapper for Nexus-owned framed content."""

    def __init__(self, parent=None, *, object_name='NexusFrame', frame_shape=QtWidgets.QFrame.NoFrame):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setFrameShape(frame_shape)


class NexusSection(NexusFrame):
    """Reusable framed section with an optional title and owned body layout."""

    def __init__(self, title='', parent=None, *, object_name='NexusSection', margins=(12, 12, 12, 12), spacing=8):
        super().__init__(parent, object_name=object_name, frame_shape=QtWidgets.QFrame.NoFrame)
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


class NexusSubWindow(QtWidgets.QMdiSubWindow):
    """Wrapper for MDI-style sub-windows hosted inside Nexus workspaces."""

    def __init__(self, parent=None, *, object_name='NexusSubWindow'):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)


class NexusMenuBar(QtWidgets.QMenuBar):
    """Framework-owned menu bar wrapper."""

    def __init__(self, parent=None, *, object_name='NexusMenuBar'):
        super().__init__(parent)
        self.setObjectName(object_name)

    def add_nexus_menu(self, title: str):
        return NexusMenu(title, self)


class NexusMenu(QtWidgets.QMenu):
    """Framework-owned menu wrapper for menus and submenus."""

    def __init__(self, title='', parent=None, *, object_name='NexusMenu'):
        super().__init__(str(title or ''), parent)
        self.setObjectName(object_name)

    def add_nexus_menu(self, title: str):
        submenu = NexusMenu(title, self)
        self.addMenu(submenu)
        return submenu

    def add_action(self, text: str, callback=None, *, checkable: bool = False, shortcut: Optional[str] = None, tooltip: str = ''):
        action = QtWidgets.QAction(str(text or ''), self)
        action.setCheckable(bool(checkable))
        if shortcut:
            action.setShortcut(QtGui.QKeySequence(str(shortcut)))
        if tooltip:
            action.setToolTip(str(tooltip))
            action.setStatusTip(str(tooltip))
        if callback is not None:
            action.triggered.connect(callback)
        self.addAction(action)
        return action


class NexusLabel(QtWidgets.QLabel):
    def __init__(self, text='', parent=None, *, object_name='NexusLabel', word_wrap=False):
        super().__init__(str(text or ''), parent)
        self.setObjectName(object_name)
        self.setWordWrap(bool(word_wrap))


class NexusTextInput(QtWidgets.QLineEdit):
    def __init__(self, text='', parent=None, *, object_name='NexusTextInput', placeholder=''):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setText(str(text or ''))
        if placeholder:
            self.setPlaceholderText(str(placeholder))


class NexusButton(QtWidgets.QPushButton):
    def __init__(self, text='', parent=None, *, object_name='NexusButton', tooltip=''):
        super().__init__(str(text or ''), parent)
        self.setObjectName(object_name)
        if tooltip:
            self.setToolTip(str(tooltip))


class NexusCheckBox(QtWidgets.QCheckBox):
    def __init__(self, text='', parent=None, *, object_name='NexusCheckBox'):
        super().__init__(str(text or ''), parent)
        self.setObjectName(object_name)


class NexusRadioButton(QtWidgets.QRadioButton):
    def __init__(self, text='', parent=None, *, object_name='NexusRadioButton'):
        super().__init__(str(text or ''), parent)
        self.setObjectName(object_name)


class NexusSlider(QtWidgets.QSlider):
    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None, *, object_name='NexusSlider'):
        super().__init__(orientation, parent)
        self.setObjectName(object_name)


class NexusComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None, *, object_name='NexusComboBox', editable=False):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setEditable(bool(editable))

    def set_items(self, items: Iterable):
        self.clear()
        for item in items or []:
            if isinstance(item, tuple) and len(item) >= 2:
                self.addItem(str(item[0]), item[1])
            else:
                self.addItem(str(item))


class NexusSpinBox(QtWidgets.QSpinBox):
    def __init__(self, parent=None, *, object_name='NexusSpinBox'):
        super().__init__(parent)
        self.setObjectName(object_name)


class NexusDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    def __init__(self, parent=None, *, object_name='NexusDoubleSpinBox'):
        super().__init__(parent)
        self.setObjectName(object_name)


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


class NexusHierarchyView(NexusTreeWidget):
    def __init__(self, parent=None, *, object_name='NexusHierarchyView'):
        super().__init__(parent, object_name=object_name)


class NexusTableWidget(QtWidgets.QTableWidget):
    def __init__(self, rows=0, columns=0, parent=None, *, object_name='NexusTableWidget'):
        super().__init__(rows, columns, parent)
        self.setObjectName(object_name)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)


class NexusTableView(NexusTableWidget):
    """Read-only table wrapper."""

    def __init__(self, rows=0, columns=0, parent=None, *, object_name='NexusTableView'):
        super().__init__(rows, columns, parent, object_name=object_name)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)


class NexusTableEditor(NexusTableWidget):
    """Editable table wrapper."""

    def __init__(self, rows=0, columns=0, parent=None, *, object_name='NexusTableEditor'):
        super().__init__(rows, columns, parent, object_name=object_name)
        self.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed | QtWidgets.QAbstractItemView.SelectedClicked)


class NexusTextEditor(QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None, *, object_name='NexusTextEditor', placeholder=''):
        super().__init__(parent)
        self.setObjectName(object_name)
        if placeholder:
            self.setPlaceholderText(str(placeholder))


class NexusProgressBar(QtWidgets.QProgressBar):
    def __init__(self, parent=None, *, object_name='NexusProgressBar'):
        super().__init__(parent)
        self.setObjectName(object_name)


class NexusStackedWidget(QtWidgets.QStackedWidget):
    def __init__(self, parent=None, *, object_name='NexusStackedWidget'):
        super().__init__(parent)
        self.setObjectName(object_name)


class NexusScrollArea(QtWidgets.QScrollArea):
    def __init__(self, parent=None, *, object_name='NexusScrollArea', widget_resizable=True):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setWidgetResizable(bool(widget_resizable))
        self.setFrameShape(QtWidgets.QFrame.NoFrame)


class NexusSplitter(QtWidgets.QSplitter):
    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None, *, object_name='NexusSplitter'):
        super().__init__(orientation, parent)
        self.setObjectName(object_name)
        self.setChildrenCollapsible(False)


class NexusContextMenu(NexusMenu):
    """Specialized menu wrapper intended for right-click context menus."""

    def __init__(self, title='', parent=None, *, object_name='NexusContextMenu'):
        super().__init__(title=title, parent=parent, object_name=object_name)


class NexusTooltip:
    """Tooltip helper so callers do not need to reference QtWidgets directly."""

    @staticmethod
    def show_text(global_pos, text: str, widget=None, rect=None, duration_ms: int = -1):
        QtWidgets.QToolTip.showText(global_pos, str(text or ''), widget, rect, duration_ms)

    @staticmethod
    def hide_text():
        QtWidgets.QToolTip.hideText()

    @staticmethod
    def set_tooltip(widget, text: str):
        if widget is not None:
            widget.setToolTip(str(text or ''))


__all__ = [
    'NexusButton',
    'NexusCheckBox',
    'NexusComboBox',
    'NexusContextMenu',
    'NexusDoubleSpinBox',
    'NexusFrame',
    'NexusHierarchyView',
    'NexusLabel',
    'NexusListWidget',
    'NexusMenu',
    'NexusMenuBar',
    'NexusProgressBar',
    'NexusRadioButton',
    'NexusScrollArea',
    'NexusSection',
    'NexusSlider',
    'NexusSpinBox',
    'NexusSplitter',
    'NexusStackedWidget',
    'NexusSubWindow',
    'NexusTabWidget',
    'NexusTableEditor',
    'NexusTableView',
    'NexusTableWidget',
    'NexusTextEditor',
    'NexusTextInput',
    'NexusTooltip',
    'NexusTreeWidget',
]
