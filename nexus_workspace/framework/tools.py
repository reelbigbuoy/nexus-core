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
# File: tools.py
# Description: Defines the base tool framework, lifecycle hooks, and common tool UI behavior.
#============================================================================

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt5 import QtCore, QtWidgets

from ..core.themes import build_stylesheet, get_theme_colors, get_theme_manager
from .actions import NexusCommandContribution, NexusCommandRegistry, NexusToolbar
from .surfaces import NexusPanel, NexusToolHeader


class NexusToolBase(QtWidgets.QWidget):
    """Base widget for Nexus-hosted tools that centralizes title and theming."""

    titleChanged = QtCore.pyqtSignal(str)
    toolActivated = QtCore.pyqtSignal()
    toolDeactivated = QtCore.pyqtSignal()

    tool_type_id = ''
    display_name = ''
    default_subtitle = ''

    def __init__(self, parent=None, *, theme_name='Midnight', editor_title='', plugin_context=None):
        super().__init__(parent)
        self.plugin_context = plugin_context
        self.command_registry = NexusCommandRegistry(plugin_context, self)
        self._theme_name = theme_name
        self._editor_title = editor_title or self.display_name or self.__class__.__name__
        self.theme_manager = get_theme_manager()
        self.theme_manager.themeChanged.connect(self._on_theme_changed)
        self._active = False
        self._toolbar = None

        self._root_layout = QtWidgets.QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        self._header = None
        self._content_panel = NexusPanel(self, object_name='NexusToolContent', margins=(0, 0, 0, 0), spacing=0)
        self._root_layout.addWidget(self._content_panel, 1)

        self.setWindowTitle(self._editor_title)
        self.apply_theme(theme_name)

    def content_layout(self):
        return self._content_panel.layout_widget()

    def ensure_header(self, *, title=None, subtitle=''):
        if self._header is None:
            self._header = NexusToolHeader(title or self._editor_title, subtitle, self)
            self._root_layout.insertWidget(0, self._header, 0)
        else:
            if title is not None:
                self._header.set_title(title)
            self._header.set_subtitle(subtitle)
        return self._header

    def ensure_toolbar(self, *, title='Commands'):
        if self._toolbar is None:
            self._toolbar = NexusToolbar(title, self)
            self._root_layout.insertWidget(1 if self._header is not None else 0, self._toolbar, 0)
        return self._toolbar

    def sync_framework_toolbar(self):
        command_ids = list(self.default_toolbar_command_ids() or [])
        toolbar = self.ensure_toolbar() if command_ids else self._toolbar
        if toolbar is None:
            return None
        if not command_ids:
            toolbar.hide()
            return toolbar
        payloads = []
        for command_id in command_ids:
            payload = self.command_registry.payload_for_command(command_id)
            if payload is not None:
                payloads.append(payload)
        toolbar.populate_from_payloads(payloads, triggered_callback=lambda command: self.command_registry.execute(command.command_id))
        toolbar.setVisible(bool(payloads))
        return toolbar

    def default_toolbar_command_ids(self) -> List[str]:
        return []

    def command_contributions(self) -> List[NexusCommandContribution]:
        return []

    def tool_metadata(self):
        return {
            'tool_type_id': getattr(self, 'tool_type_id', ''),
            'display_name': getattr(self, 'display_name', self._editor_title),
            'editor_title': self._editor_title,
            'theme_name': self._theme_name,
            'active': self._active,
        }

    def framework_state(self) -> Dict[str, Any]:
        return {
            'editor_title': self._editor_title,
            'theme_name': self._theme_name,
        }

    def restore_framework_state(self, state):
        if not isinstance(state, dict):
            return
        title = state.get('editor_title')
        if title:
            self.set_tool_title(title)

    def save_state(self):
        return self.framework_state()

    def load_state(self, state):
        self.restore_framework_state(state)

    def theme_name(self):
        return self._theme_name

    def editor_title(self):
        return self._editor_title

    def set_header_title(self, title):
        self.ensure_header(title=title)

    def set_header_subtitle(self, subtitle):
        self.ensure_header(title=self._editor_title, subtitle=subtitle)

    def set_tool_title(self, title):
        title = str(title or self._editor_title)
        if title == self._editor_title:
            return
        self._editor_title = title
        self.setWindowTitle(title)
        if self._header is not None:
            self._header.set_title(title)
        self.titleChanged.emit(title)

    def activate_tool(self):
        self._active = True
        self.sync_framework_toolbar()
        self.toolActivated.emit()

    def deactivate_tool(self):
        self._active = False
        self.toolDeactivated.emit()

    def base_tool_stylesheet(self, theme):
        return f"""
        #NexusToolHeader {{
            background-color: {theme['panel_bg']};
            border-bottom: 1px solid {theme['border']};
        }}
        #NexusToolHeaderTitle {{
            color: {theme['text']};
        }}
        #NexusToolHeaderSubtitle {{
            color: {theme['muted_text']};
        }}
        #NexusToolContent, #NexusPanel, #NexusSurface {{
            background-color: {theme['app_bg']};
        }}
        #NexusToolbarRow, QToolBar#NexusToolbar {{
            background-color: {theme['panel_bg']};
            border-bottom: 1px solid {theme['border']};
        }}
        QToolBar#NexusToolbar {{
            spacing: 4px;
            padding: 4px 6px;
        }}
        #NexusSection {{
            background-color: {theme['panel_bg']};
            border: 1px solid {theme['border']};
            border-radius: 8px;
        }}
        #NexusSectionTitle {{
            color: {theme['text']};
        }}
        #NexusTabWidget::pane {{
            border: 1px solid {theme['border']};
            background-color: {theme['app_bg']};
        }}
        #NexusSplitter::handle {{
            background-color: {theme['border']};
        }}
        #NexusListWidget, #NexusTreeWidget, #NexusTableWidget {{
            background-color: {theme['panel_bg']};
            border: 1px solid {theme['border']};
        }}
        #NexusFieldLabel {{
            color: {theme['muted_text']};
            font-weight: 600;
        }}
        #NexusFieldHelpText {{
            color: {theme['muted_text']};
        }}
        #NexusInspectorSection, #NexusForm, #NexusSearchBar, #NexusCommandBar {{
            background-color: transparent;
        }}
        """

    def build_tool_stylesheet(self, theme):
        return ''

    def apply_theme(self, theme_name):
        self._theme_name = theme_name
        theme = get_theme_colors(theme_name)
        self.setStyleSheet(
            build_stylesheet(theme)
            + "\n"
            + self.base_tool_stylesheet(theme)
            + "\n"
            + self.build_tool_stylesheet(theme)
        )

    def _on_theme_changed(self, theme_name):
        try:
            self.apply_theme(theme_name)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self.sync_framework_toolbar()

    def focusInEvent(self, event):
        self.activate_tool()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.deactivate_tool()
        super().focusOutEvent(event)

    def closeEvent(self, event):
        try:
            self.theme_manager.themeChanged.disconnect(self._on_theme_changed)
        except (TypeError, RuntimeError):
            pass
        super().closeEvent(event)