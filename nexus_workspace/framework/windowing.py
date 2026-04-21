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
# File: windowing.py
# Description: Provides reusable window, dialog, and chrome abstractions for Nexus Core.
#============================================================================

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from ..core.themes import get_theme_manager
from ..workspace.frameless import FrameInteractionEventFilter, FramelessWindowController, TitleBarEventFilter


def load_nexus_icon() -> QtGui.QIcon:
    """Return the shared Nexus application icon when available."""
    icon_path = Path(__file__).resolve().parents[1] / 'assets' / 'icons' / 'nexus_icon.png'
    if icon_path.exists():
        return QtGui.QIcon(str(icon_path))
    return QtGui.QIcon()


class NexusTitleBar(QtWidgets.QWidget):
    """Reusable Nexus title bar widget for frameless ecosystem windows."""

    minimizeRequested = QtCore.pyqtSignal()
    maximizeRestoreRequested = QtCore.pyqtSignal()
    closeRequested = QtCore.pyqtSignal()

    def __init__(self, title='', parent=None, show_minimize=True, show_maximize=False, show_close=True):
        super().__init__(parent)
        self.setObjectName('titleBar')
        self.setFixedHeight(36)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(6)

        self.iconLabel = QtWidgets.QLabel(self)
        self.iconLabel.setObjectName('titleIconLabel')
        self.iconLabel.setFixedSize(18, 18)
        self.iconLabel.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.iconLabel, 0, QtCore.Qt.AlignVCenter)

        self.leadingHost = QtWidgets.QWidget(self)
        self.leadingHost.setObjectName('titleMenuHost')
        self.leadingLayout = QtWidgets.QHBoxLayout(self.leadingHost)
        self.leadingLayout.setContentsMargins(0, 0, 0, 0)
        self.leadingLayout.setSpacing(2)
        self.leadingHost.hide()
        layout.addWidget(self.leadingHost, 0)

        layout.addStretch(1)

        self.titleLabel = QtWidgets.QLabel(title, self)
        self.titleLabel.setObjectName('titleLabel')
        self.titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.titleLabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        layout.addWidget(self.titleLabel, 1)

        layout.addStretch(1)

        self.windowControls = QtWidgets.QWidget(self)
        self.windowControls.setObjectName('titleWindowControls')
        controls = QtWidgets.QHBoxLayout(self.windowControls)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(0)

        self.btnMinimize = QtWidgets.QPushButton('—', self)
        self.btnMinimize.setObjectName('btnMinimize')
        self.btnMinimize.setToolTip('Minimize')
        self.btnMinimize.clicked.connect(self.minimizeRequested.emit)
        self.btnMinimize.setVisible(bool(show_minimize))
        controls.addWidget(self.btnMinimize)

        self.btnMaximize = QtWidgets.QPushButton('□', self)
        self.btnMaximize.setObjectName('btnMaximize')
        self.btnMaximize.setToolTip('Maximize')
        self.btnMaximize.clicked.connect(self.maximizeRestoreRequested.emit)
        self.btnMaximize.setVisible(bool(show_maximize))
        controls.addWidget(self.btnMaximize)

        self.btnClose = QtWidgets.QPushButton('✕', self)
        self.btnClose.setObjectName('btnClose')
        self.btnClose.setToolTip('Close')
        self.btnClose.clicked.connect(self.closeRequested.emit)
        self.btnClose.setVisible(bool(show_close))
        controls.addWidget(self.btnClose)

        layout.addWidget(self.windowControls, 0)

    def set_title(self, title):
        self.titleLabel.setText(str(title or ''))

    def set_window_icon(self, icon):
        if icon is None or getattr(icon, 'isNull', lambda: True)():
            self.iconLabel.clear()
            return
        self.iconLabel.setPixmap(icon.pixmap(18, 18))

    def add_leading_widget(self, widget):
        if widget is None:
            return
        self.leadingHost.show()
        self.leadingLayout.addWidget(widget)

    def set_maximized(self, maximized):
        self.btnMaximize.setText('❐' if maximized else '□')
        self.btnMaximize.setToolTip('Restore' if maximized else 'Maximize')


