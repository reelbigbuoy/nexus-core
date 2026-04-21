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
# File: ecosystem.py
# Description: Defines reusable staged tool shells for platform tools and plugin-facing workspace experiences.
#============================================================================

from __future__ import annotations

from typing import Iterable, Sequence
import json

from PyQt5 import QtCore, QtWidgets

from nexus_workspace.framework.controls import NexusSection
from nexus_workspace.framework.tools import NexusToolBase


class EcosystemShellTool(NexusToolBase):
    """Reusable staged tool shell for new Nexus ecosystem plugins."""

    tool_type_id = ''
    display_name = ''
    default_subtitle = ''
    shell_summary = ''
    shell_focus_areas: Sequence[str] = ()
    shell_document_types: Sequence[str] = ()
    shell_integration_points: Sequence[str] = ()
    shell_next_steps: Sequence[str] = ()

    def __init__(self, parent=None, *, theme_name='Midnight', editor_title='', plugin_context=None):
        super().__init__(parent, theme_name=theme_name, editor_title=editor_title or self.display_name, plugin_context=plugin_context)
        self.ensure_header(title=self.display_name, subtitle=self.default_subtitle)
        self._build_shell_ui()
        self.sync_framework_toolbar()

    def _build_shell_ui(self):
        layout = self.content_layout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        summary = QtWidgets.QLabel(self.shell_summary or self.default_subtitle or '', self)
        summary.setWordWrap(True)
        summary.setObjectName('NexusFieldHelpText')
        layout.addWidget(summary)

        layout.addWidget(self._build_list_section('Near-term focus', self.shell_focus_areas))
        layout.addWidget(self._build_list_section('Planned project document types', self.shell_document_types))
        layout.addWidget(self._build_list_section('Planned platform integrations', self.shell_integration_points))
        layout.addWidget(self._build_list_section('Implementation sequence', self.shell_next_steps))
        overview = self._build_platform_overview_section()
        if overview is not None:
            layout.addWidget(overview)
        layout.addStretch(1)

    def _build_list_section(self, title: str, lines: Iterable[str]):
        section = NexusSection(title, self)
        body = section.body_layout()
        body.setSpacing(6)
        entries = list(lines or [])
        if not entries:
            placeholder = QtWidgets.QLabel('Planned work will appear here as the tool is implemented.', section)
            placeholder.setWordWrap(True)
            placeholder.setObjectName('NexusFieldHelpText')
            body.addWidget(placeholder)
            return section
        for line in entries:
            row = QtWidgets.QLabel(f'• {line}', section)
            row.setWordWrap(True)
            body.addWidget(row)
        return section

    def default_toolbar_command_ids(self):
        return []


    def _build_platform_overview_section(self):
        context = getattr(self, 'plugin_context', None)
        if context is None:
            return None

        section = NexusSection('Platform snapshot', self)
        body = section.body_layout()
        body.setSpacing(6)

        snapshot_fields = (
            ('project_registry_snapshot', 'Project registry'),
            ('graph_registry_snapshot', 'Graph domains'),
            ('review_registry_snapshot', 'Review support'),
        )

        added_any = False
        for attr_name, title in snapshot_fields:
            value = getattr(context, attr_name, None)
            if not value:
                continue
            added_any = True
            label = QtWidgets.QLabel(title, section)
            font = label.font()
            font.setBold(True)
            label.setFont(font)
            body.addWidget(label)

            viewer = QtWidgets.QPlainTextEdit(section)
            viewer.setReadOnly(True)
            viewer.setMaximumHeight(140)
            viewer.setPlainText(json.dumps(value, indent=2, sort_keys=True))
            body.addWidget(viewer)

        if not added_any:
            placeholder = QtWidgets.QLabel('Platform registry data will appear here when available.', section)
            placeholder.setWordWrap(True)
            placeholder.setObjectName('NexusFieldHelpText')
            body.addWidget(placeholder)

        return section