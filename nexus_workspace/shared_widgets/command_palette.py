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
# File: command_palette.py
# Description: Implements the command palette dialog and related command search behavior.
#============================================================================

from PyQt5 import QtCore, QtGui, QtWidgets

from ..framework.actions import NexusCommandBar, NexusCommandList, NexusCommandRegistry
from ..framework.windowing import NexusDialogBase, NexusMessageDialog


class CommandPaletteDialog(NexusDialogBase):
    def __init__(self, plugin_context, parent=None):
        super().__init__('Command Palette', parent=parent, modal=True, show_close=True)
        self.plugin_context = plugin_context
        self._commands = []
        self.commandRegistry = NexusCommandRegistry(plugin_context, self)
        self.setObjectName('CommandPaletteDialog')
        self.resize(720, 440)
        self._build_ui()
        self.install_frame_interaction_filter()
        self._wire_events()

    def _build_ui(self):
        layout = self.content_layout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.commandBar = NexusCommandBar(self, placeholder='Search commands…', button_text='Run Command')
        self.searchEdit = self.commandBar.searchEdit
        self.executeButton = self.commandBar.executeButton
        layout.addWidget(self.commandBar, 0)

        self.resultsList = NexusCommandList(self)
        layout.addWidget(self.resultsList, 1)

        footer = QtWidgets.QHBoxLayout()
        footer.setSpacing(8)
        self.detailLabel = QtWidgets.QLabel('', self)
        self.detailLabel.setObjectName('commandPaletteDetailLabel')
        self.detailLabel.setWordWrap(True)
        footer.addWidget(self.detailLabel, 1)
        layout.addLayout(footer)

    def _wire_events(self):
        self.commandBar.queryChanged.connect(self._refresh_results)
        self.resultsList.itemSelectionChanged.connect(self._update_detail_label)
        self.resultsList.commandActivated.connect(lambda _payload: self._execute_selected())
        self.commandBar.executeRequested.connect(self._execute_selected)

        QtWidgets.QShortcut(QtGui.QKeySequence('Down'), self, activated=self._focus_results)
        QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+N'), self, activated=self._focus_results)

    def open_and_focus(self):
        self._refresh_results()
        self.searchEdit.selectAll()
        self.searchEdit.setFocus(QtCore.Qt.OtherFocusReason)
        self.exec_()

    def _focus_results(self):
        if self.resultsList.count() <= 0:
            return
        self.resultsList.setFocus(QtCore.Qt.OtherFocusReason)
        if self.resultsList.currentRow() < 0:
            self.resultsList.setCurrentRow(0)

    def _refresh_results(self):
        query = self.searchEdit.text()
        self._commands = list(self.commandRegistry.available_commands(query))
        self.resultsList.set_commands(self._commands)
        self._update_detail_label()

    def _selected_payload(self):
        return self.resultsList.selected_payload()

    def _update_detail_label(self):
        payload = self._selected_payload() or {}
        descriptor = payload.get('descriptor') if isinstance(payload, dict) else {}
        if not isinstance(descriptor, dict):
            descriptor = {}
        title = descriptor.get('title') or payload.get('title') or 'Command'
        description = descriptor.get('description') or payload.get('description') or 'Run the selected command.'
        shortcut = descriptor.get('shortcut') or payload.get('shortcut') or ''
        category = descriptor.get('category') or payload.get('category') or 'General'
        command_id = payload.get('command_id') or descriptor.get('command_id') or ''
        bits = [f"<b>{title}</b>", description]
        meta = ' · '.join([part for part in [category, shortcut, command_id] if part])
        if meta:
            bits.append(meta)
        self.detailLabel.setText('<br/>'.join(bits) if payload else 'No command selected.')
        self.executeButton.setEnabled(bool(payload))

    def _execute_selected(self):
        payload = self._selected_payload()
        if not isinstance(payload, dict):
            return
        command_id = payload.get('command_id') or ((payload.get('descriptor') or {}).get('command_id'))
        if not command_id or self.plugin_context is None:
            return
        result = self.commandRegistry.execute(command_id)
        if isinstance(result, dict) and result.get('handled'):
            self.accept()
            return
        error = result.get('error') if isinstance(result, dict) else 'Command failed.'
        NexusMessageDialog.warning(self, 'Command Failed', error or 'Command failed.')