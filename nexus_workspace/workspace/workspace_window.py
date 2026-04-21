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
# File: workspace_window.py
# Description: Defines secondary workspace window containers for detached workspace areas.
#============================================================================

import inspect
import json
import uuid
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from ..core.themes import build_stylesheet, get_theme_colors, get_theme_manager
from ..framework.actions import NexusCommandMenuBuilder, NexusCommandRegistry
from ..framework.windowing import NexusMessageDialog, NexusWindowBase, load_nexus_icon
from ..plugins.base import reset_tool_theme
from ..shared_widgets.command_palette import CommandPaletteDialog
from ..shared_widgets.shortcut_preferences import ShortcutPreferencesDialog
from ..shared_widgets.plugin_manager_dialog import PluginManagerDialog

_STANDARD_ROUTED_SHORTCUTS = {
    'ctrl+z',
    'ctrl+y',
    'ctrl+shift+z',
    'ctrl+x',
    'ctrl+c',
    'ctrl+v',
    'ctrl+f',
    'ctrl+h',
    'ctrl+r',
    'ctrl+s',
    'delete',
}
from .area import WorkspaceArea


class WorkspaceWindow(NexusWindowBase):
    RESIZE_MARGIN = 10

    def __init__(self, workspace_manager, plugin_manager=None, session_manager=None, is_primary=False, parent=None):
        self.workspace_manager = workspace_manager
        self.plugin_manager = plugin_manager
        self.session_manager = session_manager
        self.is_primary = is_primary
        self.theme_manager = get_theme_manager()
        self.current_theme_name = self.theme_manager.current_theme_name() or 'Midnight'
        self._next_tool_number = 1
        self.theme_actions = {}
        self.window_id = f"window_{uuid.uuid4().hex[:12]}"
        self._command_shortcuts = {}
        self._edit_shortcuts = {}
        self._command_palette = None
        self._max_recent_entries = 12
        self._recent_entries = []

        super().__init__('Nexus Core', parent=parent, show_minimize=True, show_maximize=True, show_close=True)
        self.theme_manager.themeChanged.connect(self._on_global_theme_changed)
        self._build_window_chrome()
        self.workspace_manager.register_window(self)
        self._sync_titlebar_window_state()

    def _build_window_chrome(self):
        self.titleIconLabel = self.titleBar.iconLabel
        self.titleLabel = self.titleBar.titleLabel
        self.btnMinimize = self.titleBar.btnMinimize
        self.btnMaximize = self.titleBar.btnMaximize
        self.btnClose = self.titleBar.btnClose
        self.titleWindowControls = self.titleBar.windowControls

        self.btnViewMenu = QtWidgets.QToolButton(self.titleBar)
        self.btnViewMenu.setObjectName('btnViewMenu')
        self.btnViewMenu.setText('View')
        self.btnViewMenu.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btnViewMenu.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.btnViewMenu.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btnViewMenu.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }")

        self.btnToolsMenu = QtWidgets.QToolButton(self.titleBar)
        self.btnToolsMenu.setObjectName('btnToolsMenu')
        self.btnToolsMenu.setText('Tools')
        self.btnToolsMenu.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btnToolsMenu.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.btnToolsMenu.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btnToolsMenu.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }")

        self.btnCommandsMenu = QtWidgets.QToolButton(self.titleBar)
        self.btnCommandsMenu.setObjectName('btnCommandsMenu')
        self.btnCommandsMenu.setText('Edit')
        self.btnCommandsMenu.setToolTip('Edit actions for the active tool or focused widget')
        self.btnCommandsMenu.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btnCommandsMenu.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.btnCommandsMenu.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btnCommandsMenu.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }")

        self.btnNexusMenu = QtWidgets.QToolButton(self.titleBar)
        self.btnNexusMenu.setObjectName('btnNexusMenu')
        self.btnNexusMenu.setText('Nexus')
        self.btnNexusMenu.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btnNexusMenu.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        self.btnNexusMenu.setFocusPolicy(QtCore.Qt.NoFocus)
        self.btnNexusMenu.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0px; }")
        self.titleMenuHost = QtWidgets.QWidget(self.titleBar)
        self.titleMenuHost.setObjectName('titleMenuHost')
        title_menu_layout = QtWidgets.QHBoxLayout(self.titleMenuHost)
        title_menu_layout.setContentsMargins(0, 0, 0, 0)
        title_menu_layout.setSpacing(2)
        title_menu_layout.addWidget(self.btnNexusMenu)
        title_menu_layout.addWidget(self.btnCommandsMenu)
        title_menu_layout.addWidget(self.btnViewMenu)
        title_menu_layout.addWidget(self.btnToolsMenu)
        self.add_titlebar_leading_widget(self.titleMenuHost)

        self.workspace_area = WorkspaceArea(self.workspace_manager, self, self)
        self.workspace_area.activeToolChanged.connect(self._on_active_tool_changed)
        self.setCentralWidget(self.workspace_area)

        self.statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(self.statusbar)
        self._install_status_branding()
        self._rebuild_workspace_menu()

    def _install_status_branding(self):
        branding = QtWidgets.QLabel('Nexus Core by Reel Big Buoy Company', self.statusbar)
        branding.setObjectName('nexusStatusBranding')
        branding.setContentsMargins(12, 0, 4, 0)
        self._status_branding_label = branding
        self.statusbar.addPermanentWidget(branding)

    def refresh_window_title(self):
        title = self._compose_window_title()
        self.titleLabel.setText(title)
        self.setWindowTitle(title)

    def _apply_window_icon(self):
        self._apply_nexus_window_icon()

    def _refresh_titlebar_icon(self):
        self._apply_nexus_window_icon()

    @staticmethod
    def _load_nexus_icon():
        return load_nexus_icon()

    def _compose_window_title(self):
        tool = self.workspace_manager.current_tool_for_window(self.window_id)
        if tool is None:
            return 'Nexus Core'

        instance_name = self._tool_instance_name(tool)
        if instance_name:
            return f'Nexus Core | {instance_name}'
        return 'Nexus Core'

    def _tool_instance_name(self, tool):
        if tool is None:
            return ''
        for record in self.workspace_manager.model.tools.values():
            if record is not None and record.widget is tool:
                return record.title or ''
        if hasattr(tool, 'windowTitle'):
            return tool.windowTitle() or ''
        return ''

    def _on_active_tool_changed(self, tool):
        self.refresh_window_title()
        plugin_context = getattr(self.plugin_manager, 'context', None) if self.plugin_manager is not None else None
        if plugin_context is not None:
            try:
                plugin_context.publish_active_tool_context(tool, window=self)
            except Exception:
                pass

    def create_detached_workspace_window(self):
        return self.workspace_manager.create_workspace_window(
            plugin_manager=self.plugin_manager,
            theme_name=self.current_theme_name,
            is_primary=False,
        )

    def _apply_theme_local(self, theme_name):
        self.current_theme_name = theme_name
        theme = get_theme_colors(theme_name)
        self.setStyleSheet(build_stylesheet(theme))
        for tool in self.workspace_area.all_tools():
            reset_tool_theme(tool, theme_name)

    def _on_global_theme_changed(self, theme_name):
        self._apply_theme_local(theme_name)

    def apply_theme(self, theme_name):
        if theme_name != self.theme_manager.current_theme_name():
            self.theme_manager.set_current_theme(theme_name)
        else:
            self._apply_theme_local(theme_name)
        self._refresh_theme_action_checks()

    def _rebuild_workspace_menu(self):
        file_menu = QtWidgets.QMenu(self.titleBar)
        file_menu.aboutToShow.connect(self._rebuild_file_menu)
        self.btnNexusMenu.setMenu(file_menu)
        self.fileMenu = file_menu

        edit_menu = QtWidgets.QMenu(self.titleBar)
        edit_menu.aboutToShow.connect(self._rebuild_edit_menu)
        self.btnCommandsMenu.setMenu(edit_menu)
        self.editMenu = edit_menu

        view_menu = QtWidgets.QMenu(self.titleBar)
        view_menu.aboutToShow.connect(self._rebuild_view_menu)
        self.btnViewMenu.setMenu(view_menu)
        self.viewMenu = view_menu

        tools_menu = QtWidgets.QMenu(self.titleBar)
        tools_menu.aboutToShow.connect(self._rebuild_tools_menu)
        self.btnToolsMenu.setMenu(tools_menu)
        self.toolsMenu = tools_menu

        self._install_command_palette_shortcut()
        self._install_edit_shortcuts()
        self._rebuild_command_shortcuts()

    def _rebuild_file_menu(self):
        menu = getattr(self, 'fileMenu', None)
        if menu is None:
            return
        menu.clear()

        new_file_menu = menu.addMenu('New File')
        self._populate_new_file_menu(new_file_menu)

        plugin_manager_action = menu.addAction('Plugin Manager…')
        plugin_manager_action.triggered.connect(self.show_plugin_manager)

        menu.addSeparator()

        new_workspace_action = menu.addAction('New Workspace')
        new_workspace_action.triggered.connect(self.open_new_workspace)

        open_file_action = menu.addAction('Open File…')
        open_file_action.triggered.connect(self.open_file)

        open_recent_menu = menu.addMenu('Open Recent')
        self._populate_open_recent_menu(open_recent_menu)

        menu.addSeparator()

        save_action = menu.addAction('Save')
        save_action.setShortcut(QtGui.QKeySequence.Save)
        save_action.triggered.connect(self.save_active_tool)

        save_as_action = menu.addAction('Save As…')
        save_as_action.triggered.connect(self.save_active_tool_as)

        save_all_action = menu.addAction('Save All')
        save_all_action.triggered.connect(self.save_all_tools)

        save_workspace_action = menu.addAction('Save Workspace…')
        save_workspace_action.triggered.connect(self.save_workspace_configuration)

        menu.addSeparator()

        command_palette_action = menu.addAction('Command Palette…')
        command_palette_action.setShortcut(QtGui.QKeySequence('Ctrl+Shift+P'))
        command_palette_action.triggered.connect(self.show_command_palette)

        themes_menu = menu.addMenu('Themes')
        self.theme_action_group = QtWidgets.QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        self.theme_actions = {}
        for category_name, theme_names in self.theme_manager.theme_names_by_category().items():
            category_menu = themes_menu.addMenu(category_name)
            for theme_name in theme_names:
                action = category_menu.addAction(theme_name)
                action.setCheckable(True)
                action.setChecked(theme_name == self.current_theme_name)
                action.triggered.connect(lambda checked=False, name=theme_name: self.apply_theme(name))
                self.theme_action_group.addAction(action)
                self.theme_actions[theme_name] = action

        preferences_action = menu.addAction('Preferences…')
        preferences_action.triggered.connect(self.show_shortcut_preferences)

        menu.addSeparator()

        close_tab_action = menu.addAction('Close Tab')
        close_tab_action.setShortcut(QtGui.QKeySequence.Close)
        close_tab_action.triggered.connect(self.close_active_tab)

        close_workspace_action = menu.addAction('Close Workspace')
        close_workspace_action.triggered.connect(self.close)

        exit_nexus_action = menu.addAction('Exit Nexus')
        exit_nexus_action.triggered.connect(self.exit_nexus)

        active_tool = self.active_tool()
        can_save = self._tool_supports_method(active_tool, 'save')
        can_save_as = self._tool_supports_method(active_tool, 'save_as') or self._tool_supports_method(active_tool, 'save_graph_to_file_as')
        save_action.setEnabled(can_save)
        save_as_action.setEnabled(can_save_as)
        close_tab_action.setEnabled(active_tool is not None)

    def _populate_new_file_menu(self, menu):
        descriptors = []
        if self.plugin_manager is not None:
            descriptors = sorted(self.plugin_manager.launchable_tool_descriptors(), key=lambda item: item.display_name.lower())
        if not descriptors:
            action = menu.addAction('No plugins available')
            action.setEnabled(False)
            return
        for descriptor in descriptors:
            action = menu.addAction(descriptor.display_name)
            action.triggered.connect(lambda checked=False, d=descriptor: self.open_tool_descriptor(d))

    def _populate_open_recent_menu(self, menu):
        entries = list(self.recent_entries())
        if not entries:
            action = menu.addAction('No recent files')
            action.setEnabled(False)
            return
        for entry in entries:
            title = entry.get('label') or Path(entry.get('path', '')).name or entry.get('path', '')
            action = menu.addAction(title)
            path = entry.get('path', '')
            kind = entry.get('kind', 'file')
            action.setToolTip(path)
            action.triggered.connect(lambda checked=False, p=path, k=kind: self._open_recent_entry(p, k))
        menu.addSeparator()
        clear_action = menu.addAction('Clear Recent')
        clear_action.triggered.connect(self.clear_recent_entries)

    def _rebuild_view_menu(self):
        menu = getattr(self, 'viewMenu', None)
        if menu is None:
            return
        menu.clear()
        if self.plugin_manager is None:
            action = menu.addAction('No views available')
            action.setEnabled(False)
            return
        descriptors = sorted(self.plugin_manager.view_tool_descriptors(), key=lambda item: item.display_name.lower())
        if not descriptors:
            action = menu.addAction('No views available')
            action.setEnabled(False)
            return
        for descriptor in descriptors:
            menu.addAction(
                descriptor.display_name,
                lambda checked=False, d=descriptor: self.open_tool_descriptor(d),
            )

    def _rebuild_tools_menu(self):
        menu = getattr(self, 'toolsMenu', None)
        if menu is None:
            return
        menu.clear()
        if self.plugin_manager is None:
            action = menu.addAction('No tools available')
            action.setEnabled(False)
            return
        descriptors = sorted(self.plugin_manager.launchable_tool_descriptors(), key=lambda item: item.display_name.lower())
        if not descriptors:
            action = menu.addAction('No tools available')
            action.setEnabled(False)
            return
        for descriptor in descriptors:
            menu.addAction(
                descriptor.display_name,
                lambda checked=False, d=descriptor: self.open_tool_descriptor(d),
            )

    def _rebuild_edit_menu(self):
        menu = getattr(self, 'editMenu', None)
        if menu is None:
            return
        menu.clear()

        added_any = False
        has_history = self._can_undo_active() or self._can_redo_active() or self._active_undo_stack() is not None
        if has_history:
            undo_action = menu.addAction('Undo')
            undo_action.triggered.connect(self.undo_active)
            undo_action.setEnabled(self._can_undo_active())

            redo_action = menu.addAction('Redo')
            redo_action.triggered.connect(self.redo_active)
            redo_action.setEnabled(self._can_redo_active())
            added_any = True

        edit_entries = []
        if self._supports_edit_operation('cut'):
            edit_entries.append(('Cut', QtGui.QKeySequence.Cut, self.cut_active))
        if self._supports_edit_operation('copy'):
            edit_entries.append(('Copy', QtGui.QKeySequence.Copy, self.copy_active))
        if self._supports_edit_operation('paste'):
            edit_entries.append(('Paste', QtGui.QKeySequence.Paste, self.paste_active))
        if edit_entries:
            if added_any:
                menu.addSeparator()
            for title, shortcut, callback in edit_entries:
                action = menu.addAction(title)
                action.triggered.connect(callback)
            added_any = True

        search_entries = []
        if self._has_find_support():
            search_entries.append(('Find', QtGui.QKeySequence.Find, self.find_in_active_context))
        if self._has_replace_support():
            search_entries.append(('Replace', QtGui.QKeySequence.Replace, self.replace_in_active_context))
        if search_entries:
            if added_any:
                menu.addSeparator()
            for title, shortcut, callback in search_entries:
                action = menu.addAction(title)
                action.triggered.connect(callback)
            added_any = True

        if not added_any:
            action = menu.addAction('No edit actions available')
            action.setEnabled(False)

    def show_plugin_manager(self):
        main = self._primary_window()
        records = main.plugin_records() if hasattr(main, 'plugin_records') else []
        overrides = dict(getattr(main, '_plugin_enablement_overrides', {}) or {})
        dialog = PluginManagerDialog(plugin_records=records, enablement_overrides=overrides, parent=self)
        if dialog.exec_() != QtWidgets.QDialog.Accepted:
            return False
        new_overrides = dialog.enablement_overrides()
        if hasattr(main, 'set_plugin_enablement_overrides'):
            main.set_plugin_enablement_overrides(new_overrides)
        else:
            main._plugin_enablement_overrides = dict(new_overrides)
        self._rebuild_file_menu()
        self._rebuild_view_menu()
        self._rebuild_tools_menu()
        self.statusbar.showMessage('Plugin preferences updated. Menu visibility refreshed; restart Nexus to fully apply load/unload changes.', 5000)
        return True

    def _primary_window(self):
        return self.workspace_manager.primary_window() or self

    def recent_entries(self):
        owner = self._primary_window()
        return list(getattr(owner, '_recent_entries', []))

    def set_recent_entries(self, entries):
        owner = self._primary_window()
        owner._recent_entries = list(entries or [])

    def clear_recent_entries(self):
        self.set_recent_entries([])

    def open_new_workspace(self):
        window = self.create_detached_workspace_window()
        if window is not None:
            window.show()
            window.raise_()
            window.activateWindow()
        return window

    def _remember_recent_path(self, path, kind='file', label=None):
        path = str(path or '').strip()
        if not path:
            return
        entries = [item for item in self.recent_entries() if str(item.get('path', '')).strip().lower() != path.lower()]
        entry = {'path': path, 'kind': kind, 'label': label or Path(path).name}
        entries.insert(0, entry)
        self.set_recent_entries(entries[: getattr(self, '_max_recent_entries', 12)])

    def _open_recent_entry(self, path, kind='file'):
        if kind == 'workspace':
            self.load_workspace_configuration(path)
            return
        self.open_file(file_path=path)

    def _tool_supports_method(self, tool, method_name):
        return tool is not None and callable(getattr(tool, method_name, None))

    def _active_undo_stack(self):
        tool = self.active_tool()
        if tool is not None and hasattr(tool, 'get_undo_stack'):
            try:
                return tool.get_undo_stack()
            except Exception:
                return None
        return None

    def _can_undo_active(self):
        stack = self._active_undo_stack()
        if stack is None:
            return False
        try:
            return bool(stack.canUndo())
        except Exception:
            return False

    def _can_redo_active(self):
        stack = self._active_undo_stack()
        if stack is None:
            return False
        try:
            return bool(stack.canRedo())
        except Exception:
            return False

    def undo_active(self):
        stack = self._active_undo_stack()
        if stack is not None and hasattr(stack, 'undo'):
            stack.undo()

    def redo_active(self):
        stack = self._active_undo_stack()
        if stack is not None and hasattr(stack, 'redo'):
            stack.redo()

    def _focused_widget(self):
        widget = QtWidgets.QApplication.focusWidget()
        if widget is None:
            return None
        return widget

    def _supports_focused_widget_method(self, method_name):
        widget = self._focused_widget()
        return callable(getattr(widget, method_name, None))

    def _supports_tool_method(self, method_name):
        tool = self.active_tool()
        return callable(getattr(tool, method_name, None))

    def _supports_edit_operation(self, method_name):
        return self._supports_focused_widget_method(method_name) or self._supports_tool_method(method_name)

    def _invoke_edit_operation(self, method_name):
        widget = self._focused_widget()
        method = getattr(widget, method_name, None)
        if callable(method):
            return method()
        tool = self.active_tool()
        method = getattr(tool, method_name, None) if tool is not None else None
        if callable(method):
            return method()
        return None

    def cut_active(self):
        return self._invoke_edit_operation('cut')

    def copy_active(self):
        return self._invoke_edit_operation('copy')

    def paste_active(self):
        return self._invoke_edit_operation('paste')

    def _active_tool_find_method(self):
        tool = self.active_tool()
        for method_name in ('show_find_replace', 'show_find', 'find_in_document'):
            method = getattr(tool, method_name, None) if tool is not None else None
            if callable(method):
                return method
        return None

    def _active_tool_replace_method(self):
        tool = self.active_tool()
        for method_name in ('show_find_replace', 'show_replace', 'replace_in_document'):
            method = getattr(tool, method_name, None) if tool is not None else None
            if callable(method):
                return method
        return None

    def _focused_text_widget(self):
        focus = self._focused_widget()
        if isinstance(focus, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            return focus
        return None

    def _has_find_support(self):
        return self._active_tool_find_method() is not None or self._focused_text_widget() is not None

    def _has_replace_support(self):
        focus = self._focused_text_widget()
        return self._active_tool_replace_method() is not None or isinstance(focus, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit))

    def find_in_active_context(self):
        method = self._active_tool_find_method()
        if method is not None:
            return method()
        focus = self._focused_text_widget()
        if focus is not None:
            focus.setFocus()
        return None

    def replace_in_active_context(self):
        method = self._active_tool_replace_method()
        if method is not None:
            return method()
        focus = self._focused_text_widget()
        if isinstance(focus, (QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit)):
            focus.setFocus()
        return None

    def close_active_tab(self):
        tool = self.active_tool()
        if tool is None:
            return False
        parent = tool.parentWidget()
        while parent is not None:
            if hasattr(parent, 'index_of_tool') and hasattr(parent, 'close_tab'):
                index = parent.index_of_tool(tool)
                if index >= 0:
                    parent.close_tab(index)
                    return True
            parent = parent.parentWidget()
        return False

    def save_active_tool(self):
        tool = self.active_tool()
        if tool is None:
            return False
        method = getattr(tool, 'save', None)
        if callable(method):
            result = method()
            file_path = self._extract_tool_file_path(tool)
            if result and file_path:
                self._remember_recent_path(file_path, kind='file')
            return result
        return False

    def save_active_tool_as(self):
        tool = self.active_tool()
        if tool is None:
            return False
        for method_name in ('save_as', 'save_graph_to_file_as'):
            method = getattr(tool, method_name, None)
            if callable(method):
                result = method()
                file_path = self._extract_tool_file_path(tool)
                if result and file_path:
                    self._remember_recent_path(file_path, kind='file')
                return result
        return False

    def save_all_tools(self):
        saved_any = False
        for window in self.workspace_manager.windows():
            for tool in self.workspace_manager.tools_for_window(window.window_id):
                method = getattr(tool, 'save', None)
                if callable(method):
                    result = method()
                    file_path = self._extract_tool_file_path(tool)
                    if result and file_path:
                        self._remember_recent_path(file_path, kind='file')
                    saved_any = bool(result) or saved_any
        return saved_any

    def _extract_tool_file_path(self, tool):
        if tool is None:
            return None
        for attr in ('current_file_path',):
            value = getattr(tool, attr, None)
            if value:
                return value
        document_model = getattr(tool, 'document_model', None)
        if document_model is not None:
            value = getattr(document_model, 'file_path', None)
            if value:
                return value
        return None

    def _descriptor_matches_extension(self, descriptor, suffix):
        metadata = dict(getattr(descriptor, 'metadata', None) or {})
        extensions = [str(ext).lower() for ext in metadata.get('file_extensions', [])]
        return suffix.lower() in extensions

    def _descriptor_loads_path(self, descriptor, file_path):
        tool = self.active_tool()
        if tool is not None and getattr(tool, '_nexus_tool_type_id', None) == descriptor.tool_type_id:
            return self._load_path_into_tool(tool, file_path)
        new_tool = self.open_tool_descriptor(descriptor)
        if new_tool is None:
            return False
        return self._load_path_into_tool(new_tool, file_path)

    def _load_path_into_tool(self, tool, file_path):
        if tool is None:
            return False
        for method_name in ('load_from_path', 'load_graph_from_file'):
            method = getattr(tool, method_name, None)
            if callable(method):
                try:
                    result = method(file_path)
                except TypeError:
                    continue
                if result:
                    self._remember_recent_path(file_path, kind='file')
                return result
        method = getattr(tool, 'load', None)
        if callable(method):
            try:
                signature = inspect.signature(method)
                if len(signature.parameters) == 0:
                    result = method()
                else:
                    result = method(file_path)
            except Exception:
                return False
            if result:
                self._remember_recent_path(file_path, kind='file')
            return result
        return False

    def _workspace_state_contract(self, payload):
        if not isinstance(payload, dict):
            return False
        return str(payload.get('contract') or '').strip() == 'platform.persisted_state.v2'

    def _build_open_file_filter(self):
        filters = ['All Supported Files (*.json *.tdzn *.nexus-workspace.json *.nexusws.json)', 'Nexus Workspace (*.nexus-workspace.json *.nexusws.json)', 'JSON Files (*.json)', 'Test Designinator (*.tdzn)']
        seen = set(filters)
        if self.plugin_manager is not None:
            for descriptor in self.plugin_manager.tool_descriptors():
                file_filter = (dict(getattr(descriptor, 'metadata', None) or {})).get('file_open_filter')
                if file_filter and file_filter not in seen:
                    filters.append(file_filter)
                    seen.add(file_filter)
        return ';;'.join(filters)

    def open_file(self, file_path=None):
        if not file_path:
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open File', '', self._build_open_file_filter())
        if not file_path:
            return False
        path_obj = Path(file_path)
        suffix = path_obj.suffix.lower()
        payload = None
        if suffix == '.json' or file_path.lower().endswith('.nexus-workspace.json') or file_path.lower().endswith('.nexusws.json'):
            try:
                payload = json.loads(Path(file_path).read_text(encoding='utf-8'))
            except Exception:
                payload = None
        if self._workspace_state_contract(payload):
            return self.load_workspace_configuration(file_path)

        descriptors = []
        if self.plugin_manager is not None:
            descriptors = [d for d in self.plugin_manager.launchable_tool_descriptors() if self._descriptor_matches_extension(d, suffix)]
        active_tool = self.active_tool()
        if active_tool is not None:
            active_type = getattr(active_tool, '_nexus_tool_type_id', None)
            preferred = next((d for d in descriptors if d.tool_type_id == active_type), None)
            if preferred is not None:
                return self._descriptor_loads_path(preferred, file_path)
        if len(descriptors) == 1:
            return self._descriptor_loads_path(descriptors[0], file_path)
        if len(descriptors) > 1:
            items = [descriptor.display_name for descriptor in descriptors]
            choice, ok = QtWidgets.QInputDialog.getItem(self, 'Open File', 'Choose plugin for this file:', items, 0, False)
            if ok and choice:
                descriptor = next((d for d in descriptors if d.display_name == choice), None)
                if descriptor is not None:
                    return self._descriptor_loads_path(descriptor, file_path)
                return False
            return False
        if active_tool is not None and self._load_path_into_tool(active_tool, file_path):
            return True
        NexusMessageDialog.information(self, 'Open File', f'No plugin is configured to open:\n{file_path}')
        return False

    def save_workspace_configuration(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, 'Save Workspace Configuration', 'nexus-workspace.nexus-workspace.json', 'Nexus Workspace (*.nexus-workspace.json *.nexusws.json);;JSON Files (*.json);;All Files (*)')
        if not file_path:
            return False
        state = self.state_manager.save_workspace_state(self._primary_window()) if self.state_manager is not None else None
        if not state:
            return False
        Path(file_path).write_text(json.dumps(state, indent=2), encoding='utf-8')
        self._remember_recent_path(file_path, kind='workspace')
        self.statusbar.showMessage(f'Saved workspace configuration to {file_path}', 4000)
        return True

    def load_workspace_configuration(self, file_path=None):
        if not file_path:
            file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Load Workspace Configuration', '', 'Nexus Workspace (*.nexus-workspace.json *.nexusws.json);;JSON Files (*.json);;All Files (*)')
        if not file_path:
            return False
        try:
            payload = json.loads(Path(file_path).read_text(encoding='utf-8'))
        except Exception as exc:
            NexusMessageDialog.critical(self, 'Load Workspace Failed', f'Could not load workspace configuration:\n{exc}')
            return False
        if not self._workspace_state_contract(payload):
            NexusMessageDialog.warning(self, 'Load Workspace Failed', 'The selected file is not a Nexus workspace configuration.')
            return False
        primary = self._primary_window()
        if self.state_manager is None:
            return False
        restored = self.state_manager.restore_workspace_state(primary, payload)
        if restored:
            self._remember_recent_path(file_path, kind='workspace')
            primary.refresh_command_bindings()
            primary.statusbar.showMessage(f'Loaded workspace configuration from {file_path}', 4000)
        return restored

    def _install_edit_shortcuts(self):
        if getattr(self, '_edit_shortcuts', None):
            return
        shortcuts = {
            'undo': (QtGui.QKeySequence.Undo, self.undo_active),
            'redo': (QtGui.QKeySequence.Redo, self.redo_active),
            'redo_alt': (QtGui.QKeySequence('Ctrl+Shift+Z'), self.redo_active),
            'cut': (QtGui.QKeySequence.Cut, self.cut_active),
            'copy': (QtGui.QKeySequence.Copy, self.copy_active),
            'paste': (QtGui.QKeySequence.Paste, self.paste_active),
            'find': (QtGui.QKeySequence.Find, self.find_in_active_context),
            'replace': (QtGui.QKeySequence.Replace, self.replace_in_active_context),
        }
        for key, (sequence, callback) in shortcuts.items():
            shortcut = QtWidgets.QShortcut(sequence, self)
            shortcut.setContext(QtCore.Qt.ApplicationShortcut)
            shortcut.activated.connect(callback)
            self._edit_shortcuts[key] = shortcut

    def _install_command_palette_shortcut(self):
        if getattr(self, '_command_palette_shortcut', None) is not None:
            return
        self._command_palette_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+Shift+P'), self)
        self._command_palette_shortcut.setContext(QtCore.Qt.ApplicationShortcut)
        self._command_palette_shortcut.activated.connect(self.show_command_palette)

    def _rebuild_commands_menu(self):
        menu = getattr(self, 'commandsMenu', None)
        plugin_context = getattr(self.plugin_manager, 'context', None) if self.plugin_manager is not None else None
        if menu is None or plugin_context is None:
            return
        current_tool = self.active_tool() or self.workspace_manager.current_tool_for_window(self.window_id)
        if current_tool is not None:
            try:
                plugin_context.publish_active_tool_context(current_tool, window=self)
            except Exception:
                pass
        registry = NexusCommandRegistry(plugin_context, self)
        builder = NexusCommandMenuBuilder(registry)
        builder.build_menu(menu, include_palette_action=self.show_command_palette)

    def _rebuild_command_shortcuts(self):
        plugin_context = getattr(self.plugin_manager, 'context', None) if self.plugin_manager is not None else None
        if plugin_context is None:
            return
        for shortcut in getattr(self, '_command_shortcuts', {}).values():
            try:
                shortcut.activated.disconnect()
            except Exception:
                pass
            shortcut.setParent(None)
        self._command_shortcuts = {}
        registry = plugin_context.command_registry() or {}
        seen = set()
        for descriptor in registry.get('commands', []) if isinstance(registry, dict) else []:
            shortcut_text = str(descriptor.get('shortcut') or '').strip()
            if not shortcut_text or shortcut_text.lower() == 'ctrl+shift+p':
                continue
            normalized = shortcut_text.lower()
            if normalized in _STANDARD_ROUTED_SHORTCUTS:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(shortcut_text), self)
            shortcut.setContext(QtCore.Qt.ApplicationShortcut)
            shortcut.activated.connect(lambda shortcut_text=shortcut_text: self._execute_shortcut_commands(shortcut_text))
            self._command_shortcuts[normalized] = shortcut

    def _execute_shortcut_commands(self, shortcut_text):
        plugin_context = getattr(self.plugin_manager, 'context', None) if self.plugin_manager is not None else None
        if plugin_context is None:
            return None
        current_tool = self.active_tool() or self.workspace_manager.current_tool_for_window(self.window_id)
        if current_tool is not None:
            try:
                plugin_context.publish_active_tool_context(current_tool, window=self)
            except Exception:
                pass
        service = getattr(plugin_context, 'command_service', None)
        candidates = service.available_commands_for_shortcut(shortcut_text) if service is not None else []
        if not candidates:
            return None
        candidate = candidates[0]
        return self._execute_platform_command(candidate.get('command_id'))

    def show_command_palette(self):
        plugin_context = getattr(self.plugin_manager, 'context', None) if self.plugin_manager is not None else None
        if plugin_context is None:
            return
        current_tool = self.active_tool() or self.workspace_manager.current_tool_for_window(self.window_id)
        if current_tool is not None:
            try:
                plugin_context.publish_active_tool_context(current_tool, window=self)
            except Exception:
                pass
        dialog = CommandPaletteDialog(plugin_context, parent=self)
        dialog.open_and_focus()

    def show_shortcut_preferences(self):
        plugin_context = getattr(self.plugin_manager, 'context', None) if self.plugin_manager is not None else None
        if plugin_context is None:
            return
        dialog = ShortcutPreferencesDialog(plugin_context, parent=self)
        dialog.exec_()
        self.refresh_command_bindings()

    def refresh_command_bindings(self):
        self._rebuild_command_shortcuts()

    def _execute_platform_command(self, command_id):
        plugin_context = getattr(self.plugin_manager, 'context', None) if self.plugin_manager is not None else None
        if plugin_context is None:
            return None
        result = plugin_context.execute_command(command_id)
        if isinstance(result, dict) and result.get('handled'):
            self.statusbar.showMessage('Executed command: %s' % command_id, 2000)
        elif isinstance(result, dict) and result.get('error'):
            self.statusbar.showMessage('Command failed: %s' % result.get('error'), 4000)
        return result

    def _refresh_theme_action_checks(self):
        for theme_name, action in getattr(self, 'theme_actions', {}).items():
            action.setChecked(theme_name == self.current_theme_name)

    def _make_next_tool_title(self, base_name='Tool', tool_type_id=None):
        used_numbers = set()
        for record in self.workspace_manager.model.tools.values():
            if record is None:
                continue
            if tool_type_id and getattr(record, 'tool_type_id', '') != tool_type_id:
                continue
            title = str(getattr(record, 'title', '') or '')
            if not title.startswith(f'{base_name} '):
                continue
            suffix = title[len(base_name) + 1:].strip()
            if suffix.isdigit():
                used_numbers.add(int(suffix))
        number = 1
        while number in used_numbers:
            number += 1
        self._next_tool_number = max(self._next_tool_number, number + 1)
        return f'{base_name} {number}'

    def open_tool_by_id(self, tool_type_id, title=None):
        if self.plugin_manager is None:
            return None
        descriptor = self.plugin_manager.descriptor_for_tool(tool_type_id)
        if descriptor is None:
            return None
        return self.open_tool_descriptor(descriptor, title=title)

    def open_tool_descriptor(self, descriptor, title=None, target_pane=None):
        title = title or self._make_next_tool_title(descriptor.display_name, descriptor.tool_type_id)
        plugin_context = getattr(self.plugin_manager, 'context', None) if self.plugin_manager is not None else None
        tool = descriptor.create_instance(parent=self, theme_name=self.current_theme_name, editor_title=title, plugin_context=plugin_context)
        tool._nexus_plugin_display_name = descriptor.display_name
        tool._nexus_instance_name = title
        tool._nexus_tool_type_id = descriptor.tool_type_id
        tool._nexus_plugin_id = descriptor.plugin_id
        if hasattr(tool, 'setWindowTitle'):
            tool.setWindowTitle(title)
        self.workspace_area.add_tool(
            tool,
            title,
            target_pane=target_pane,
            plugin_id=descriptor.plugin_id,
            tool_type_id=descriptor.tool_type_id,
        )
        self.refresh_window_title()
        if hasattr(tool, 'focus_primary_surface'):
            tool.focus_primary_surface()
        plugin_context = getattr(self.plugin_manager, 'context', None) if self.plugin_manager is not None else None
        if plugin_context is not None:
            try:
                plugin_context.publish_active_tool_context(tool, window=self)
            except Exception:
                pass
        return tool

    def active_tool(self):
        focus = QtWidgets.QApplication.focusWidget()
        while focus is not None:
            for tool in self.workspace_area.all_tools():
                parent = focus
                while parent is not None:
                    if parent is tool:
                        return tool
                    parent = parent.parentWidget()
            focus = focus.parentWidget()
        return self.workspace_manager.current_tool_for_window(self.window_id)

    def toggle_maximize_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self._normal_geometry = self.geometry()
            self.showMaximized()
        self._sync_titlebar_window_state()

    def _update_maximize_button(self):
        icon_enum = QtWidgets.QStyle.SP_TitleBarNormalButton if self.isMaximized() else QtWidgets.QStyle.SP_TitleBarMaxButton
        self.btnMaximize.setText('')
        self.btnMaximize.setToolTip('Restore Down' if self.isMaximized() else 'Maximize')
        self.btnMaximize.setIcon(self.style().standardIcon(icon_enum))
        self.btnMaximize.setIconSize(QtCore.QSize(14, 14))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.WindowStateChange:
            self._sync_titlebar_window_state()

    def exit_nexus(self):
        if self.session_manager is not None:
            self.session_manager.shutdown_application(anchor_window=self)
        else:
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.quit()

    def closeEvent(self, event):
        if self.session_manager is not None and not self.session_manager.should_allow_window_close(self):
            event.ignore()
            return
        event.accept()
        super().closeEvent(event)
        if self.session_manager is not None:
            self.session_manager.on_window_closed(self)
        else:
            self.workspace_manager.unregister_window(self)

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