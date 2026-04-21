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
# Description: Implements the bundled property inspector tool for editing inspectable properties.
#============================================================================

from PyQt5 import QtCore

from ...core.serialization import NexusSerializable
from ...core.selection_contract import SELECTION_CURRENT_KEY, normalize_selection_payload
from ...core.inspectable_contract import normalize_inspectable_object
from ...core.data_model import data_model_to_inspectable
from ...core.context_contract import CONTEXT_INSPECTABLE_TARGET_KEY
from ...core.action_requests import ActionRequestPublisher
from ...framework import NexusPropertyGrid, NexusToolBase


class PropertyInspectorTool(NexusToolBase, NexusSerializable):
    tool_type_id = 'property_inspector'
    display_name = 'Property Inspector'

    PRIMARY_KEY = CONTEXT_INSPECTABLE_TARGET_KEY
    FALLBACK_KEY = SELECTION_CURRENT_KEY

    def __init__(self, parent=None, theme_name='Midnight', editor_title='Property Inspector', plugin_context=None):
        super().__init__(parent, theme_name=theme_name, editor_title=editor_title, plugin_context=plugin_context)
        self._primary_subscription = None
        self._current_payload = None
        self._action_publisher = ActionRequestPublisher(plugin_context=plugin_context, source_tool=self)
        self.ensure_header(title='Property Inspector', subtitle='Listening to shared platform context')

        root = self.content_layout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.grid = NexusPropertyGrid(self)
        self.grid.propertyEditRequested.connect(self.request_property_edit)
        root.addWidget(self.grid, 1)
        self._connect_store()
        self._initialize_from_store()

    def build_tool_stylesheet(self, theme):
        return self._build_inspector_stylesheet(theme)

    def _build_inspector_stylesheet(self, theme):
        return f"""
        #PropertyGridContainer {{
            background-color: {theme['app_bg']};
        }}

        #PropertyGridEmptyState {{
            color: {theme['muted_text']};
            padding: 4px 2px;
        }}

        #PropertySummaryCard, #PropertySection {{
            background-color: {theme['panel_bg']};
            border: 1px solid {theme['border']};
            border-radius: 8px;
        }}

        #PropertySummaryTitle {{
            color: {theme['text']};
            font-size: 15px;
            font-weight: 700;
        }}

        #PropertySummaryChip, #PropertySectionCount {{
            background-color: {theme['panel_alt_bg']};
            color: {theme['muted_text']};
            border: 1px solid {theme['border']};
            border-radius: 10px;
            padding: 2px 8px;
        }}

        #PropertySectionTitle {{
            color: {theme['text']};
            font-size: 12px;
            font-weight: 600;
        }}

        #PropertyRowLabel {{
            color: {theme['muted_text']};
            font-weight: 600;
            padding-top: 2px;
        }}

        #PropertyScalarValue {{
            color: {theme['text']};
            background: transparent;
        }}

        #PropertyStructuredValue {{
            background-color: {theme['editor_bg']};
            color: {theme['editor_text']};
            border: 1px solid {theme['border']};
            border-radius: 6px;
        }}

        #PropertyBooleanValue {{
            spacing: 0px;
        }}
        """

    def _connect_store(self):
        data_store = getattr(self.plugin_context, 'data_store', None) if self.plugin_context is not None else None
        if data_store is None:
            self.grid.show_empty_state('DataStore is unavailable for this tool instance')
            return
        if self._primary_subscription is None:
            self._primary_subscription = data_store.subscribe(self.PRIMARY_KEY, self._on_primary_selection_changed)

    def _initialize_from_store(self):
        data_store = getattr(self.plugin_context, 'data_store', None) if self.plugin_context is not None else None
        if data_store is None:
            return
        payload = data_store.get(self.PRIMARY_KEY)
        if payload is None:
            payload = data_store.get(self.FALLBACK_KEY)
        self._set_payload(payload)

    def _on_primary_selection_changed(self, payload):
        self._set_payload(payload)

    def _set_payload(self, payload):
        if isinstance(payload, dict) and payload.get('contract') == 'context.inspectable_target.v1':
            self._set_context_payload(payload)
            return
        normalized = normalize_selection_payload(payload)
        self._current_payload = normalized
        if not normalized:
            self.set_header_subtitle('Listening to shared platform context')
            self.grid.show_empty_state('Select something in a tool that publishes platform context')
            return
        display_name = normalized.get('display_name') or normalized.get('id') or 'Selection'
        source = normalized.get('source') or {}
        source_title = source.get('tool_title') or 'Unknown tool'
        kind = normalized.get('kind') or 'selection'
        metadata = normalized.get('metadata') or {}
        inspectable = normalize_inspectable_object(metadata.get('inspectable'))
        data_model = metadata.get('data_model')
        if inspectable is None:
            inspectable = data_model_to_inspectable(data_model)
        if inspectable:
            contract_name = 'data.model.v1' if data_model else 'inspectable.object.v1'
            self.set_header_subtitle(f'{display_name} · {kind} · {contract_name} · from {source_title}')
        else:
            self.set_header_subtitle(f'{display_name} · {kind} · from {source_title}')
        self.grid.set_payload(normalized)

    def _set_context_payload(self, payload):
        selection = normalize_selection_payload((payload or {}).get('selection'))
        active_tool = (payload or {}).get('active_tool') if isinstance(payload, dict) else {}
        self._current_payload = selection
        if not selection:
            self.set_header_subtitle('Listening to shared platform context')
            self.grid.show_empty_state('Select something in a tool that publishes platform context')
            return
        display_name = selection.get('display_name') or selection.get('id') or 'Selection'
        kind = selection.get('kind') or 'selection'
        inspectable = normalize_inspectable_object((payload or {}).get('inspectable'))
        data_model = (((selection or {}).get('metadata') or {}).get('data_model')) if isinstance(selection, dict) else None
        if inspectable is None:
            inspectable = data_model_to_inspectable(data_model)
        active_tool_title = ''
        if isinstance(active_tool, dict):
            active_tool_title = active_tool.get('tool_title') or active_tool.get('plugin_display_name') or ''
        source_title = ((selection.get('source') or {}).get('tool_title') or 'Unknown tool')
        contract_name = 'data.model.v1' if data_model else 'inspectable.object.v1'
        if inspectable and active_tool_title:
            self.set_header_subtitle(f'{display_name} · {kind} · {contract_name} · active in {active_tool_title}')
        elif inspectable:
            self.set_header_subtitle(f'{display_name} · {kind} · {contract_name} · from {source_title}')
        elif active_tool_title:
            self.set_header_subtitle(f'{display_name} · {kind} · active in {active_tool_title}')
        else:
            self.set_header_subtitle(f'{display_name} · {kind} · from {source_title}')
        self.grid.set_payload(selection)

    def request_property_edit(self, field_path, value):
        if not self._current_payload:
            return None
        return self._action_publisher.request_property_edit(
            target_selection=self._current_payload,
            field_path=field_path,
            value=value,
        )

    def save_state(self):
        return {
            'editor_title': self._editor_title,
        }

    def load_state(self, state):
        if not state:
            return
        title = state.get('editor_title')
        if title:
            self._editor_title = title
            self.setWindowTitle(title)

    def closeEvent(self, event):
        data_store = getattr(self.plugin_context, 'data_store', None) if self.plugin_context is not None else None
        if data_store is not None:
            if self._primary_subscription is not None:
                try:
                    data_store.unsubscribe(self.PRIMARY_KEY, self._primary_subscription)
                except Exception:
                    pass
                self._primary_subscription = None
        super().closeEvent(event)