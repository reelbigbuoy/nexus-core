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
# File: actions.py
# Description: Provides framework-level actions, menus, and UI integrations for command-driven workflows.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

from PyQt5 import QtCore, QtGui, QtWidgets

from .controls import NexusListWidget


@dataclass(frozen=True)
class NexusCommand:
    command_id: str
    title: str
    description: str = ''
    category: str = 'General'
    shortcut: Optional[str] = None
    plugin_id: Optional[str] = None
    tool_type_id: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    requires_active_tool: bool = False
    requires_inspectable_target: bool = False
    requires_selection_kind: Optional[str] = None

    @classmethod
    def from_payload(cls, payload: Any) -> "NexusCommand":
        descriptor = {}
        if isinstance(payload, dict):
            descriptor = payload.get('descriptor') if isinstance(payload.get('descriptor'), dict) else payload
        descriptor = dict(descriptor or {})
        return cls(
            command_id=str(descriptor.get('command_id') or ''),
            title=str(descriptor.get('title') or descriptor.get('command_id') or 'Command'),
            description=str(descriptor.get('description') or ''),
            category=str(descriptor.get('category') or 'General'),
            shortcut=str(descriptor.get('shortcut') or '') or None,
            plugin_id=str(descriptor.get('plugin_id') or '') or None,
            tool_type_id=str(descriptor.get('tool_type_id') or '') or None,
            keywords=[str(item) for item in (descriptor.get('keywords') or []) if str(item).strip()],
            metadata=dict(descriptor.get('metadata') or {}),
            requires_active_tool=bool(descriptor.get('requires_active_tool')),
            requires_inspectable_target=bool(descriptor.get('requires_inspectable_target')),
            requires_selection_kind=str(descriptor.get('requires_selection_kind') or '') or None,
        )

    def to_registration_kwargs(self) -> Dict[str, Any]:
        return {
            'command_id': self.command_id,
            'title': self.title,
            'description': self.description,
            'plugin_id': self.plugin_id,
            'tool_type_id': self.tool_type_id,
            'category': self.category,
            'shortcut': self.shortcut,
            'requires_active_tool': self.requires_active_tool,
            'requires_inspectable_target': self.requires_inspectable_target,
            'requires_selection_kind': self.requires_selection_kind,
            'metadata': dict(self.metadata or {}),
            'keywords': list(self.keywords or []),
        }

    def searchable_text(self) -> str:
        parts = [
            self.title,
            self.description,
            self.category,
            self.command_id,
            self.shortcut or '',
            ' '.join(self.keywords or []),
        ]
        return ' '.join(str(part) for part in parts if part).lower()


@dataclass(frozen=True)
class NexusCommandContribution:
    command_id: str
    location: str = 'menu'
    menu_path: str = 'Commands'
    toolbar_id: str = 'default'
    order: int = 100
    group: str = 'General'
    metadata: Dict[str, Any] = field(default_factory=dict)


class NexusAction(QtWidgets.QAction):
    """Qt action wrapper that keeps a Nexus command payload attached."""

    def __init__(self, command: NexusCommand, parent=None, *, triggered_callback: Optional[Callable[[NexusCommand], Any]] = None):
        super().__init__(command.title, parent)
        self.command = command
        self.setObjectName(f"NexusAction_{command.command_id.replace('.', '_')}")
        self.setToolTip(command.description or command.title)
        if command.shortcut:
            self.setShortcut(QtGui.QKeySequence(command.shortcut))
        self.setData(command.command_id)
        if triggered_callback is not None:
            self.triggered.connect(lambda _checked=False: triggered_callback(self.command))


