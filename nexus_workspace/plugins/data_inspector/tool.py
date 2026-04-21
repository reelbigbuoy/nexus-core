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
# File: tool.py
# Description: Implements the bundled data inspector tool for viewing structured object data.
#============================================================================

import json
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from ...core.serialization import NexusSerializable
from ...core.themes import build_stylesheet, get_theme_colors
from ...framework import NexusListWidget, NexusSearchBar, NexusSplitter, NexusTabWidget, NexusToolBase


class DataInspectorTool(NexusToolBase, NexusSerializable):
    tool_type_id = 'data_inspector'
    display_name = 'Platform Diagnostics'

    def default_toolbar_command_ids(self):
        return ['platform.refresh_diagnostics']

    def __init__(self, parent=None, theme_name='Midnight', editor_title='Platform Diagnostics', plugin_context=None):
        super().__init__(parent, theme_name=theme_name, editor_title=editor_title, plugin_context=plugin_context)
        self._selected_key = None
        self._selected_event_index = None
        self._selected_action_index = None
        self._store_subscription = None
        self._event_subscription = None

        self.ensure_header(title='Platform Diagnostics', subtitle='Inspect runtime state, actions, events, and registered plugins')

        root = self.content_layout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.searchBar = NexusSearchBar(self, placeholder='Filter DataStore keys...', button_text='Refresh')
        self.filterEdit = self.searchBar.searchEdit
        self.refreshButton = self.searchBar.primaryButton
        root.addWidget(self.searchBar)

        self.tabs = NexusTabWidget(self)
        root.addWidget(self.tabs, 1)

        self._build_overview_tab()
        self._build_store_tab()
        self._build_plugins_tab()
        self._build_actions_tab()
        self._build_events_tab()

        self.filterEdit.textChanged.connect(self._apply_filter)
        self.refreshButton.clicked.connect(self.refresh_view)
        self.keyList.currentItemChanged.connect(self._on_key_changed)
        self.pluginList.currentItemChanged.connect(self._on_plugin_changed)
        self.toolList.currentItemChanged.connect(self._on_tool_changed)
        self.handlerList.currentItemChanged.connect(self._on_handler_changed)
        self.actionList.currentItemChanged.connect(self._on_action_changed)
        self.eventList.currentItemChanged.connect(self._on_event_changed)

        self._connect_runtime_sources()
        self.refresh_view()

    def _build_overview_tab(self):
        page = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.summaryLabel = QtWidgets.QLabel(page)
        self.summaryLabel.setWordWrap(True)
        self.summaryLabel.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self.summaryLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        font = QtGui.QFont()
        font.setPointSize(font.pointSize() + 1)
        self.summaryLabel.setFont(font)
        layout.addWidget(self.summaryLabel, 0)

        self.statePathLabel = QtWidgets.QLabel(page)
        self.statePathLabel.setWordWrap(True)
        self.statePathLabel.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.statePathLabel, 0)

        self.overviewJson = QtWidgets.QPlainTextEdit(page)
        self.overviewJson.setReadOnly(True)
        layout.addWidget(self.overviewJson, 1)

        self.tabs.addTab(page, 'Overview')

    def _build_store_tab(self):
        page = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        splitter = NexusSplitter(QtCore.Qt.Horizontal, page)
        self.keyList = NexusListWidget(splitter)
        self.valueView = QtWidgets.QPlainTextEdit(splitter)
        self.valueView.setReadOnly(True)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.storeSplitter = splitter
        layout.addWidget(splitter, 1)

        self.tabs.addTab(page, 'Store')

    def _build_plugins_tab(self):
        page = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        splitter = NexusSplitter(QtCore.Qt.Horizontal, page)

        left = NexusSplitter(QtCore.Qt.Vertical, splitter)
        self.pluginList = NexusListWidget(left)
        self.toolList = NexusListWidget(left)
        left.setStretchFactor(0, 1)
        left.setStretchFactor(1, 1)

        self.pluginDetail = QtWidgets.QPlainTextEdit(splitter)
        self.pluginDetail.setReadOnly(True)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.pluginSplitter = splitter
        layout.addWidget(splitter, 1)

        self.tabs.addTab(page, 'Plugins')

    def _build_actions_tab(self):
        page = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        splitter = NexusSplitter(QtCore.Qt.Horizontal, page)

        left = NexusSplitter(QtCore.Qt.Vertical, splitter)
        self.handlerList = NexusListWidget(left)
        self.actionList = NexusListWidget(left)
        left.setStretchFactor(0, 1)
        left.setStretchFactor(1, 1)

        self.actionDetail = QtWidgets.QPlainTextEdit(splitter)
        self.actionDetail.setReadOnly(True)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.actionSplitter = splitter
        layout.addWidget(splitter, 1)

        self.tabs.addTab(page, 'Actions')

    def _build_events_tab(self):
        page = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        splitter = NexusSplitter(QtCore.Qt.Horizontal, page)
        self.eventList = NexusListWidget(splitter)
        self.eventDetail = QtWidgets.QPlainTextEdit(splitter)
        self.eventDetail.setReadOnly(True)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.eventSplitter = splitter
        layout.addWidget(splitter, 1)

        self.tabs.addTab(page, 'Events')

    def editor_title(self):
        return self._editor_title

    def apply_theme(self, theme_name):
        self._theme_name = theme_name
        theme = get_theme_colors(theme_name)
        self.setStyleSheet(build_stylesheet(theme))

    def _connect_runtime_sources(self):
        data_store = getattr(self.plugin_context, 'data_store', None) if self.plugin_context is not None else None
        if data_store is not None and self._store_subscription is None:
            self._store_subscription = data_store.subscribe_all(self._on_store_changed)
        event_bus = getattr(self.plugin_context, 'event_bus', None) if self.plugin_context is not None else None
        if event_bus is not None and self._event_subscription is None and hasattr(event_bus, 'subscribe_all'):
            self._event_subscription = event_bus.subscribe_all(self._on_event_bus_changed)

    def _on_store_changed(self, payload):
        if isinstance(payload, dict):
            key = str(payload.get('key') or '')
            if key.startswith('platform.event_bus') or key.startswith('platform.events.recent'):
                return
        self.refresh_view(preserve_selection=True)

    def _on_event_bus_changed(self, payload):
        if isinstance(payload, dict):
            event_type = str(payload.get('event_type') or '')
            if event_type in {'data.changed'}:
                event_payload = payload.get('payload') if isinstance(payload.get('payload'), dict) else {}
                key = str(event_payload.get('key') or '')
                if key.startswith('platform.event_bus') or key.startswith('platform.events.recent'):
                    return
        self.refresh_view(preserve_selection=True)

    def refresh_view(self, preserve_selection=True):
        self._refresh_overview()
        self._refresh_store(preserve_selection=preserve_selection)
        self._refresh_plugins()
        self._refresh_actions()
        self._refresh_events()

    def _refresh_overview(self):
        data_store = getattr(self.plugin_context, 'data_store', None)
        plugin_registry = data_store.get('platform.plugin_registry', {}) if data_store is not None else {}
        state_taxonomy = data_store.get('platform.state_taxonomy', {}) if data_store is not None else {}
        action_snapshot = data_store.get('platform.action_dispatcher', {}) if data_store is not None else {}
        command_snapshot = data_store.get('platform.command_registry', {}) if data_store is not None else {}
        available_commands = data_store.get('context.available_commands', []) if data_store is not None else []
        recent_commands = data_store.get('platform.commands.recent', []) if data_store is not None else []
        event_snapshot = data_store.get('platform.event_bus', {}) if data_store is not None else {}
        selection = data_store.get('selection.current', {}) if data_store is not None else {}
        inspectable = None
        if data_store is not None:
            selection_payload = data_store.get('selection.current', {})
            if isinstance(selection_payload, dict):
                inspectable = ((selection_payload.get('metadata') or {}).get('inspectable'))
        summary = [
            'Nexus platform diagnostics summary',
            '',
            f"Plugins registered: {len(plugin_registry.get('plugins', []) or [])}",
            f"Tools registered: {len(plugin_registry.get('tools', []) or [])}",
            f"Action handlers: {len(action_snapshot.get('handlers', []) or [])}",
            f"Registered commands: {len(command_snapshot.get('commands', []) or [])}",
            f"Available commands: {len(available_commands or [])}",
            f"Recent command executions: {len(recent_commands or [])}",
            f"Recent actions tracked: {len(action_snapshot.get('recent_activity', []) or [])}",
            f"Event subscriptions: {len(event_snapshot.get('subscriber_counts', {}) or {})}",
            f"Recent events tracked: {len(event_snapshot.get('recent_events', []) or [])}",
            f"DataStore keys: {len(data_store.keys()) if data_store is not None else 0}",
            f"State taxonomy categories: {len(state_taxonomy.get('categories', []) or [])}",
            f"Selection contract: {selection.get('contract', 'none') if isinstance(selection, dict) else 'none'}",
            f"Inspectable contract: {inspectable.get('contract', 'none') if isinstance(inspectable, dict) else 'none'}",
        ]
        self.summaryLabel.setText('\n'.join(summary))

        state_manager = getattr(self.plugin_context, 'state_manager', None)
        try:
            state_path = str(state_manager.state_file_path()) if state_manager is not None else 'Unavailable'
        except Exception:
            state_path = 'Unavailable'
        self.statePathLabel.setText(f'Persistence file: {state_path}')

        overview_payload = {
            'plugin_registry': plugin_registry,
            'state_taxonomy': state_taxonomy,
            'action_dispatcher': action_snapshot,
            'command_registry': command_snapshot,
            'available_commands': available_commands,
            'recent_commands': recent_commands,
            'event_bus': event_snapshot,
            'selection_current': selection,
            'inspectable_current': inspectable,
        }
        self.overviewJson.setPlainText(self._format_value(overview_payload))

    def _refresh_store(self, preserve_selection=True):
        data_store = getattr(self.plugin_context, 'data_store', None) if self.plugin_context is not None else None
        current_key = self._selected_key if preserve_selection else None
        keys = sorted(data_store.keys()) if data_store is not None else []
        filter_text = self.filterEdit.text().strip().lower()
        self.keyList.blockSignals(True)
        self.keyList.clear()
        for key in keys:
            if filter_text and filter_text not in key.lower():
                continue
            self.keyList.addItem(key)
        self.keyList.blockSignals(False)

        if current_key:
            matches = self.keyList.findItems(current_key, QtCore.Qt.MatchExactly)
            if matches:
                self.keyList.setCurrentItem(matches[0])
                return

        if self.keyList.count():
            self.keyList.setCurrentRow(0)
        else:
            self._selected_key = None
            self.valueView.setPlainText('')

    def _refresh_plugins(self):
        data_store = getattr(self.plugin_context, 'data_store', None)
        plugin_registry = data_store.get('platform.plugin_registry', {}) if data_store is not None else {}
        plugins = plugin_registry.get('plugins', []) or []
        tools = plugin_registry.get('tools', []) or []
        current_plugin = self.pluginList.currentItem().data(QtCore.Qt.UserRole) if self.pluginList.currentItem() is not None else None
        current_tool = self.toolList.currentItem().data(QtCore.Qt.UserRole) if self.toolList.currentItem() is not None else None

        self.pluginList.blockSignals(True)
        self.pluginList.clear()
        for manifest in plugins:
            item = QtWidgets.QListWidgetItem(f"{manifest.get('display_name', manifest.get('plugin_id', 'plugin'))} ({manifest.get('plugin_id', '')})")
            item.setData(QtCore.Qt.UserRole, manifest)
            self.pluginList.addItem(item)
        self.pluginList.blockSignals(False)

        self.toolList.blockSignals(True)
        self.toolList.clear()
        for tool in tools:
            item = QtWidgets.QListWidgetItem(f"{tool.get('display_name', tool.get('tool_type_id', 'tool'))} [{tool.get('plugin_id', '')}]")
            item.setData(QtCore.Qt.UserRole, tool)
            self.toolList.addItem(item)
        self.toolList.blockSignals(False)

        self._restore_list_selection(self.pluginList, current_plugin, lambda payload: payload.get('plugin_id'))
        self._restore_list_selection(self.toolList, current_tool, lambda payload: payload.get('tool_type_id'))
        if self.pluginList.count() and self.pluginList.currentRow() < 0:
            self.pluginList.setCurrentRow(0)
        if self.toolList.count() and self.toolList.currentRow() < 0:
            self.toolList.setCurrentRow(0)
        if self.pluginList.currentItem() is None and self.toolList.currentItem() is None:
            self.pluginDetail.setPlainText('')

    def _refresh_actions(self):
        data_store = getattr(self.plugin_context, 'data_store', None)
        action_snapshot = data_store.get('platform.action_dispatcher', {}) if data_store is not None else {}
        handlers = action_snapshot.get('handlers', []) or []
        recent_actions = list(reversed(action_snapshot.get('recent_activity', []) or []))
        current_handler = self.handlerList.currentItem().data(QtCore.Qt.UserRole) if self.handlerList.currentItem() is not None else None
        current_action = self.actionList.currentItem().data(QtCore.Qt.UserRole) if self.actionList.currentItem() is not None else None

        self.handlerList.blockSignals(True)
        self.handlerList.clear()
        for handler in handlers:
            label = f"{handler.get('action_type', '')} -> {handler.get('name', 'handler')}"
            plugin_id = handler.get('plugin_id')
            if plugin_id:
                label += f" [{plugin_id}]"
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, handler)
            self.handlerList.addItem(item)
        self.handlerList.blockSignals(False)

        self.actionList.blockSignals(True)
        self.actionList.clear()
        for activity in recent_actions:
            request = activity.get('request', {}) if isinstance(activity, dict) else {}
            result = activity.get('result', {}) if isinstance(activity, dict) else {}
            label = f"{request.get('action_type', 'action')} -> {result.get('status', 'unknown')}"
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, activity)
            self.actionList.addItem(item)
        self.actionList.blockSignals(False)

        self._restore_list_selection(self.handlerList, current_handler, lambda payload: (payload or {}).get('name'))
        self._restore_list_selection(self.actionList, current_action, lambda payload: ((payload or {}).get('request') or {}).get('action_type'))
        if self.handlerList.count() and self.handlerList.currentRow() < 0:
            self.handlerList.setCurrentRow(0)
        if self.actionList.count() and self.actionList.currentRow() < 0:
            self.actionList.setCurrentRow(0)
        if self.handlerList.currentItem() is None and self.actionList.currentItem() is None:
            self.actionDetail.setPlainText('')

    def _refresh_events(self):
        data_store = getattr(self.plugin_context, 'data_store', None)
        events = list(reversed(data_store.get('platform.events.recent', []) or [])) if data_store is not None else []
        current_event = self.eventList.currentItem().data(QtCore.Qt.UserRole) if self.eventList.currentItem() is not None else None

        self.eventList.blockSignals(True)
        self.eventList.clear()
        for event in events:
            label = event.get('event_type', 'event')
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, event)
            self.eventList.addItem(item)
        self.eventList.blockSignals(False)

        self._restore_list_selection(self.eventList, current_event, lambda payload: (payload or {}).get('event_type'))
        if self.eventList.count() and self.eventList.currentRow() < 0:
            self.eventList.setCurrentRow(0)
        if self.eventList.currentItem() is None:
            self.eventDetail.setPlainText('')

    def _apply_filter(self):
        self._refresh_store(preserve_selection=True)

    def _on_key_changed(self, current, previous):
        key = current.text() if current is not None else None
        self._selected_key = key
        data_store = getattr(self.plugin_context, 'data_store', None) if self.plugin_context is not None else None
        if key is None or data_store is None:
            self.valueView.setPlainText('')
            return
        value = data_store.get(key)
        self.valueView.setPlainText(self._format_value(value))

    def _on_plugin_changed(self, current, previous):
        payload = current.data(QtCore.Qt.UserRole) if current is not None else None
        self.pluginDetail.setPlainText(self._format_value(payload) if payload is not None else '')

    def _on_tool_changed(self, current, previous):
        payload = current.data(QtCore.Qt.UserRole) if current is not None else None
        if payload is not None:
            self.pluginDetail.setPlainText(self._format_value(payload))

    def _on_handler_changed(self, current, previous):
        payload = current.data(QtCore.Qt.UserRole) if current is not None else None
        self.actionDetail.setPlainText(self._format_value(payload) if payload is not None else '')

    def _on_action_changed(self, current, previous):
        payload = current.data(QtCore.Qt.UserRole) if current is not None else None
        if payload is not None:
            self.actionDetail.setPlainText(self._format_value(payload))

    def _on_event_changed(self, current, previous):
        payload = current.data(QtCore.Qt.UserRole) if current is not None else None
        self.eventDetail.setPlainText(self._format_value(payload) if payload is not None else '')

    def _restore_list_selection(self, widget, previous_payload, key_func):
        if previous_payload is None:
            return
        previous_key = key_func(previous_payload)
        for row in range(widget.count()):
            item = widget.item(row)
            payload = item.data(QtCore.Qt.UserRole)
            if key_func(payload) == previous_key:
                widget.setCurrentItem(item)
                return

    def _safe_serialize(self, value, max_depth=5, _depth=0, _seen=None):
        if _seen is None:
            _seen = set()

        if id(value) in _seen:
            return '<circular>'
        if _depth > max_depth:
            return '<max_depth>'
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        _seen.add(id(value))
        try:
            if isinstance(value, dict):
                items = list(value.items())
                safe = {
                    str(k): self._safe_serialize(v, max_depth=max_depth, _depth=_depth + 1, _seen=_seen)
                    for k, v in items[:50]
                }
                if len(items) > 50:
                    safe['<truncated>'] = f'{len(items) - 50} more entries'
                return safe
            if isinstance(value, (list, tuple, set)):
                items = list(value)
                safe = [
                    self._safe_serialize(v, max_depth=max_depth, _depth=_depth + 1, _seen=_seen)
                    for v in items[:100]
                ]
                if len(items) > 100:
                    safe.append(f'<truncated {len(items) - 100} more items>')
                return safe
        finally:
            _seen.discard(id(value))

        return f'<{type(value).__name__}>'

    def _format_value(self, value):
        try:
            return json.dumps(self._safe_serialize(value), indent=2, sort_keys=True)
        except Exception:
            return repr(value)

    def save_state(self):
        sizes = {}
        for name, splitter in [('store', self.storeSplitter), ('plugins', self.pluginSplitter), ('actions', self.actionSplitter), ('events', self.eventSplitter)]:
            try:
                sizes[name] = list(splitter.sizes())
            except Exception:
                sizes[name] = []
        return {
            'editor_title': self._editor_title,
            'selected_key': self._selected_key,
            'filter_text': self.filterEdit.text(),
            'tab_index': self.tabs.currentIndex(),
            'splitter_sizes': sizes,
        }

    def load_state(self, state):
        if not state:
            return
        title = state.get('editor_title')
        if title:
            self._editor_title = title
            self.setWindowTitle(title)
        self.filterEdit.setText(state.get('filter_text', ''))
        self._selected_key = state.get('selected_key')
        self.refresh_view(preserve_selection=True)
        index = int(state.get('tab_index', 0) or 0)
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)
        sizes = state.get('splitter_sizes') or {}
        for name, splitter in [('store', self.storeSplitter), ('plugins', self.pluginSplitter), ('actions', self.actionSplitter), ('events', self.eventSplitter)]:
            splitter_sizes = sizes.get(name) or []
            if splitter_sizes:
                QtCore.QTimer.singleShot(0, lambda s=splitter, v=splitter_sizes: s.setSizes(v))

    def closeEvent(self, event):
        data_store = getattr(self.plugin_context, 'data_store', None) if self.plugin_context is not None else None
        if data_store is not None and self._store_subscription is not None:
            try:
                data_store.unsubscribe_all(self._store_subscription)
            except Exception:
                pass
            self._store_subscription = None
        event_bus = getattr(self.plugin_context, 'event_bus', None) if self.plugin_context is not None else None
        if event_bus is not None and self._event_subscription is not None and hasattr(event_bus, 'unsubscribe_all'):
            try:
                event_bus.unsubscribe_all(self._event_subscription)
            except Exception:
                pass
            self._event_subscription = None
        super().closeEvent(event)