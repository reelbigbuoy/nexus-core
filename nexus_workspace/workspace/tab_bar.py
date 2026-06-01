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
# File: tab_bar.py
# Description: Provides the customized tab bar used by workspace panes.
#============================================================================

from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets


class _VisibleCloseButton(QtWidgets.QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAutoRaise(True)
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setFixedSize(16, 16)
        self.setIconSize(QtCore.QSize(10, 10))
        self._refresh_icon()
        self.setStyleSheet(
            "QToolButton { border: none; padding: 0px; margin: 0px; background: rgba(255, 255, 255, 0.08); border-radius: 8px; }"
            "QToolButton:hover { background: rgba(255, 255, 255, 0.16); border-radius: 8px; }"
            "QToolButton:pressed { background: rgba(255, 255, 255, 0.22); border-radius: 8px; }"
        )

    def _refresh_icon(self):
        icon = self.style().standardIcon(QtWidgets.QStyle.SP_TitleBarCloseButton)
        self.setIcon(icon)

    def changeEvent(self, event):
        if event.type() in (QtCore.QEvent.StyleChange, QtCore.QEvent.PaletteChange):
            self._refresh_icon()
        super().changeEvent(event)


class WorkspaceTabBar(QtWidgets.QTabBar):
    detachRequested = QtCore.pyqtSignal(int, QtCore.QPoint)
    renameRequested = QtCore.pyqtSignal(int, str)

    def __init__(self, pane, manager, parent=None):
        super().__init__(parent)
        self.pane = pane
        self.manager = manager
        self._drag_start_pos = None
        self.setAcceptDrops(True)
        self.setMovable(False)
        self.setElideMode(QtCore.Qt.ElideRight)
        self.setUsesScrollButtons(True)
        self.setTabsClosable(True)
        self._rename_editor = None
        self._rename_index = -1

    def tabInserted(self, index):
        super().tabInserted(index)
        self._install_close_button(index)

    def _install_close_button(self, index):
        button = _VisibleCloseButton(self)
        button.clicked.connect(self._on_close_button_clicked)
        self.setTabButton(index, QtWidgets.QTabBar.RightSide, button)

    def _on_close_button_clicked(self):
        button = self.sender()
        for index in range(self.count()):
            if self.tabButton(index, QtWidgets.QTabBar.RightSide) is button:
                parent = self.parentWidget()
                if parent is not None and hasattr(parent, 'tabCloseRequested'):
                    parent.tabCloseRequested.emit(index)
                break



    def mouseDoubleClickEvent(self, event):
        # Tab rename is intentionally not double-click driven. Double-click is
        # reserved for future tab activation/open behavior and avoids accidental
        # rename sessions while switching tools quickly. Use right-click > Rename.
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        index = self.tabAt(event.pos())
        if index < 0:
            super().contextMenuEvent(event)
            return

        tool_id = self.pane.tool_id_at(index)
        group_manager = getattr(self.manager, 'tab_group_manager', None)
        current_group = group_manager.get_group_for_tool(tool_id) if group_manager is not None and tool_id else None

        menu = QtWidgets.QMenu(self)
        act_rename = menu.addAction("Rename Tab")
        menu.addSeparator()
        act_create_group = menu.addAction("Create Tab Group")
        act_remove_group = None
        act_rename_group = None
        act_color_group = None
        move_actions = {}

        groups = list(getattr(getattr(self.manager, 'model', None), 'tab_groups', {}).values())
        if groups:
            move_menu = menu.addMenu("Move To Tab Group")
            for group in groups:
                action = move_menu.addAction(group.label)
                action.setEnabled(current_group is None or group.group_id != current_group.group_id)
                move_actions[action] = group.group_id

        if current_group is not None:
            menu.addSeparator()
            act_remove_group = menu.addAction(f"Remove From {current_group.label}")
            act_rename_group = menu.addAction("Rename Current Group")
            act_color_group = menu.addAction("Change Current Group Color")

        chosen = menu.exec_(event.globalPos())
        if chosen is act_rename:
            self._begin_rename(index)
            event.accept()
            return
        if chosen is act_create_group and tool_id:
            label, ok = QtWidgets.QInputDialog.getText(self, "Create Tab Group", "Group name:")
            if ok:
                label = label.strip() or None
                group = self.manager.create_tab_group(label=label, tool_ids=[tool_id])
                if group is not None:
                    event.accept()
                    return
        if chosen in move_actions and tool_id:
            self.manager.move_tool_to_tab_group(tool_id, move_actions[chosen])
            event.accept()
            return
        if chosen is act_remove_group and tool_id:
            self.manager.remove_tool_from_tab_group(tool_id)
            event.accept()
            return
        if chosen is act_rename_group and current_group is not None:
            label, ok = QtWidgets.QInputDialog.getText(self, "Rename Tab Group", "Group name:", text=current_group.label)
            if ok and label.strip():
                self.manager.rename_tab_group(current_group.group_id, label.strip())
                event.accept()
                return
        if chosen is act_color_group and current_group is not None:
            color = QtWidgets.QColorDialog.getColor(QtGui.QColor(current_group.color), self, "Choose Tab Group Color")
            if color.isValid():
                self.manager.change_tab_group_color(current_group.group_id, color.name())
                event.accept()
                return
        super().contextMenuEvent(event)

    def _begin_rename(self, index):
        if index < 0 or index >= self.count():
            return
        self._finish_rename(commit=False)

        tab_rect = self.tabRect(index)
        editor_rect = QtCore.QRect(tab_rect)
        editor_rect.adjust(6, 4, -6, -4)

        close_button = self.tabButton(index, QtWidgets.QTabBar.RightSide)
        if close_button is not None:
            button_geom = close_button.geometry()
            if not button_geom.isNull():
                editor_rect.setRight(min(editor_rect.right(), button_geom.left() - 4))

        if editor_rect.width() < 40:
            return

        editor = QtWidgets.QLineEdit(self)
        editor.setObjectName('workspaceTabRenameEditor')
        editor.setFrame(False)
        editor.setText(self.tabText(index))
        editor.setGeometry(editor_rect)
        editor.selectAll()
        editor.editingFinished.connect(self._commit_rename_from_editor)
        editor.installEventFilter(self)
        editor.show()
        editor.setFocus(QtCore.Qt.MouseFocusReason)

        self._rename_editor = editor
        self._rename_index = index

    def _commit_rename_from_editor(self):
        self._finish_rename(commit=True)

    def _finish_rename(self, commit):
        editor = self._rename_editor
        index = self._rename_index
        if editor is None:
            return

        self._rename_editor = None
        self._rename_index = -1

        new_name = editor.text().strip()
        editor.removeEventFilter(self)
        editor.deleteLater()

        if commit and index >= 0 and index < self.count() and new_name and new_name != self.tabText(index):
            self.renameRequested.emit(index, new_name)

    def eventFilter(self, obj, event):
        if obj is self._rename_editor and event.type() == QtCore.QEvent.KeyPress:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self._finish_rename(commit=True)
                return True
            if event.key() == QtCore.Qt.Key_Escape:
                self._finish_rename(commit=False)
                return True
        return super().eventFilter(obj, event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-nexus-workspace-tab"):
            event.acceptProposedAction()
            self.pane._update_overlay(self.pane.mapFromGlobal(event.globalPos()))
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-nexus-workspace-tab"):
            event.acceptProposedAction()
            self.pane._update_overlay(self.pane.mapFromGlobal(event.globalPos()))
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.pane.overlay.clear_zone()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat("application/x-nexus-workspace-tab"):
            event.ignore()
            return
        zone = self.pane._zone_for_pos(self.pane.mapFromGlobal(event.globalPos()))
        self.pane.overlay.clear_zone()
        self.manager.drop_drag_on_pane(self.pane, zone)
        event.acceptProposedAction()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton and self._drag_start_pos is not None:
            if (event.pos() - self._drag_start_pos).manhattanLength() >= QtWidgets.QApplication.startDragDistance():
                index = self.tabAt(self._drag_start_pos)
                if index >= 0:
                    self._start_drag(index)
                    self._drag_start_pos = None
                    return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start_pos = None
        super().mouseReleaseEvent(event)

    def _start_drag(self, index):
        payload = self.manager.begin_drag(self.pane, index)
        if payload is None:
            return

        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setData("application/x-nexus-workspace-tab", payload.encode("utf-8"))
        drag.setMimeData(mime)

        pixmap = self.grab(self.tabRect(index))
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QtCore.QPoint(pixmap.width() // 2, min(12, pixmap.height() // 2)))

        result = drag.exec_(QtCore.Qt.MoveAction)
        if result == QtCore.Qt.IgnoreAction:
            self.manager.detach_drag_to_new_window(QtGui.QCursor.pos())
        self.manager.end_drag()