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
# File: pane.py
# Description: Implements the workspace pane widget that hosts tabbed tools and pane controls.
#============================================================================

from nexus_workspace.framework.qt import QtCore, QtWidgets

from .drop_overlay import WorkspaceDropOverlay, build_drop_regions
from .tab_bar import WorkspaceTabBar


class WorkspacePane(QtWidgets.QFrame):
    currentToolChanged = QtCore.pyqtSignal(object)
    _DRAG_EVENT_TYPES = {
        QtCore.QEvent.DragEnter,
        QtCore.QEvent.DragMove,
        QtCore.QEvent.DragLeave,
        QtCore.QEvent.Drop,
    }

    def __init__(self, manager, area, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.area = area
        self.pane_id = None
        self._tool_ids = []
        self.setObjectName("WorkspacePane")
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setAcceptDrops(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tab_widget = QtWidgets.QTabWidget(self)
        self.tab_widget.setObjectName("workspacePaneTabs")
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(False)
        self.tab_bar = WorkspaceTabBar(self, self.manager, self.tab_widget)
        self.tab_widget.setTabBar(self.tab_bar)
        self.tab_bar.renameRequested.connect(self.rename_tab)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._on_current_changed)
        layout.addWidget(self.tab_widget, 1)

        self.overlay = WorkspaceDropOverlay(self)
        self.overlay.setGeometry(self.rect())
        QtWidgets.QApplication.instance().installEventFilter(self)

    def bind_pane_id(self, pane_id):
        self.pane_id = pane_id

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.setGeometry(self.rect())

    def _on_current_changed(self, index):
        tool = self.current_tool()
        if self.pane_id:
            pane_node = self.manager.model.find_pane(self.pane_id)
            if pane_node is not None:
                pane_node.active_tool_id = self.tool_id_at(index)
        self.currentToolChanged.emit(tool)
        self.area.activeToolChanged.emit(tool)
        self._sync_window_title()

    def _sync_window_title(self):
        window = self.window()
        if hasattr(window, 'refresh_window_title'):
            window.refresh_window_title()

    def add_tool(self, tool, title, tool_id=None):
        index = self.tab_widget.addTab(tool, title)
        self._tool_ids.append(tool_id)
        self.tab_widget.setCurrentIndex(index)
        self._attach_tool_signals(tool, tool_id)
        self.currentToolChanged.emit(tool)
        self.area.activeToolChanged.emit(tool)
        self._sync_window_title()
        return index

    def insert_tool(self, index, tool, title, tool_id=None):
        index = self.tab_widget.insertTab(index, tool, title)
        self._tool_ids.insert(index, tool_id)
        self.tab_widget.setCurrentIndex(index)
        self._attach_tool_signals(tool, tool_id)
        self.currentToolChanged.emit(tool)
        self.area.activeToolChanged.emit(tool)
        self._sync_window_title()
        return index

    def _attach_tool_signals(self, tool, tool_id):
        self._install_drag_filters(tool)
        if hasattr(tool, 'titleChanged'):
            try:
                tool.titleChanged.disconnect(self._on_tool_title_changed)
            except Exception:
                pass
            tool.titleChanged.connect(self._on_tool_title_changed)
        if tool_id and hasattr(tool, '_nexus_tool_id') is False:
            setattr(tool, '_nexus_tool_id', tool_id)


    def _install_drag_filters(self, widget):
        if widget is None:
            return
        widget.setAcceptDrops(False)
        widget.installEventFilter(self)
        for child in widget.findChildren(QtWidgets.QWidget):
            child.setAcceptDrops(False)
            child.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() not in self._DRAG_EVENT_TYPES:
            return super().eventFilter(obj, event)

        if obj is self or not isinstance(obj, QtWidgets.QWidget):
            return super().eventFilter(obj, event)

        if obj is not self.tab_bar and not self.isAncestorOf(obj):
            return super().eventFilter(obj, event)

        mime = getattr(event, 'mimeData', None)
        if mime is None or not event.mimeData().hasFormat("application/x-nexus-workspace-tab"):
            return super().eventFilter(obj, event)

        if event.type() == QtCore.QEvent.DragLeave:
            self.overlay.clear_zone()
            event.accept()
            return False

        local_pos = self.mapFromGlobal(obj.mapToGlobal(event.pos()))
        zone = self._zone_for_pos(local_pos)

        if event.type() in (QtCore.QEvent.DragEnter, QtCore.QEvent.DragMove):
            self.overlay.set_zone(zone, self._drop_regions())
            event.acceptProposedAction()
            return True

        if event.type() == QtCore.QEvent.Drop:
            self.overlay.clear_zone()
            self.manager.drop_drag_on_pane(self, zone)
            event.acceptProposedAction()
            return True

        return super().eventFilter(obj, event)

    def _on_tool_title_changed(self, title):
        tool = self.sender()
        index = self.index_of_tool(tool)
        if index >= 0:
            self.tab_widget.setTabText(index, title)
            tool_id = self.tool_id_at(index)
            if tool_id:
                self.manager.update_tool_title(tool_id, title)
            self._sync_window_title()


    def rename_tab(self, index, title):
        title = (title or '').strip()
        if not title:
            return

        tool = self.widget_at(index)
        tool_id = self.tool_id_at(index)
        if tool is None or tool_id is None:
            return

        self.tab_widget.setTabText(index, title)
        self.manager.update_tool_title(tool_id, title)

        setattr(tool, '_nexus_instance_name', title)
        if hasattr(tool, 'setWindowTitle'):
            tool.setWindowTitle(title)
        if hasattr(tool, 'titleChanged'):
            try:
                tool.titleChanged.emit(title)
            except Exception:
                pass

        self._sync_window_title()

    def close_tab(self, index):
        tool = self.widget_at(index)
        tool_id = self.tool_id_at(index)
        if tool is None or tool_id is None or self.pane_id is None:
            return
        self.manager.close_tool_in_pane(self.pane_id, tool_id)
        if hasattr(tool, 'close'):
            tool.close()

    def widget_at(self, index):
        if index < 0 or index >= self.tab_widget.count():
            return None
        return self.tab_widget.widget(index)

    def tool_id_at(self, index):
        if index < 0 or index >= len(self._tool_ids):
            return None
        return self._tool_ids[index]

    def tab_title_at(self, index):
        if index < 0 or index >= self.tab_widget.count():
            return ''
        return self.tab_widget.tabText(index)

    def index_of_tool(self, tool):
        for i in range(self.tab_widget.count()):
            if self.tab_widget.widget(i) is tool:
                return i
        return -1

    def index_of_tool_id(self, tool_id):
        try:
            return self._tool_ids.index(tool_id)
        except ValueError:
            return -1

    def current_tool(self):
        return self.tab_widget.currentWidget()

    def tab_count(self):
        return self.tab_widget.count()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-nexus-workspace-tab"):
            event.acceptProposedAction()
            self._update_overlay(event.pos())
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-nexus-workspace-tab"):
            event.acceptProposedAction()
            self._update_overlay(event.pos())
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.overlay.clear_zone()
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat("application/x-nexus-workspace-tab"):
            event.ignore()
            return
        zone = self._zone_for_pos(event.pos())
        self.overlay.clear_zone()
        self.manager.drop_drag_on_pane(self, zone)
        event.acceptProposedAction()

    def _update_overlay(self, pos):
        self.overlay.set_zone(self._zone_for_pos(pos), self._drop_regions())

    def _drop_regions(self):
        return build_drop_regions(self.rect(), self.tab_widget.tabBar().geometry())

    def _zone_for_pos(self, pos):
        regions = self._drop_regions()
        if regions['tab'].contains(pos) or regions['center'].contains(pos):
            return 'center'

        content = regions['content']
        if not content.contains(pos):
            pos = QtCore.QPoint(
                max(content.left(), min(content.right(), pos.x())),
                max(content.top(), min(content.bottom(), pos.y())),
            )

        candidates = []
        for key in ('left', 'right', 'top', 'bottom'):
            if regions[key].contains(pos):
                candidates.append(key)

        if not candidates:
            distances = {
                'left': abs(pos.x() - regions['left'].right()),
                'right': abs(pos.x() - regions['right'].left()),
                'top': abs(pos.y() - regions['top'].bottom()),
                'bottom': abs(pos.y() - regions['bottom'].top()),
            }
            return min(distances, key=distances.get)

        if len(candidates) == 1:
            return candidates[0]

        distances = {
            'left': abs(pos.x() - regions['left'].right()),
            'right': abs(pos.x() - regions['right'].left()),
            'top': abs(pos.y() - regions['top'].bottom()),
            'bottom': abs(pos.y() - regions['bottom'].top()),
        }
        return min(candidates, key=lambda key: distances[key])