class NexusCommandRegistry(QtCore.QObject):
    """Framework wrapper around the platform command service and plugin context."""

    registryChanged = QtCore.pyqtSignal()

    def __init__(self, plugin_context=None, parent=None):
        super().__init__(parent)
        self.plugin_context = plugin_context

    def command_service(self):
        return getattr(self.plugin_context, 'command_service', None) if self.plugin_context is not None else None

    def register(self, command: NexusCommand, callback, *, availability_callback=None):
        return register_nexus_command(self.plugin_context, command, callback, availability_callback=availability_callback)

    def unregister(self, command_id: str):
        service = self.command_service()
        if service is None or not hasattr(service, 'unregister_command'):
            return None
        result = service.unregister_command(str(command_id or ''))
        self.registryChanged.emit()
        return result

    def available_commands(self, query: str = '') -> List[Dict[str, Any]]:
        if self.plugin_context is None:
            return []
        if str(query or '').strip() and hasattr(self.plugin_context, 'search_available_commands'):
            return list(self.plugin_context.search_available_commands(query) or [])
        if hasattr(self.plugin_context, 'available_commands'):
            return list(self.plugin_context.available_commands() or [])
        return []

    def registry_snapshot(self) -> Dict[str, Any]:
        if self.plugin_context is None or not hasattr(self.plugin_context, 'command_registry'):
            return {'contract': 'platform.command_registry.v1', 'commands': [], 'categories': []}
        return self.plugin_context.command_registry() or {'contract': 'platform.command_registry.v1', 'commands': [], 'categories': []}

    def execute(self, command_id: str):
        if self.plugin_context is None or not hasattr(self.plugin_context, 'execute_command'):
            return {'handled': False, 'status': 'unavailable', 'error': 'Command context unavailable.'}
        return self.plugin_context.execute_command(str(command_id or ''))

    def payload_for_command(self, command_id: str, *, available_only: bool = True) -> Optional[Dict[str, Any]]:
        command_id = str(command_id or '').strip()
        if not command_id:
            return None
        source = self.available_commands() if available_only else list(self.registry_snapshot().get('commands', []) or [])
        for payload in source:
            descriptor = payload.get('descriptor') if isinstance(payload, dict) else None
            candidate = payload.get('command_id') if isinstance(payload, dict) else None
            if not candidate and isinstance(descriptor, dict):
                candidate = descriptor.get('command_id')
            if str(candidate or '').strip() == command_id:
                return payload
        return None

    def categories(self, *, available_only: bool = True) -> List[str]:
        source = self.available_commands() if available_only else list(self.registry_snapshot().get('commands', []) or [])
        values = sorted({str(((payload.get('descriptor') or {}).get('category') if isinstance(payload, dict) else '') or (payload.get('category') if isinstance(payload, dict) else '') or 'General') for payload in source})
        return values

    def grouped_payloads(self, *, available_only: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        source = self.available_commands() if available_only else list(self.registry_snapshot().get('commands', []) or [])
        for payload in source:
            descriptor = payload.get('descriptor') if isinstance(payload, dict) else {}
            category = str((descriptor.get('category') if isinstance(descriptor, dict) else '') or (payload.get('category') if isinstance(payload, dict) else '') or 'General')
            grouped.setdefault(category, []).append(payload)
        for category in grouped:
            grouped[category].sort(key=lambda item: (str(((item.get('descriptor') or {}).get('title') if isinstance(item, dict) else '') or item.get('title') or item.get('command_id') or '').lower(), str(item.get('command_id') or '').lower()))
        return grouped


class NexusCommandList(NexusListWidget):
    """List widget specialized for showing Nexus commands."""

    commandActivated = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None, *, object_name='NexusCommandList'):
        super().__init__(parent, object_name=object_name)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.itemActivated.connect(self._emit_activated)

    def set_commands(self, payloads: Iterable[dict]):
        self.clear()
        for payload in payloads or []:
            command = NexusCommand.from_payload(payload)
            line2 = [command.category]
            if command.shortcut:
                line2.append(command.shortcut)
            if command.command_id:
                line2.append(command.command_id)
            item = QtWidgets.QListWidgetItem(command.title)
            item.setData(QtCore.Qt.UserRole, dict(payload or {}))
            item.setToolTip(command.description or command.title)
            item.setText(f"{command.title}\n{' • '.join(line2)}")
            self.addItem(item)
        if self.count() > 0:
            self.setCurrentRow(0)

    def selected_payload(self) -> Optional[dict]:
        item = self.currentItem()
        return item.data(QtCore.Qt.UserRole) if item is not None else None

    def _emit_activated(self, item):
        payload = item.data(QtCore.Qt.UserRole) if item is not None else None
        if isinstance(payload, dict):
            self.commandActivated.emit(payload)


