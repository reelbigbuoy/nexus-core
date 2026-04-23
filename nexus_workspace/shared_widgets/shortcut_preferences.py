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
# File: shortcut_preferences.py
# Description: Provides the shortcut preferences dialog for viewing and editing key bindings.
#============================================================================

from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets

from ..framework.controls import NexusTableWidget
from ..framework.forms import NexusForm, NexusInspectorSection, NexusSearchBar
from ..framework.windowing import NexusDialogBase


class ShortcutPreferencesDialog(NexusDialogBase):
    def __init__(self, plugin_context, parent=None):
        super().__init__('Shortcut Preferences', parent=parent, modal=True, show_close=True)
        self.plugin_context = plugin_context
        self._entries = []
        self._filtered_entries = []
        self.resize(860, 520)
        self._build_ui()
        self.install_frame_interaction_filter()
        self._wire_events()
        self.refresh_entries()

    def _build_ui(self):
        layout = self.content_layout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.searchBar = NexusSearchBar(self, placeholder='Filter commands…', button_text='Refresh')
        self.searchBar.primaryButton.hide()
        self.searchEdit = self.searchBar.searchEdit
        layout.addWidget(self.searchBar)

        self.table = NexusTableWidget(parent=self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['Command', 'Category', 'Default', 'Current'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        editor_group = NexusInspectorSection('Selected Command Shortcut', self, help_text='Edit command shortcuts through the Nexus command framework.')
        editor_form = editor_group.form
        self.commandLabel = QtWidgets.QLabel('No command selected', editor_group)
        self.commandLabel.setWordWrap(True)
        editor_form.add_row('Command', self.commandLabel)
        self.shortcutEdit = QtWidgets.QKeySequenceEdit(editor_group)
        editor_form.add_row('Shortcut', self.shortcutEdit)
        buttons_row = QtWidgets.QWidget(editor_group)
        buttons_layout = QtWidgets.QHBoxLayout(buttons_row)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(8)
        self.applyButton = QtWidgets.QPushButton('Apply', editor_group)
        self.clearButton = QtWidgets.QPushButton('Clear Override', editor_group)
        self.resetButton = QtWidgets.QPushButton('Reset to Default', editor_group)
        buttons_layout.addWidget(self.applyButton)
        buttons_layout.addWidget(self.clearButton)
        buttons_layout.addWidget(self.resetButton)
        buttons_layout.addStretch(1)
        editor_form.add_row('Actions', buttons_row)
        layout.addWidget(editor_group)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _wire_events(self):
        self.searchEdit.textChanged.connect(self.refresh_entries)
        self.table.itemSelectionChanged.connect(self._sync_selected_entry)
        self.applyButton.clicked.connect(self._apply_selected_shortcut)
        self.clearButton.clicked.connect(self._clear_selected_shortcut)
        self.resetButton.clicked.connect(self._reset_selected_shortcut)

    def refresh_entries(self):
        registry = self.plugin_context.shortcut_registry() if self.plugin_context is not None else {'entries': []}
        entries = list(registry.get('entries') or []) if isinstance(registry, dict) else []
        query = str(self.searchEdit.text() or '').strip().lower()
        if query:
            entries = [item for item in entries if query in ' '.join([str(item.get('title') or ''), str(item.get('category') or ''), str(item.get('command_id') or '')]).lower()]
        self._entries = entries
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            title = str(entry.get('title') or entry.get('command_id') or 'Command')
            if entry.get('command_id'):
                title = f"{title}\n{entry.get('command_id')}"
            items = [
                QtWidgets.QTableWidgetItem(title),
                QtWidgets.QTableWidgetItem(str(entry.get('category') or 'General')),
                QtWidgets.QTableWidgetItem(str(entry.get('default_shortcut') or '')),
                QtWidgets.QTableWidgetItem(str(entry.get('shortcut') or '')),
            ]
            for item in items:
                item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            items[0].setData(QtCore.Qt.UserRole, dict(entry))
            for col, item in enumerate(items):
                self.table.setItem(row, col, item)
        if entries:
            self.table.selectRow(0)
        else:
            self.commandLabel.setText('No command selected')
            self.shortcutEdit.setKeySequence(QtGui.QKeySequence())

    def _selected_entry(self):
        item = self.table.item(self.table.currentRow(), 0) if self.table.currentRow() >= 0 else None
        return item.data(QtCore.Qt.UserRole) if item is not None else None

    def _sync_selected_entry(self):
        entry = self._selected_entry() or {}
        if not entry:
            self.commandLabel.setText('No command selected')
            self.shortcutEdit.setKeySequence(QtGui.QKeySequence())
            return
        self.commandLabel.setText(f"<b>{entry.get('title') or entry.get('command_id')}</b><br/>{entry.get('command_id')}")
        self.shortcutEdit.setKeySequence(QtGui.QKeySequence(str(entry.get('shortcut') or '')))

    def _apply_selected_shortcut(self):
        entry = self._selected_entry() or {}
        command_id = entry.get('command_id')
        if not command_id or self.plugin_context is None:
            return
        shortcut = self.shortcutEdit.keySequence().toString(QtGui.QKeySequence.NativeText) or self.shortcutEdit.keySequence().toString()
        self.plugin_context.set_shortcut_override(command_id, shortcut)
        self.refresh_entries()
        self._restore_selection(command_id)

    def _clear_selected_shortcut(self):
        entry = self._selected_entry() or {}
        command_id = entry.get('command_id')
        if not command_id or self.plugin_context is None:
            return
        self.plugin_context.clear_shortcut_override(command_id)
        self.refresh_entries()
        self._restore_selection(command_id)

    def _reset_selected_shortcut(self):
        entry = self._selected_entry() or {}
        command_id = entry.get('command_id')
        default_shortcut = str(entry.get('default_shortcut') or '')
        if not command_id or self.plugin_context is None:
            return
        if default_shortcut:
            self.plugin_context.set_shortcut_override(command_id, default_shortcut)
        else:
            self.plugin_context.clear_shortcut_override(command_id)
        self.refresh_entries()
        self._restore_selection(command_id)

    def _restore_selection(self, command_id):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            entry = item.data(QtCore.Qt.UserRole) if item is not None else None
            if isinstance(entry, dict) and entry.get('command_id') == command_id:
                self.table.selectRow(row)
                break