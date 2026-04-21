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
# File: property_grid.py
# Description: Implements the property grid widget for editing structured field descriptors.
#============================================================================

import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from PyQt5 import QtCore, QtWidgets

from ..core.selection_contract import normalize_selection_payload
from ..core.inspectable_contract import normalize_inspectable_object
from ..core.data_model import data_model_to_inspectable


PropertyRow = Tuple[str, Any, Optional[str]]
RendererFunc = Callable[[Any, QtWidgets.QWidget], QtWidgets.QWidget]
EditableResolver = Callable[[str, Any], bool]


class PropertyValueRendererRegistry:
    """Registry for read-only and editable property renderers used by the shared property grid."""

    def __init__(self):
        self._typed_renderers: List[Tuple[type, RendererFunc]] = []
        self._predicate_renderers: List[Tuple[Callable[[Any], bool], RendererFunc]] = []
        self._register_defaults()

    def _register_defaults(self):
        self.register_type(bool, self._render_bool)
        self.register_type(int, self._render_scalar)
        self.register_type(float, self._render_scalar)
        self.register_type(str, self._render_scalar)
        self.register_predicate(lambda value: value is None, self._render_scalar)
        self.register_predicate(lambda value: isinstance(value, (dict, list, tuple, set)), self._render_structured)

    def register_type(self, value_type: type, renderer: RendererFunc):
        self._typed_renderers.append((value_type, renderer))

    def register_predicate(self, predicate: Callable[[Any], bool], renderer: RendererFunc):
        self._predicate_renderers.append((predicate, renderer))

    def render(self, value: Any, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
        for value_type, renderer in self._typed_renderers:
            if isinstance(value, value_type):
                return renderer(value, parent)
        for predicate, renderer in self._predicate_renderers:
            try:
                if predicate(value):
                    return renderer(value, parent)
            except Exception:
                continue
        return self._render_scalar(value, parent)

    def create_editor(self, field_path: str, value: Any, parent: QtWidgets.QWidget, descriptor: Optional[Dict[str, Any]] = None) -> Optional[QtWidgets.QWidget]:
        descriptor = descriptor or {}
        editor_hint = descriptor.get('editor') if isinstance(descriptor.get('editor'), dict) else {}
        editor_kind = str(editor_hint.get('kind') or '')
        value_type = str(descriptor.get('value_type') or '')

        if editor_kind == 'choice':
            editor = QtWidgets.QComboBox(parent)
            options = editor_hint.get('options') or []
            current_index = -1
            for idx, option in enumerate(options):
                option_value = option.get('value') if isinstance(option, dict) else option
                option_label = option.get('label') if isinstance(option, dict) else str(option)
                editor.addItem(str(option_label), option_value)
                if option_value == value:
                    current_index = idx
            if current_index >= 0:
                editor.setCurrentIndex(current_index)
            editor.setObjectName('PropertyChoiceEditor')
            editor.field_path = field_path
            editor.original_value = value
            return editor

        numeric = editor_hint.get('numeric') if isinstance(editor_hint, dict) else {}
        minimum = numeric.get('minimum') if isinstance(numeric, dict) else None
        maximum = numeric.get('maximum') if isinstance(numeric, dict) else None
        decimals = int((numeric or {}).get('decimals', 0) or 0) if isinstance(numeric, dict) else 0
        step = (numeric or {}).get('step') if isinstance(numeric, dict) else None

        if value_type == 'bool' or isinstance(value, bool):
            editor = QtWidgets.QCheckBox(parent)
            editor.setChecked(bool(value))
            editor.setObjectName('PropertyBooleanEditor')
            editor.field_path = field_path
            editor.original_value = bool(value)
            return editor
        if value_type == 'int' or (isinstance(value, int) and not isinstance(value, bool)):
            editor = QtWidgets.QSpinBox(parent)
            editor.setRange(int(minimum if minimum is not None else -999999999), int(maximum if maximum is not None else 999999999))
            if step is not None:
                editor.setSingleStep(int(step))
            editor.setValue(int(value))
            editor.setObjectName('PropertySpinEditor')
            editor.field_path = field_path
            editor.original_value = int(value)
            return editor
        if value_type == 'float' or isinstance(value, float):
            editor = QtWidgets.QDoubleSpinBox(parent)
            editor.setRange(float(minimum if minimum is not None else -1e12), float(maximum if maximum is not None else 1e12))
            editor.setDecimals(max(0, decimals or 6))
            if step is not None:
                editor.setSingleStep(float(step))
            editor.setValue(float(value))
            editor.setObjectName('PropertyDoubleEditor')
            editor.field_path = field_path
            editor.original_value = float(value)
            return editor
        if value_type == 'string' or isinstance(value, str) or editor_kind in {'text', 'multiline'}:
            if editor_kind == 'multiline' or bool(editor_hint.get('multiline', False)):
                editor = QtWidgets.QPlainTextEdit(parent)
                editor.setPlainText('' if value is None else str(value))
                editor.setFixedHeight(84)
                editor.setObjectName('PropertyMultilineEditor')
                editor.field_path = field_path
                editor.original_value = '' if value is None else str(value)
                return editor
            editor = QtWidgets.QLineEdit(parent)
            editor.setText('' if value is None else str(value))
            editor.setClearButtonEnabled(bool(editor_hint.get('clearable', True)))
            placeholder = editor_hint.get('placeholder')
            if placeholder:
                editor.setPlaceholderText(str(placeholder))
            editor.setObjectName('PropertyLineEditor')
            editor.field_path = field_path
            editor.original_value = '' if value is None else str(value)
            return editor
        return None

    def _render_bool(self, value: bool, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
        checkbox = QtWidgets.QCheckBox(parent)
        checkbox.setChecked(bool(value))
        checkbox.setEnabled(False)
        checkbox.setObjectName('PropertyBooleanValue')
        return checkbox

    def _render_scalar(self, value: Any, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
        label = QtWidgets.QLabel(self._format_scalar(value), parent)
        label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        label.setWordWrap(True)
        label.setObjectName('PropertyScalarValue')
        return label

    def _render_structured(self, value: Any, parent: QtWidgets.QWidget) -> QtWidgets.QWidget:
        text = QtWidgets.QPlainTextEdit(parent)
        text.setReadOnly(True)
        text.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        text.setPlainText(self._format_structured(value))
        text.setFixedHeight(self._preferred_text_height(value, parent.fontMetrics()))
        text.setObjectName('PropertyStructuredValue')
        return text

    def _format_scalar(self, value: Any) -> str:
        if value is None:
            return '—'
        return str(value)

    def _format_structured(self, value: Any) -> str:
        try:
            return json.dumps(value, indent=2, sort_keys=True)
        except TypeError:
            return repr(value)

    def _preferred_text_height(self, value: Any, metrics) -> int:
        if isinstance(value, dict):
            line_count = max(4, min(12, len(value) + 2))
        elif isinstance(value, (list, tuple, set)):
            line_count = max(4, min(12, len(value) + 2))
        else:
            line_count = 6
        return (metrics.lineSpacing() * line_count) + 16


class PropertySectionWidget(QtWidgets.QFrame):
    """Card-style section used by the property inspector grid."""

    def __init__(self, title: str, rows: Iterable[PropertyRow], renderer_registry: PropertyValueRendererRegistry, parent=None, editable_resolver: Optional[EditableResolver] = None, descriptor_resolver: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None):
        super().__init__(parent)
        self.setObjectName('PropertySection')
        self.fieldEdited = None
        self._descriptor_resolver = descriptor_resolver

        row_items = [self._normalize_row(row) for row in rows]

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QtWidgets.QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)

        title_label = QtWidgets.QLabel(title, self)
        title_label.setObjectName('PropertySectionTitle')
        header.addWidget(title_label, 1)

        count_label = QtWidgets.QLabel(str(len(row_items) if row_items else 1), self)
        count_label.setObjectName('PropertySectionCount')
        count_label.setAlignment(QtCore.Qt.AlignCenter)
        count_label.setMinimumWidth(24)
        header.addWidget(count_label, 0)

        layout.addLayout(header)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)

        if not row_items:
            row_items = [('Value', '—', None)]

        for row_index, (label, value, field_path) in enumerate(row_items):
            key_label = QtWidgets.QLabel(str(label), self)
            key_label.setObjectName('PropertyRowLabel')
            key_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
            key_label.setWordWrap(True)
            grid.addWidget(key_label, row_index, 0, QtCore.Qt.AlignTop)

            descriptor = self._descriptor_resolver(field_path) if callable(self._descriptor_resolver) and field_path else None
            value_widget = None
            if field_path and editable_resolver and editable_resolver(field_path, value):
                value_widget = renderer_registry.create_editor(field_path, value, self, descriptor=descriptor)
                if value_widget is not None:
                    self._connect_editor(value_widget, field_path)
            if value_widget is None:
                value_widget = renderer_registry.render(value, self)
            if descriptor and descriptor.get('description') and hasattr(value_widget, 'setToolTip'):
                value_widget.setToolTip(str(descriptor.get('description')))
                key_label.setToolTip(str(descriptor.get('description')))
            grid.addWidget(value_widget, row_index, 1)

        layout.addLayout(grid)

    def _normalize_row(self, row: Any) -> PropertyRow:
        if isinstance(row, tuple):
            if len(row) >= 3:
                return (str(row[0]), row[1], row[2])
            if len(row) == 2:
                return (str(row[0]), row[1], None)
        return (str(row), row, None)

    def _connect_editor(self, editor: QtWidgets.QWidget, field_path: str):
        if isinstance(editor, QtWidgets.QLineEdit):
            editor.editingFinished.connect(lambda e=editor, p=field_path: self._emit_edit(p, e.text(), getattr(e, 'original_value', None)))
        elif isinstance(editor, QtWidgets.QPlainTextEdit):
            editor.focusOutEvent = self._wrap_focus_out(editor.focusOutEvent, lambda e=editor, p=field_path: self._emit_edit(p, e.toPlainText(), getattr(e, 'original_value', None)))
        elif isinstance(editor, QtWidgets.QSpinBox):
            editor.editingFinished.connect(lambda e=editor, p=field_path: self._emit_edit(p, int(e.value()), getattr(e, 'original_value', None)))
        elif isinstance(editor, QtWidgets.QDoubleSpinBox):
            editor.editingFinished.connect(lambda e=editor, p=field_path: self._emit_edit(p, float(e.value()), getattr(e, 'original_value', None)))
        elif isinstance(editor, QtWidgets.QCheckBox):
            editor.toggled.connect(lambda value, e=editor, p=field_path: self._emit_edit(p, bool(value), getattr(e, 'original_value', None)))
        elif isinstance(editor, QtWidgets.QComboBox):
            editor.currentIndexChanged.connect(lambda _idx, e=editor, p=field_path: self._emit_edit(p, e.currentData(), getattr(e, 'original_value', None)))

    def _wrap_focus_out(self, original_handler, callback):
        def wrapped(event):
            callback()
            return original_handler(event)
        return wrapped

    def _emit_edit(self, field_path: str, value: Any, original: Any):
        if value == original:
            return
        if callable(self.fieldEdited):
            self.fieldEdited(field_path, value)


class PropertySummaryWidget(QtWidgets.QFrame):
    """High-level summary card for the current selection."""

    def __init__(self, payload: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setObjectName('PropertySummaryCard')

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        display_name = payload.get('display_name') or payload.get('id') or 'Selection'
        title = QtWidgets.QLabel(display_name, self)
        title.setObjectName('PropertySummaryTitle')
        title.setWordWrap(True)
        layout.addWidget(title)

        source = payload.get('source') or {}
        chips_layout = QtWidgets.QHBoxLayout()
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(6)
        chips_layout.addWidget(self._build_chip(payload.get('kind') or 'selection'))
        source_title = source.get('tool_title') or source.get('plugin_id') or 'Unknown source'
        chips_layout.addWidget(self._build_chip(source_title))
        object_id = payload.get('id')
        if object_id:
            chips_layout.addWidget(self._build_chip(object_id))
        chips_layout.addStretch(1)
        layout.addLayout(chips_layout)

    def _build_chip(self, text: str) -> QtWidgets.QLabel:
        chip = QtWidgets.QLabel(str(text), self)
        chip.setObjectName('PropertySummaryChip')
        chip.setAlignment(QtCore.Qt.AlignCenter)
        return chip


class PropertyGridWidget(QtWidgets.QWidget):
    """Reusable property grid for inspecting and editing shared selection payloads."""

    EMPTY_MESSAGE = 'Select something in a tool that publishes selection state'
    propertyEditRequested = QtCore.pyqtSignal(str, object)

    def __init__(self, parent=None, renderer_registry: Optional[PropertyValueRendererRegistry] = None):
        super().__init__(parent)
        self._renderer_registry = renderer_registry or PropertyValueRendererRegistry()
        self._editable_field_paths = set()
        self._field_descriptors: Dict[str, Dict[str, Any]] = {}

        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QtWidgets.QStackedLayout()
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.setStackingMode(QtWidgets.QStackedLayout.StackOne)
        root.addLayout(self._stack, 1)

        self._empty_page = QtWidgets.QWidget(self)
        empty_layout = QtWidgets.QVBoxLayout(self._empty_page)
        empty_layout.setContentsMargins(16, 16, 16, 16)
        empty_layout.setSpacing(10)
        self._empty_label = QtWidgets.QLabel(self.EMPTY_MESSAGE, self._empty_page)
        self._empty_label.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft)
        self._empty_label.setWordWrap(True)
        self._empty_label.setObjectName('PropertyGridEmptyState')
        empty_layout.addWidget(self._empty_label, 0, QtCore.Qt.AlignTop)
        empty_layout.addStretch(1)

        self._scroll = QtWidgets.QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._scroll.setObjectName('PropertyGridScrollArea')
        self._container = QtWidgets.QWidget(self._scroll)
        self._container.setObjectName('PropertyGridContainer')
        self._layout = QtWidgets.QVBoxLayout(self._container)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)
        self._layout.addStretch(1)
        self._scroll.setWidget(self._container)

        self._stack.addWidget(self._empty_page)
        self._stack.addWidget(self._scroll)
        self.show_empty_state(self.EMPTY_MESSAGE)

    def clear_content(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)
        self._layout.addStretch(1)

    def _clear_layout(self, layout: QtWidgets.QLayout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            child_layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif child_layout is not None:
                self._clear_layout(child_layout)

    def show_empty_state(self, message: str):
        self._empty_label.setText(message or self.EMPTY_MESSAGE)
        self._stack.setCurrentWidget(self._empty_page)

    def set_payload(self, payload: Dict[str, Any]):
        payload = normalize_selection_payload(payload)
        if not payload:
            self._editable_field_paths = set()
            self._field_descriptors = {}
            self.show_empty_state(self.EMPTY_MESSAGE)
            return

        self.clear_content()
        self._editable_field_paths = set()
        self._field_descriptors = {}
        self._layout.insertWidget(self._layout.count() - 1, PropertySummaryWidget(payload, self._container))

        inspectable = self._extract_inspectable(payload)
        if inspectable:
            self._render_inspectable_payload(payload, inspectable)
        else:
            self._render_legacy_payload(payload)

        self._stack.setCurrentWidget(self._scroll)

    def _extract_inspectable(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        metadata = payload.get('metadata') or {}
        inspectable = normalize_inspectable_object(metadata.get('inspectable'))
        if inspectable is None:
            inspectable = data_model_to_inspectable(metadata.get('data_model'))
        return inspectable

    def _render_inspectable_payload(self, payload: Dict[str, Any], inspectable: Dict[str, Any]):
        summary_rows = self._filtered_rows([
            ('Display Name', inspectable.get('display_name'), None),
            ('Object Type', inspectable.get('object_type'), None),
            ('Contract', inspectable.get('contract'), None),
            ('Selection Contract', payload.get('contract'), None),
        ])
        self._insert_section('Selection', summary_rows)

        for section in inspectable.get('sections') or []:
            rows: List[PropertyRow] = []
            for field in section.get('fields') or []:
                field_path = field.get('field_path') or None
                label = field.get('label') or field_path or 'Value'
                rows.append((str(label), field.get('value'), field_path))
                if field_path:
                    self._field_descriptors[field_path] = field
                    if field.get('editable'):
                        self._editable_field_paths.add(field_path)
            self._insert_section(section.get('title') or 'Section', rows)

    def _render_legacy_payload(self, payload: Dict[str, Any]):
        metadata = payload.get('metadata') or {}
        editable_fields = metadata.get('editable_fields') or []
        self._editable_field_paths = {str(path) for path in editable_fields if path}

        source = payload.get('source') or {}
        identity_rows = self._filtered_rows([
            ('Display Name', payload.get('display_name'), None),
            ('Kind', payload.get('kind'), None),
            ('Id', payload.get('id'), None),
            ('Contract', payload.get('contract'), None),
            ('Source Plugin', source.get('plugin_id'), None),
            ('Source Tool Id', source.get('tool_id'), None),
            ('Source Title', source.get('tool_title'), None),
        ])
        self._insert_section('Selection', identity_rows)

        properties = payload.get('properties') or {}
        if properties:
            self._insert_property_sections('Properties', properties, root_path='properties')

        metadata = payload.get('metadata') or {}
        if metadata:
            self._insert_property_sections('Metadata', metadata, root_path='metadata')

    def _insert_section(self, title: str, rows: Iterable[PropertyRow]):
        section = PropertySectionWidget(
            title,
            list(rows),
            self._renderer_registry,
            self._container,
            editable_resolver=self._is_editable_field,
            descriptor_resolver=self._descriptor_for_field_path,
        )
        section.fieldEdited = self._forward_edit_request
        self._layout.insertWidget(self._layout.count() - 1, section)

    def _insert_property_sections(self, title: str, properties: Dict[str, Any], root_path: str):
        scalar_rows: List[PropertyRow] = []
        structured_rows: List[PropertyRow] = []
        nested_sections: List[Tuple[str, List[PropertyRow], str]] = []

        for key in sorted(properties.keys(), key=lambda item: str(item).lower()):
            value = properties.get(key)
            field_path = f'{root_path}.{key}'
            if isinstance(value, dict) and value:
                nested_sections.append((self._format_section_title(title, key), self._rows_from_mapping(value, prefix=field_path), field_path))
            elif isinstance(value, (list, tuple, set, dict)):
                structured_rows.append((str(key), value, None))
            else:
                scalar_rows.append((str(key), value, field_path))

        if scalar_rows:
            self._insert_section(title, scalar_rows)
        if structured_rows:
            self._insert_section(f'{title} Details', structured_rows)
        for nested_title, rows, _nested_root in nested_sections:
            self._insert_section(nested_title, rows)

    def _rows_from_mapping(self, mapping: Dict[str, Any], prefix: Optional[str] = None) -> List[PropertyRow]:
        rows: List[PropertyRow] = []
        for key in sorted(mapping.keys(), key=lambda item: str(item).lower()):
            field_path = f'{prefix}.{key}' if prefix else None
            rows.append((str(key), mapping.get(key), field_path))
        return rows

    def _filtered_rows(self, rows: Iterable[PropertyRow]) -> List[PropertyRow]:
        return [(label, value, field_path) for label, value, field_path in rows if value not in (None, '')]

    def _format_section_title(self, root_title: str, key: Any) -> str:
        key_text = str(key).replace('_', ' ').strip()
        if not key_text:
            return root_title
        return f'{root_title} · {key_text.title()}'

    def _descriptor_for_field_path(self, field_path: str) -> Optional[Dict[str, Any]]:
        return self._field_descriptors.get(field_path)

    def _is_editable_field(self, field_path: str, value: Any) -> bool:
        if field_path not in self._editable_field_paths:
            return False
        descriptor = self._descriptor_for_field_path(field_path)
        if descriptor is not None:
            value_type = descriptor.get('value_type')
            return value_type in {'string', 'int', 'float', 'bool'}
        return isinstance(value, (str, int, float, bool))

    def _forward_edit_request(self, field_path: str, value: Any):
        self.propertyEditRequested.emit(field_path, value)