class NexusChromeMixin(FramelessWindowController):
    """Shared frameless chrome behavior for Nexus-owned windows and dialogs."""

    RESIZE_MARGIN = 10
    WINDOW_KIND = 'window'

    def _init_nexus_chrome(self, *, title='', show_minimize=True, show_maximize=False, show_close=True):
        self.theme_manager = getattr(self, 'theme_manager', None) or get_theme_manager()
        self._drag_active = False
        self._drag_pos = QtCore.QPoint()
        self._normal_geometry = self.geometry()
        self._resize_active = False
        self._resize_edges = set()
        self._resize_start_global = QtCore.QPoint()
        self._resize_start_geometry = QtCore.QRect()
        self._titlebar_drag_widgets = []
        self._titlebar_filter = TitleBarEventFilter(self)
        self._frame_filter = FrameInteractionEventFilter(self)
        self._titlebar_buttons = {}
        self._build_nexus_chrome(title=title, show_minimize=show_minimize, show_maximize=show_maximize, show_close=show_close)
        self.install_titlebar_drag_filter()
        self.install_frame_interaction_filter()
        self.theme_manager.themeChanged.connect(self._on_nexus_theme_changed)
        self._apply_nexus_window_icon()

    def _chrome_surface_object_name(self):
        return 'nexusDialogSurface' if self.WINDOW_KIND == 'dialog' else 'nexusWindowSurface'

    def _chrome_content_object_name(self):
        return 'nexusDialogContent' if self.WINDOW_KIND == 'dialog' else 'nexusWindowContent'

    def _build_nexus_chrome(self, title, show_minimize, show_maximize, show_close):
        self.titleBar = NexusTitleBar(
            title=title,
            parent=self,
            show_minimize=show_minimize,
            show_maximize=show_maximize,
            show_close=show_close,
        )
        self.titleBar.minimizeRequested.connect(self.showMinimized)
        self.titleBar.maximizeRestoreRequested.connect(self.toggle_maximize_restore)
        self.titleBar.closeRequested.connect(self._handle_nexus_close_requested)
        self._titlebar_drag_widgets = [self.titleBar, self.titleBar.iconLabel, self.titleBar.titleLabel]
        self._titlebar_buttons = {
            'minimize': self.titleBar.btnMinimize,
            'maximize': self.titleBar.btnMaximize,
            'close': self.titleBar.btnClose,
        }

    def _handle_nexus_close_requested(self):
        self.close()

    def _apply_nexus_window_icon(self):
        icon = self._resolve_nexus_window_icon()
        if icon is not None and not icon.isNull():
            self.setWindowIcon(icon)
            if hasattr(self, 'titleBar'):
                self.titleBar.set_window_icon(icon)

    def _resolve_nexus_window_icon(self):
        icon = QtGui.QIcon()
        if hasattr(self, 'windowIcon'):
            try:
                icon = self.windowIcon()
            except Exception:
                icon = QtGui.QIcon()
        if icon is None or icon.isNull():
            parent = self.parentWidget() if hasattr(self, 'parentWidget') else None
            if parent is not None:
                try:
                    icon = parent.windowIcon()
                except Exception:
                    icon = QtGui.QIcon()
        if icon is None or icon.isNull():
            icon = QtWidgets.QApplication.windowIcon()
        if icon is None or icon.isNull():
            icon = load_nexus_icon()
        return icon

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, 'titleBar'):
            self.titleBar.set_title(title)

    def titlebar_can_drag(self, pos):
        child = self.titleBar.childAt(pos)
        return not isinstance(child, QtWidgets.QAbstractButton)

    def _titlebar_can_drag(self, pos):
        return self.titlebar_can_drag(pos)

    def _start_window_drag(self, global_pos):
        self.start_window_drag(global_pos)

    def _perform_window_drag(self, global_pos):
        self.perform_window_drag(global_pos)

    def _stop_window_drag(self):
        self.stop_window_drag()

    def _detect_resize_edges(self, pos):
        return self.detect_resize_edges(pos)

    def _update_cursor_for_position(self, pos):
        self.update_cursor_for_position(pos)

    def _perform_resize(self, global_pos):
        self.perform_resize(global_pos)

    def toggle_maximize_restore(self):
        maximize_button = self._titlebar_buttons.get('maximize') if hasattr(self, '_titlebar_buttons') else None
        if maximize_button is None or not maximize_button.isVisible():
            return
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_titlebar_window_state()

    def _sync_titlebar_window_state(self):
        if hasattr(self, 'titleBar'):
            self.titleBar.set_maximized(self.isMaximized())

    def add_titlebar_leading_widget(self, widget):
        if hasattr(self, 'titleBar'):
            self.titleBar.add_leading_widget(widget)

    def _on_nexus_theme_changed(self, *_args):
        if hasattr(self, 'titleBar'):
            self.titleBar.update()
        self.update()

    def closeEvent(self, event):
        try:
            self.theme_manager.themeChanged.disconnect(self._on_nexus_theme_changed)
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)


