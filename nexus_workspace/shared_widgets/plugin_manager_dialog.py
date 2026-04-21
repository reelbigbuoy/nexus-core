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
# File: plugin_manager_dialog.py
# Description: Provides the plugin manager dialog for viewing plugin status and metadata.
#============================================================================

from __future__ import annotations

import json

from PyQt5 import QtCore, QtGui, QtWidgets

from ..framework.windowing import NexusDialogBase
from ..framework.controls import NexusTableWidget


class BadgeItemDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, style_map, parent=None):
        super().__init__(parent)
        self._style_map = style_map

    def _badge_meta(self, index):
        data = index.data(QtCore.Qt.UserRole + 1) or {}
        return {
            'label': str(data.get('label') or index.data(QtCore.Qt.DisplayRole) or ''),
            'bg': str(data.get('bg') or '#465268'),
            'fg': str(data.get('fg') or '#ffffff'),
            'icon_kind': str(data.get('icon_kind') or ''),
        }

    def _icon_for_kind(self, option, icon_kind):
        style = option.widget.style() if option.widget else QtWidgets.QApplication.style()
        icon_map = {
            'platform': QtWidgets.QStyle.SP_MessageBoxInformation,
            'first_party': QtWidgets.QStyle.SP_DialogApplyButton,
            'official': QtWidgets.QStyle.SP_DialogApplyButton,
            'official': QtWidgets.QStyle.SP_DialogApplyButton,
            'builtin': QtWidgets.QStyle.SP_TitleBarMenuButton,
            'bundled': QtWidgets.QStyle.SP_DirIcon,
            'organization': QtWidgets.QStyle.SP_FileDialogDetailedView,
            'verified': QtWidgets.QStyle.SP_DialogYesButton,
            'third_party': QtWidgets.QStyle.SP_ComputerIcon,
            'unverified': QtWidgets.QStyle.SP_MessageBoxWarning,
            'external': QtWidgets.QStyle.SP_ArrowRight,
            'manual': QtWidgets.QStyle.SP_FileIcon,
            'marketplace': QtWidgets.QStyle.SP_DriveNetIcon,
            'local': QtWidgets.QStyle.SP_DirHomeIcon,
            'private': QtWidgets.QStyle.SP_DialogResetButton,
            'unknown': QtWidgets.QStyle.SP_MessageBoxQuestion,
        }
        pixmap_type = icon_map.get(icon_kind)
        return style.standardIcon(pixmap_type) if pixmap_type is not None else QtGui.QIcon()

    def paint(self, painter, option, index):
        meta = self._badge_meta(index)
        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        selected = bool(option.state & QtWidgets.QStyle.State_Selected)
        hovered = bool(option.state & QtWidgets.QStyle.State_MouseOver)

        outer = option.rect.adjusted(6, 5, -6, -5)
        bg = QtGui.QColor(meta['bg'])
        fg = QtGui.QColor(meta['fg'])
        if selected:
            bg = bg.lighter(115)
        elif hovered:
            bg = bg.lighter(108)

        pill = QtGui.QPainterPath()
        pill.addRoundedRect(QtCore.QRectF(outer), 9, 9)
        painter.fillPath(pill, bg)

        pen = QtGui.QPen(bg.lighter(135) if selected else bg.darker(115))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(pill)

        icon = self._icon_for_kind(option, meta['icon_kind'])
        text_rect = outer.adjusted(10, 0, -10, 0)
        if not icon.isNull():
            icon_size = 14
            icon_rect = QtCore.QRect(
                text_rect.left(),
                text_rect.center().y() - icon_size // 2,
                icon_size,
                icon_size,
            )
            mode = QtGui.QIcon.Normal
            state = QtGui.QIcon.On if selected else QtGui.QIcon.Off
            icon.paint(painter, icon_rect, QtCore.Qt.AlignCenter, mode, state)
            text_rect.setLeft(icon_rect.right() + 7)

        font = option.font
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(fg)
        painter.drawText(
            text_rect,
            QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
            meta['label'].upper(),
        )
        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QtCore.QSize(max(size.width(), 90), max(size.height(), 28))


