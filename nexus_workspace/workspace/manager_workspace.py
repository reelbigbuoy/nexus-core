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
# File: manager_workspace.py
# Description: Coordinates workspace model management, rendering, and persistence integration.
#============================================================================

from dataclasses import dataclass

from nexus_workspace.framework.qt import QtCore, QtWidgets

from .controller import WorkspaceController
from .layout_model import PaneNode, SplitNode, WorkspaceModel
from .renderer import WorkspaceRenderer


@dataclass
class TabDragTransaction:
    source_pane_id: str
    source_window_id: str
    tool_id: str


class WorkspaceManager:
    def __init__(self, parent=None):
        self._windows = []
        self._drag_tx = None
        self._next_tool_number = 1
        self._default_plugin_manager = None
        self.model = WorkspaceModel()
        self.session_manager = None
        self.controller = WorkspaceController(self)
        self.renderer = WorkspaceRenderer(self)

    def register_window(self, window):
        if window not in self._windows:
            self._windows.append(window)
        if getattr(window, 'plugin_manager', None) is not None and self._default_plugin_manager is None:
            self._default_plugin_manager = window.plugin_manager
        self.model.register_window(window.window_id, is_primary=window.is_primary)

    def windows(self):
        return list(self._windows)

    def primary_window(self):
        for window in self._windows:
            if getattr(window, 'is_primary', False):
                return window
        return self._windows[0] if self._windows else None

    def promote_primary_window(self):
        if not self._windows:
            return None
        if any(getattr(window, 'is_primary', False) for window in self._windows):
            return self.primary_window()
        new_primary = self._windows[0]
        new_primary.is_primary = True
        return new_primary

    def unregister_window(self, window):
        if window in self._windows:
            self._windows.remove(window)
        self.model.unregister_window(window.window_id)

    def register_tool(self, widget, title, plugin_id="", tool_type_id="", tool_id=None):
        return self.model.register_tool(widget, title, plugin_id=plugin_id, tool_type_id=tool_type_id, tool_id=tool_id)

    def render_window(self, window):
        window_node = self.model.windows.get(window.window_id)
        if window_node is not None:
            self.model.normalize_window(window_node)
        self.renderer.render_window(window)
        self.renderer.cleanup_stale_panes()
        window.refresh_window_title()

    def render_all(self):
        for window in list(self._windows):
            window_node = self.model.windows.get(window.window_id)
            if window_node is not None:
                self.model.normalize_window(window_node)
            self.renderer.render_window(window)
        self.renderer.cleanup_stale_panes()
        for window in list(self._windows):
            window.refresh_window_title()
        self._cleanup_empty_detached_windows()
        self.ensure_all_windows_visible()

    def begin_drag(self, source_pane, index):
        tool = source_pane.widget_at(index)
        if tool is None:
            return None
        tool_id = source_pane.tool_id_at(index)
        if tool_id is None:
            return None
        self._drag_tx = TabDragTransaction(
            source_pane_id=source_pane.pane_id,
            source_window_id=source_pane.area.window_id,
            tool_id=tool_id,
        )
        return f"pane:{source_pane.pane_id}:tool:{tool_id}"

    def end_drag(self):
        self._drag_tx = None

    def add_tool_to_window(self, window, tool_id, target_pane_id=None):
        pane_id = self.controller.add_tool_to_window(window.window_id, tool_id, target_pane_id=target_pane_id)
        self.render_window(window)
        return pane_id

    def detach_drag_to_new_window(self, global_pos):
        if not self._drag_tx:
            return None
        source_window = self.window_by_id(self._drag_tx.source_window_id)
        if source_window is None:
            return None
        window = self.create_workspace_window(
            plugin_manager=getattr(source_window, 'plugin_manager', None),
            theme_name=getattr(source_window, 'current_theme_name', None),
            is_primary=False,
        )
        self.controller.detach_tool_to_new_window(
            self._drag_tx.source_pane_id,
            self._drag_tx.tool_id,
            window.window_id,
        )
        self.render_all()
        window.move(global_pos - window.rect().center())
        window.show()
        window.raise_()
        return window

    def drop_drag_on_pane(self, target_pane, zone):
        if not self._drag_tx:
            return None
        pane_id = self.controller.move_tool(
            self._drag_tx.source_pane_id,
            self._drag_tx.tool_id,
            target_pane.pane_id,
            zone,
        )
        self.render_all()
        return pane_id

    def close_tool_in_pane(self, pane_id, tool_id):
        window = self.model.find_window_for_pane(pane_id)
        ok = self.controller.close_tool(pane_id, tool_id)
        if ok and window:
            ui_window = self.window_by_id(window.window_id)
            if ui_window:
                self.render_window(ui_window)
            self._cleanup_empty_detached_windows()
        return ok

    def update_tool_title(self, tool_id, title):
        self.model.update_tool_title(tool_id, title)

    def tools_for_window(self, window_id):
        window = self.model.windows.get(window_id)
        if window is None:
            return []
        tools = []
        for pane in self.model.iter_panes(window.root_node):
            for tool_id in pane.tool_ids:
                record = self.model.tools.get(tool_id)
                if record is not None:
                    tools.append(record.widget)
        return tools

    def current_tool_for_window(self, window_id):
        window = self.model.windows.get(window_id)
        if window is None:
            return None
        for pane in self.model.iter_panes(window.root_node):
            if pane.active_tool_id:
                record = self.model.tools.get(pane.active_tool_id)
                if record is not None:
                    return record.widget
        return None

    def preferred_pane_id(self, window_id):
        window = self.model.windows.get(window_id)
        if window is None:
            return None
        for pane in self.model.iter_panes(window.root_node):
            if pane.tool_ids:
                return pane.pane_id
        for pane in self.model.iter_panes(window.root_node):
            return pane.pane_id
        return None

    def window_by_id(self, window_id):
        for window in self._windows:
            if window.window_id == window_id:
                return window
        return None

    def create_workspace_window(self, plugin_manager=None, theme_name=None, is_primary=False):
        from nexus_workspace.workspace.workspace_window import WorkspaceWindow

        plugin_manager = plugin_manager or self._default_plugin_manager
        window = WorkspaceWindow(self, plugin_manager=plugin_manager, session_manager=self.session_manager, is_primary=is_primary)
        if theme_name:
            window.apply_theme(theme_name)
        window.resize(1200, 800)
        return window

    def _cleanup_empty_detached_windows(self):
        open_windows = list(self._windows)
        if len(open_windows) <= 1:
            return
        empty_windows = [window for window in open_windows if not self.tools_for_window(window.window_id)]
        windows_to_keep = 1 if len(empty_windows) >= len(open_windows) else 0
        for window in empty_windows:
            if windows_to_keep > 0:
                windows_to_keep -= 1
                continue
            window.close()



    def capture_live_layout(self):
        for window in list(self._windows):
            window_node = self.model.windows.get(window.window_id)
            if window_node is None:
                continue
            if hasattr(window, 'isMaximized') and not window.isMaximized():
                window_node.geometry = window.geometry()
            root_widget = getattr(getattr(window, 'workspace_area', None), '_root_widget', None)
            if root_widget is not None:
                self._capture_splitter_sizes(window_node.root_node, root_widget)

    def _capture_splitter_sizes(self, model_node, widget):
        if isinstance(model_node, SplitNode) and hasattr(widget, 'sizes'):
            try:
                model_node.sizes = list(widget.sizes())
            except Exception:
                model_node.sizes = []
            for child_node, child_widget in zip(model_node.children, [widget.widget(i) for i in range(widget.count())]):
                self._capture_splitter_sizes(child_node, child_widget)

    def reset_model(self):
        self.model = WorkspaceModel()
        self.session_manager = None
        self.controller.model = self.model

    def restore_from_state(self, primary_window, state, state_manager):
        for window in list(self._windows):
            if window is not primary_window:
                window.close()
        self._windows = [primary_window]
        self.reset_model()
        self.register_window(primary_window)

        session_state = state.get('session') or {}
        self._next_tool_number = session_state.get('next_tool_number', 1)
        platform_state = state.get('platform') or {}
        theme_pref = (((platform_state.get('preferences') or {}).get('theme') or {}).get('current'))
        window_states = session_state.get('windows', [])
        primary_state = next((item for item in window_states if item.get('is_primary')), window_states[0] if window_states else None)
        detached_states = [item for item in window_states if item is not primary_state]

        if primary_state is not None:
            self._restore_window(primary_window, primary_state, state_manager)

        for window_state in detached_states:
            window = self.create_workspace_window(
                plugin_manager=getattr(primary_window, 'plugin_manager', None),
                theme_name=window_state.get('theme_name', window_state.get('current_theme_name', theme_pref or getattr(primary_window, 'current_theme_name', 'Midnight'))),
                is_primary=False,
            )
            self._restore_window(window, window_state, state_manager)
            window.show()

        self.render_all()


    def _screen_geometries(self):
        """Return available geometries for every attached monitor."""
        app = QtWidgets.QApplication.instance()
        screens = app.screens() if app is not None else []
        geometries = []
        for screen in screens:
            try:
                available = screen.availableGeometry()
                if available is not None and not available.isNull():
                    geometries.append(QtCore.QRect(available))
            except Exception:
                pass
        if not geometries:
            geometries.append(QtCore.QRect(0, 0, 1280, 720))
        return geometries

    def _primary_screen_geometry(self):
        app = QtWidgets.QApplication.instance()
        try:
            screen = app.primaryScreen() if app is not None else None
            if screen is not None:
                available = screen.availableGeometry()
                if available is not None and not available.isNull():
                    return QtCore.QRect(available)
        except Exception:
            pass
        return self._screen_geometries()[0]

    def _available_desktop_rect(self):
        """Return the union of all currently visible monitor work areas."""
        rect = QtCore.QRect()
        for available in self._screen_geometries():
            rect = rect.united(available) if not rect.isNull() else QtCore.QRect(available)
        return rect

    def _coerce_int(self, value, default):
        try:
            return int(value)
        except Exception:
            return int(default)

    def _intersection_area(self, a, b):
        inter = a.intersected(b)
        if inter.isNull():
            return 0
        return max(0, inter.width()) * max(0, inter.height())

    def _screen_for_rect(self, rect, fallback_to_primary=True):
        """Choose the monitor that should own a restored/live window rect.

        If the rect intersects one or more monitors, keep it on the monitor
        with the largest visible overlap.  If the rect is completely off every
        monitor, use the primary screen as the safe recovery target.
        """
        screens = self._screen_geometries()
        if rect is None or rect.isNull():
            return self._primary_screen_geometry() if fallback_to_primary else screens[0]
        best = None
        best_area = 0
        for screen_rect in screens:
            area = self._intersection_area(rect, screen_rect)
            if area > best_area:
                best_area = area
                best = screen_rect
        if best is not None and best_area > 0:
            return QtCore.QRect(best)
        return self._primary_screen_geometry() if fallback_to_primary else QtCore.QRect(screens[0])

    def _rect_is_fully_visible(self, rect, screen_rect):
        """Return True only when the complete window rect is inside its target screen.

        The manual View > Bring Windows On Screen command should be an
        enforcement action, not only an emergency recovery action.  A window
        that is even partially off-screen should be pulled fully back inside
        the current monitor work area.
        """
        if rect is None or rect.isNull() or screen_rect.isNull():
            return False
        return screen_rect.contains(rect)

    def _safe_fallback_geometry(self, width=1200, height=800, screen_rect=None):
        screen_rect = QtCore.QRect(screen_rect or self._primary_screen_geometry())
        min_w, min_h = 640, 420
        width = max(min_w, min(int(width or 1200), max(min_w, screen_rect.width())))
        height = max(min_h, min(int(height or 800), max(min_h, screen_rect.height())))
        x = screen_rect.x() + max(0, (screen_rect.width() - width) // 2)
        y = screen_rect.y() + max(0, (screen_rect.height() - height) // 2)
        return QtCore.QRect(x, y, width, height)

    def _clamped_window_geometry(self, geometry):
        min_w, min_h = 640, 420
        raw_width = self._coerce_int(geometry.get('width', 1200), 1200)
        raw_height = self._coerce_int(geometry.get('height', 800), 800)
        raw_x = self._coerce_int(geometry.get('x', 0), 0)
        raw_y = self._coerce_int(geometry.get('y', 0), 0)
        candidate = QtCore.QRect(raw_x, raw_y, max(1, raw_width), max(1, raw_height))
        screen_rect = self._screen_for_rect(candidate, fallback_to_primary=True)

        width = max(min_w, min(raw_width, max(min_w, screen_rect.width())))
        height = max(min_h, min(raw_height, max(min_h, screen_rect.height())))
        candidate = QtCore.QRect(raw_x, raw_y, width, height)

        # Always enforce full visibility.  The previous recovery behavior only
        # moved windows that were completely off-screen or barely reachable,
        # which meant View > Bring Windows On Screen appeared to do nothing when
        # a window was partially off-screen.  This clamps every live/restored
        # window fully inside the best matching monitor while keeping it on the
        # monitor with the largest overlap.
        if not self._rect_is_fully_visible(candidate, screen_rect):
            max_x = screen_rect.right() - width + 1
            max_y = screen_rect.bottom() - height + 1
            min_x = screen_rect.left()
            min_y = screen_rect.top()
            x = max(min_x, min(candidate.x(), max_x))
            y = max(min_y, min(candidate.y(), max_y))
            return QtCore.QRect(x, y, width, height)

        return QtCore.QRect(candidate)

    def _restore_window(self, window, window_state, state_manager):
        root_node = state_manager.deserialize_layout_node(window_state.get('root_node'))
        self.model.windows[window.window_id].root_node = root_node
        self.model.normalize_window(self.model.windows[window.window_id])
        theme_name = window_state.get('theme_name', window_state.get('current_theme_name'))
        if theme_name:
            window.apply_theme(theme_name)
        for tool_state in window_state.get('tools', []):
            descriptor = getattr(window, 'plugin_manager', None).descriptor_for_tool(tool_state.get('tool_type_id')) if getattr(window, 'plugin_manager', None) else None
            if descriptor is None:
                continue
            title = tool_state.get('title') or descriptor.display_name
            plugin_context = getattr(getattr(window, 'plugin_manager', None), 'context', None)
            tool = descriptor.create_instance(parent=window, theme_name=getattr(window, 'current_theme_name', 'Midnight'), editor_title=title, plugin_context=plugin_context)
            tool._nexus_plugin_display_name = descriptor.display_name
            tool._nexus_instance_name = title
            tool._nexus_tool_type_id = descriptor.tool_type_id
            tool._nexus_plugin_id = descriptor.plugin_id
            if hasattr(tool, 'setWindowTitle'):
                tool.setWindowTitle(title)
            if hasattr(tool, 'load_state'):
                try:
                    tool.load_state(tool_state.get('state') or {})
                except Exception:
                    pass
            window.workspace_area.add_tool(
                tool,
                title,
                target_pane=tool_state.get('pane_id'),
                tool_id=tool_state.get('tool_id'),
                plugin_id=descriptor.plugin_id,
                tool_type_id=descriptor.tool_type_id,
            )
        geometry = window_state.get('geometry') or {}
        if geometry:
            window.setGeometry(self._clamped_window_geometry(geometry))
            if geometry.get('maximized'):
                window.showMaximized()
            else:
                self.ensure_window_is_visible(window)

    def ensure_window_is_visible(self, window):
        """Clamp a live workspace/floating window after monitor changes."""
        if window is None:
            return
        try:
            if hasattr(window, 'isMaximized') and window.isMaximized():
                return
            geometry = window.geometry()
            clamped = self._clamped_window_geometry({
                'x': geometry.x(),
                'y': geometry.y(),
                'width': geometry.width(),
                'height': geometry.height(),
            })
            if clamped != geometry:
                window.setGeometry(clamped)
            if hasattr(window, 'show'):
                window.show()
            if hasattr(window, 'raise_'):
                window.raise_()
        except Exception:
            pass

    def _recoverable_top_level_widgets(self):
        """Return Nexus-owned top-level widgets that can be safely repositioned."""
        widgets = []
        seen = set()
        for window in list(self._windows):
            if window is not None:
                widgets.append(window)
                seen.add(id(window))

        app = QtWidgets.QApplication.instance()
        if app is None:
            return widgets

        for widget in app.topLevelWidgets():
            if widget is None or id(widget) in seen:
                continue
            if not widget.isVisible():
                continue
            is_floating_dock = isinstance(widget, QtWidgets.QDockWidget) and widget.isFloating()
            is_nexus_workspace = hasattr(widget, 'workspace_manager') or hasattr(widget, 'window_id')
            if is_floating_dock or is_nexus_workspace:
                widgets.append(widget)
                seen.add(id(widget))
        return widgets

    def ensure_all_windows_visible(self):
        for window in self._recoverable_top_level_widgets():
            self.ensure_window_is_visible(window)

    def reset_layout_to_single_pane(self, primary_window=None):
        """Move all open tools into one visible pane on the primary window.

        This is a safety valve for corrupted layouts, off-screen detached
        windows, or confusing split arrangements.  It intentionally preserves
        open tool instances and their state.
        """
        primary = primary_window or self.primary_window()
        if primary is None:
            return

        # Preserve tool order by walking the current layout before replacing it.
        ordered_tool_ids = []
        for window_node in list(self.model.windows.values()):
            for pane in self.model.iter_panes(window_node.root_node):
                for tool_id in pane.tool_ids:
                    if tool_id in self.model.tools and tool_id not in ordered_tool_ids:
                        ordered_tool_ids.append(tool_id)

        if primary.window_id not in self.model.windows:
            self.register_window(primary)
        pane = PaneNode(tool_ids=ordered_tool_ids, active_tool_id=ordered_tool_ids[-1] if ordered_tool_ids else None)
        self.model.windows[primary.window_id].root_node = pane
        self.model.windows[primary.window_id].is_primary = True

        # Empty the detached model windows before rendering so their live tool
        # widgets are re-parented into the primary pane instead of being
        # destroyed with the detached workspace.
        for window_id, window_node in list(self.model.windows.items()):
            if window_id != primary.window_id:
                window_node.root_node = PaneNode()

        self.model.normalize_window(self.model.windows[primary.window_id])
        self.ensure_window_is_visible(primary)
        self.render_all()

        for window in list(self._windows):
            if window is not primary:
                try:
                    window.close()
                except Exception:
                    pass
        self.render_all()

    def make_next_tool_title(self, base_name="Tool"):
        title = "%s %s" % (base_name, self._next_tool_number)
        self._next_tool_number += 1
        return title