class NexusDialogBase(QtWidgets.QDialog, NexusChromeMixin):
    """Base class for Nexus-themed frameless dialogs."""

    WINDOW_KIND = 'dialog'

    def __init__(
        self,
        title='',
        parent=None,
        *,
        modal=True,
        show_minimize=False,
        show_maximize=False,
        show_close=True,
    ):
        super().__init__(parent)
        self.setObjectName('NexusDialogBase')
        self.setModal(bool(modal))
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        self.setMinimumSize(420, 260)
        self._init_nexus_chrome(title=title, show_minimize=show_minimize, show_maximize=show_maximize, show_close=show_close)
        self._build_dialog_layout()

    def _build_dialog_layout(self):
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(1, 1, 1, 1)
        root_layout.setSpacing(0)

        self.surfaceFrame = QtWidgets.QFrame(self)
        self.surfaceFrame.setObjectName(self._chrome_surface_object_name())
        self.surfaceFrame.setFrameShape(QtWidgets.QFrame.NoFrame)
        root_layout.addWidget(self.surfaceFrame, 1)

        surface_layout = QtWidgets.QVBoxLayout(self.surfaceFrame)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)
        surface_layout.addWidget(self.titleBar, 0)

        self.contentFrame = QtWidgets.QFrame(self.surfaceFrame)
        self.contentFrame.setObjectName(self._chrome_content_object_name())
        self.contentFrame.setFrameShape(QtWidgets.QFrame.NoFrame)
        surface_layout.addWidget(self.contentFrame, 1)

        self.contentLayout = QtWidgets.QVBoxLayout(self.contentFrame)
        self.contentLayout.setContentsMargins(12, 12, 12, 12)
        self.contentLayout.setSpacing(10)

    def _handle_nexus_close_requested(self):
        self.reject()

    def content_layout(self):
        return self.contentLayout

    def _on_nexus_theme_changed(self, *_args):
        super()._on_nexus_theme_changed(*_args)
        if hasattr(self, 'contentFrame'):
            self.contentFrame.update()


class NexusWindowBase(QtWidgets.QMainWindow, NexusChromeMixin):
    """Base class for Nexus-themed primary and floating tool windows."""

    WINDOW_KIND = 'window'

    def __init__(
        self,
        title='',
        parent=None,
        *,
        show_minimize=True,
        show_maximize=True,
        show_close=True,
    ):
        super().__init__(parent)
        self.setObjectName('NexusWindowBase')
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self._init_nexus_chrome(title=title, show_minimize=show_minimize, show_maximize=show_maximize, show_close=show_close)
        self.setMenuWidget(self.titleBar)
        self._sync_titlebar_window_state()

    def _handle_nexus_close_requested(self):
        self.close()


class NexusMessageDialog(NexusDialogBase):
    """Small themed message dialog used in place of raw QMessageBox."""

    def __init__(self, title, message, *, parent=None, level='info', details='', buttons=None):
        super().__init__(title, parent=parent, modal=True, show_close=True)
        self.resize(520, 220)
        self._result = QtWidgets.QDialog.Rejected
        self._buttons = buttons or [
            (QtWidgets.QDialogButtonBox.Ok, QtWidgets.QDialog.Accepted),
        ]
        layout = self.content_layout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(12)
        icon_label = QtWidgets.QLabel(self)
        icon_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        icon_label.setFixedWidth(36)
        icon = self._icon_for_level(level)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(24, 24))
        row.addWidget(icon_label, 0)

        text_col = QtWidgets.QVBoxLayout()
        body = QtWidgets.QLabel(message, self)
        body.setWordWrap(True)
        body.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        text_col.addWidget(body, 0)
        if details:
            detail_edit = QtWidgets.QPlainTextEdit(self)
            detail_edit.setReadOnly(True)
            detail_edit.setPlainText(details)
            detail_edit.setMaximumBlockCount(2000)
            detail_edit.setMinimumHeight(90)
            text_col.addWidget(detail_edit, 1)
        row.addLayout(text_col, 1)
        layout.addLayout(row, 1)

        button_box = QtWidgets.QDialogButtonBox(parent=self)
        for standard_button, role_result in self._buttons:
            button = button_box.addButton(standard_button)
            button.clicked.connect(lambda _checked=False, result=role_result: self._finish(result))
        layout.addWidget(button_box, 0)

    def _finish(self, result):
        self._result = result
        if result == QtWidgets.QDialog.Accepted:
            self.accept()
        else:
            self.reject()

    @staticmethod
    def _icon_for_level(level):
        style = QtWidgets.QApplication.style()
        mapping = {
            'info': QtWidgets.QStyle.SP_MessageBoxInformation,
            'warning': QtWidgets.QStyle.SP_MessageBoxWarning,
            'critical': QtWidgets.QStyle.SP_MessageBoxCritical,
        }
        return style.standardIcon(mapping.get(level, QtWidgets.QStyle.SP_MessageBoxInformation))

    @classmethod
    def information(cls, parent, title, message, details=''):
        dialog = cls(title, message, parent=parent, level='info', details=details)
        dialog.exec_()
        return dialog._result

    @classmethod
    def warning(cls, parent, title, message, details=''):
        dialog = cls(title, message, parent=parent, level='warning', details=details)
        dialog.exec_()
        return dialog._result

    @classmethod
    def critical(cls, parent, title, message, details=''):
        dialog = cls(title, message, parent=parent, level='critical', details=details)
        dialog.exec_()
        return dialog._result