class PluginManagerDialog(NexusDialogBase):
    BADGE_STYLES = {
        'platform': ('Platform', '#2d4f85', '#ffffff', 'platform'),
        'first_party': ('First Party', '#1f6f50', '#ffffff', 'first_party'),
        'official': ('Reel Big Buoy', '#1f6f50', '#ffffff', 'official'),
        'official': ('Official', '#1f6f50', '#ffffff', 'official'),
        'builtin': ('Built-in', '#2d4f85', '#ffffff', 'builtin'),
        'bundled': ('Bundled', '#465268', '#ffffff', 'bundled'),
        'organization': ('Organization', '#5b4b8a', '#ffffff', 'organization'),
        'verified': ('Verified', '#1d6b75', '#ffffff', 'verified'),
        'third_party': ('Third Party', '#6d5a2f', '#ffffff', 'third_party'),
        'unverified': ('Unverified', '#7a3f3f', '#ffffff', 'unverified'),
        'external': ('External', '#6d5a2f', '#ffffff', 'external'),
        'manual': ('Manual', '#465268', '#ffffff', 'manual'),
        'marketplace': ('Marketplace', '#355c7d', '#ffffff', 'marketplace'),
        'local': ('Local', '#465268', '#ffffff', 'local'),
        'private': ('Private', '#5b4b8a', '#ffffff', 'private'),
        'unknown': ('Unknown', '#555555', '#ffffff', 'unknown'),
    }

    def __init__(self, plugin_records=None, enablement_overrides=None, parent=None):
        super().__init__('Plugin Manager', parent=parent, modal=True, show_close=True)
        self.resize(1180, 520)
        self._records = list(plugin_records or [])
        self._enablement_overrides = dict(enablement_overrides or {})
        self._build_ui()
        self.install_frame_interaction_filter()
        self._populate()

    def _build_ui(self):
        layout = self.content_layout()
        intro = QtWidgets.QLabel(
            'Enable or disable plugins and review their provider, category, trust, and distribution details. '
            'Visibility updates immediately; a restart is still recommended for full load/unload changes.'
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.table = NexusTableWidget(0, 12, self)
        self.table.setHorizontalHeaderLabels([
            'Enabled',
            'Name',
            'Provider',
            'Ownership',
            'Channel',
            'Trust',
            'Install Root',
            'Plugin ID',
            'Type',
            'Source',
            'Version',
            'Status',
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        for idx in range(2, 12):
            self.table.horizontalHeader().setSectionResizeMode(idx, QtWidgets.QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._refresh_details)

        self._badge_delegate = BadgeItemDelegate(self.BADGE_STYLES, self.table)
        for column in (3, 4, 5, 9):
            self.table.setItemDelegateForColumn(column, self._badge_delegate)

        layout.addWidget(self.table, 1)

        self.details = QtWidgets.QPlainTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setPlaceholderText('Select a plugin to inspect its manifest and load details.')
        layout.addWidget(self.details, 1)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _normalize_badge_key(self, value):
        return str(value or '').strip().lower().replace(' ', '_').replace('-', '_')

    def _badge_payload(self, value):
        key = self._normalize_badge_key(value)
        label, bg, fg, icon_kind = self.BADGE_STYLES.get(
            key,
            (str(value or '').strip().replace('_', ' ').title(), '#465268', '#ffffff', 'unknown'),
        )
        return key, label, bg, fg, icon_kind

    def _make_badge_item(self, value, record):
        _, label, bg, fg, icon_kind = self._badge_payload(value)
        item = QtWidgets.QTableWidgetItem(label)
        item.setData(QtCore.Qt.UserRole, record)
        item.setData(QtCore.Qt.UserRole + 1, {
            'label': label,
            'bg': bg,
            'fg': fg,
            'icon_kind': icon_kind,
        })
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        return item

    def _display_source_label(self, record):
        distribution_source = str(record.get('distribution_source') or '').strip()
        raw_source = str(record.get('source') or '').strip()
        install_root = str(record.get('install_root') or '').strip()
        if distribution_source:
            return distribution_source
        if raw_source == 'builtin':
            return 'bundled'
        if raw_source == 'official' or install_root == 'official':
            return 'official'
        return raw_source or install_root or 'unknown'

    def _populate(self):
        self.table.setRowCount(len(self._records))
        for row, record in enumerate(self._records):
            plugin_id = record.get('plugin_id', '')
            checkbox = QtWidgets.QCheckBox(self.table)
            enabled = bool(self._enablement_overrides.get(plugin_id, record.get('enabled', True)))
            checkbox.setChecked(enabled)
            checkbox.stateChanged.connect(
                lambda state, pid=plugin_id: self._on_enabled_changed(pid, state)
            )

            cell = QtWidgets.QWidget(self.table)
            cell_layout = QtWidgets.QHBoxLayout(cell)
            cell_layout.setContentsMargins(6, 0, 6, 0)
            cell_layout.addWidget(checkbox)
            cell_layout.addStretch(1)
            self.table.setCellWidget(row, 0, cell)

            values = [
                record.get('display_name', ''),
                record.get('provider_name', ''),
                record.get('ownership_class', ''),
                record.get('distribution_channel', ''),
                record.get('trust_level', ''),
                record.get('install_root', ''),
                plugin_id,
                record.get('plugin_type', ''),
                self._display_source_label(record),
                record.get('version', ''),
                record.get('status', ''),
            ]

            badge_columns = {3, 4, 5, 9}
            for col, value in enumerate(values, start=1):
                if col in badge_columns:
                    item = self._make_badge_item(value, record)
                else:
                    item = QtWidgets.QTableWidgetItem(str(value))
                    item.setData(QtCore.Qt.UserRole, record)
                self.table.setItem(row, col, item)

        if self._records:
            self.table.selectRow(0)

    def _on_enabled_changed(self, plugin_id, state):
        self._enablement_overrides[str(plugin_id)] = bool(state == QtCore.Qt.Checked)

    def _refresh_details(self):
        items = self.table.selectedItems()
        if not items:
            self.details.clear()
            return

        record = items[0].data(QtCore.Qt.UserRole) or {}
        manifest = record.get('manifest') or {}
        lines = [
            f"Name: {record.get('display_name', '')}",
            f"Plugin ID: {record.get('plugin_id', '')}",
            f"Provider: {record.get('provider_name', '')} ({record.get('provider_id', '')})",
            f"Ownership: {record.get('ownership_class', '')}",
            f"Distribution channel: {record.get('distribution_channel', '')}",
            f"Distribution source: {record.get('distribution_source', '')}",
            f"Trust level: {record.get('trust_level', '')}",
            f"Install root: {record.get('install_root', '')}",
            f"Type: {record.get('plugin_type', '')}",
            f"Source: {record.get('source', '')}",
            f"Location: {record.get('location', '')}",
            f"Version: {record.get('version', '')}",
            f"Status: {record.get('status', '')}",
        ]

        error = record.get('error', '')
        if error:
            lines.append(f'Error: {error}')

        if manifest:
            lines.append('')
            lines.append('Manifest:')
            lines.append(json.dumps(manifest, indent=2))

        self.details.setPlainText("\n".join(lines))

    def enablement_overrides(self):
        return dict(self._enablement_overrides)