class NexusCommandBar(QtWidgets.QWidget):
    """Reusable search + execute row for command-driven surfaces."""

    executeRequested = QtCore.pyqtSignal()
    queryChanged = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, *, placeholder='Search commands…', button_text='Run Command'):
        super().__init__(parent)
        self.setObjectName('NexusCommandBar')
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.searchEdit = QtWidgets.QLineEdit(self)
        self.searchEdit.setPlaceholderText(placeholder)
        self.searchEdit.setClearButtonEnabled(True)
        self.executeButton = QtWidgets.QPushButton(button_text, self)
        layout.addWidget(self.searchEdit, 1)
        layout.addWidget(self.executeButton, 0)
        self.searchEdit.textChanged.connect(self.queryChanged)
        self.executeButton.clicked.connect(self.executeRequested)


class NexusToolbar(QtWidgets.QToolBar):
    """Framework-owned toolbar that binds its actions from command payloads."""

    def __init__(self, title: str = 'Commands', parent=None):
        super().__init__(title, parent)
        self.setObjectName('NexusToolbar')
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QtCore.QSize(16, 16))

    def populate_from_payloads(self, payloads: Sequence[Dict[str, Any]], *, triggered_callback=None):
        self.clear()
        for payload in payloads or []:
            if payload is None:
                self.addSeparator()
                continue
            action = build_action_from_payload(payload, parent=self, triggered_callback=triggered_callback)
            self.addAction(action)


class NexusCommandMenuBuilder:
    """Utility to build menus and toolbars from framework command payloads."""

    def __init__(self, registry: NexusCommandRegistry):
        self.registry = registry

    def build_menu(self, menu: QtWidgets.QMenu, *, include_palette_action: Optional[Callable[[], Any]] = None):
        menu.clear()
        if include_palette_action is not None:
            palette_action = menu.addAction('Command Palette…')
            palette_action.setShortcut(QtGui.QKeySequence('Ctrl+Shift+P'))
            palette_action.triggered.connect(include_palette_action)
            menu.addSeparator()
        grouped = self.registry.grouped_payloads(available_only=True)
        if not grouped:
            action = menu.addAction('No commands available')
            action.setEnabled(False)
            return
        categories = sorted(grouped.keys())
        for index, category in enumerate(categories):
            category_menu = menu.addMenu(category)
            for payload in grouped.get(category, []):
                action = build_action_from_payload(payload, parent=category_menu, triggered_callback=lambda command, registry=self.registry: registry.execute(command.command_id))
                shortcut = NexusCommand.from_payload(payload).shortcut
                if shortcut:
                    action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
                category_menu.addAction(action)
            if index < len(categories) - 1:
                menu.addSeparator()

    def payloads_for_ids(self, command_ids: Sequence[str]) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        for command_id in command_ids or []:
            payload = self.registry.payload_for_command(command_id)
            if payload is not None:
                payloads.append(payload)
        return payloads


def register_nexus_command(plugin_context, command: NexusCommand, callback, *, availability_callback=None):
    if plugin_context is None or not hasattr(plugin_context, 'register_command'):
        return None
    kwargs = command.to_registration_kwargs()
    kwargs['callback'] = callback
    kwargs['availability_callback'] = availability_callback
    return plugin_context.register_command(**kwargs)


def build_action_from_payload(payload: Any, parent=None, *, triggered_callback=None) -> NexusAction:
    return NexusAction(NexusCommand.from_payload(payload), parent=parent, triggered_callback=triggered_callback)