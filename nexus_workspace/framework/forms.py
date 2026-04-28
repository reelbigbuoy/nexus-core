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
# File: forms.py
# Description: Provides reusable form-building helpers and field widgets for data-entry interfaces.
#============================================================================

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from .controls import (
    NexusButton, NexusCheckBox, NexusComboBox, NexusDoubleSpinBox, NexusLabel,
    NexusSection, NexusSpinBox, NexusTextEditor, NexusTextInput,
)


class NexusSearchBar(QtWidgets.QWidget):
    def __init__(self, parent=None, *, placeholder='Search…', button_text='Refresh'):
        super().__init__(parent)
        self.setObjectName('NexusSearchBar')
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.searchEdit = NexusTextInput(parent=self, placeholder=placeholder, clear_button=True)
        self.primaryButton = NexusButton(button_text, self)
        layout.addWidget(self.searchEdit, 1)
        layout.addWidget(self.primaryButton, 0)


class NexusFieldRow(QtWidgets.QWidget):
    def __init__(self, label='', field=None, parent=None, *, help_text=''):
        super().__init__(parent)
        self.setObjectName('NexusFieldRow')
        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(4)
        self.label = NexusLabel(str(label or ''), self)
        self.label.setObjectName('NexusFieldLabel')
        self.label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        layout.addWidget(self.label, 0, 0)
        self.field = field or QtWidgets.QWidget(self)
        layout.addWidget(self.field, 0, 1)
        layout.setColumnStretch(1, 1)
        self.helpLabel = None
        if help_text:
            self.helpLabel = NexusLabel(str(help_text), self, word_wrap=True)
            self.helpLabel.setObjectName('NexusFieldHelpText')
            layout.addWidget(self.helpLabel, 1, 1)


class NexusForm(QtWidgets.QWidget):
    def __init__(self, parent=None, *, margins=(0, 0, 0, 0), spacing=10):
        super().__init__(parent)
        self.setObjectName('NexusForm')
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(*margins)
        self._layout.setSpacing(spacing)

    def add_row(self, label, field, *, help_text=''):
        row = NexusFieldRow(label=label, field=field, parent=self, help_text=help_text)
        self._layout.addWidget(row, 0)
        return row

    def add_widget(self, widget, stretch=0):
        self._layout.addWidget(widget, stretch)

    def add_stretch(self):
        self._layout.addStretch(1)

    def layout_widget(self):
        return self._layout


class NexusInspectorSection(NexusSection):
    def __init__(self, title='', parent=None, *, help_text=''):
        super().__init__(title=title, parent=parent)
        self.setObjectName('NexusInspectorSection')
        self.form = NexusForm(self)
        self.body_layout().addWidget(self.form, 1)
        self.helpLabel = None
        if help_text:
            self.helpLabel = NexusLabel(str(help_text), self, word_wrap=True)
            self.helpLabel.setObjectName('NexusFieldHelpText')
            self.form.layout_widget().insertWidget(0, self.helpLabel)

from ..core.data_model import normalize_data_model


class NexusDataModelForm(QtWidgets.QScrollArea):
    """Schema-driven form surface backed by the canonical data.model.v1 contract."""

    fieldValueEdited = QtCore.pyqtSignal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('NexusDataModelForm')
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._editors = {}
        self._model = None

        self._container = QtWidgets.QWidget(self)
        self._layout = QtWidgets.QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(12)
        self._layout.addStretch(1)
        self.setWidget(self._container)

    def clear_form(self):
        self._editors = {}
        self._model = None
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._layout.addStretch(1)

    def set_data_model(self, model_payload):
        model = normalize_data_model(model_payload)
        self.clear_form()
        self._model = model
        if model is None:
            placeholder = NexusLabel('No data model is available for this selection.', self._container, word_wrap=True)
            placeholder.setObjectName('NexusFieldHelpText')
            self._layout.insertWidget(0, placeholder)
            return

        for section in model.get('sections') or []:
            section_widget = NexusInspectorSection(
                title=section.get('title') or 'Section',
                parent=self._container,
                help_text=section.get('description') or '',
            )
            for field in section.get('fields') or []:
                editor = self._create_editor(field)
                if editor is None:
                    continue
                row = section_widget.form.add_row(
                    field.get('label') or field.get('field_path') or 'Value',
                    editor,
                    help_text=field.get('description') or '',
                )
                if field.get('required') and row.label is not None:
                    row.label.setText(f"{row.label.text()} *")
            section_widget.form.add_stretch()
            self._layout.insertWidget(self._layout.count() - 1, section_widget)

    def _create_editor(self, field):
        field_path = str(field.get('field_path') or '').strip()
        if not field_path:
            return None
        editable = bool(field.get('editable', False))
        value = field.get('value')
        value_type = str(field.get('value_type') or 'string')
        editor_hint = field.get('editor') if isinstance(field.get('editor'), dict) else {}
        kind = str(editor_hint.get('kind') or '')
        placeholder = str(editor_hint.get('placeholder') or '')
        multiline = bool(editor_hint.get('multiline', False))

        if kind == 'choice':
            editor = NexusComboBox(self._container)
            current_index = -1
            for index, option in enumerate(editor_hint.get('options') or []):
                option_value = option.get('value') if isinstance(option, dict) else option
                option_label = option.get('label') if isinstance(option, dict) else str(option)
                editor.addItem(str(option_label), option_value)
                if option_value == value:
                    current_index = index
            if current_index >= 0:
                editor.setCurrentIndex(current_index)
            editor.currentIndexChanged.connect(lambda _idx, e=editor, p=field_path: self.fieldValueEdited.emit(p, e.currentData()))
        elif value_type == 'bool' or kind == 'bool':
            editor = NexusCheckBox(parent=self._container)
            editor.setChecked(bool(value))
            editor.toggled.connect(lambda checked, p=field_path: self.fieldValueEdited.emit(p, bool(checked)))
        elif value_type == 'int':
            editor = NexusSpinBox(self._container)
            numeric = editor_hint.get('numeric') if isinstance(editor_hint.get('numeric'), dict) else {}
            editor.setMinimum(int(numeric.get('minimum', -2147483648) or -2147483648))
            editor.setMaximum(int(numeric.get('maximum', 2147483647) or 2147483647))
            editor.setSingleStep(int(numeric.get('step', 1) or 1))
            editor.setValue(int(value or 0))
            editor.editingFinished.connect(lambda e=editor, p=field_path: self.fieldValueEdited.emit(p, int(e.value())))
        elif value_type == 'float':
            editor = NexusDoubleSpinBox(self._container)
            numeric = editor_hint.get('numeric') if isinstance(editor_hint.get('numeric'), dict) else {}
            editor.setDecimals(int(numeric.get('decimals', 3) or 3))
            editor.setMinimum(float(numeric.get('minimum', -999999999.0) or -999999999.0))
            editor.setMaximum(float(numeric.get('maximum', 999999999.0) or 999999999.0))
            editor.setSingleStep(float(numeric.get('step', 0.1) or 0.1))
            editor.setValue(float(value or 0.0))
            editor.editingFinished.connect(lambda e=editor, p=field_path: self.fieldValueEdited.emit(p, float(e.value())))
        else:
            if multiline:
                editor = NexusTextEditor(self._container)
                editor.setPlainText('' if value is None else str(value))
                editor.setPlaceholderText(placeholder)
                editor.focusOutEvent = self._wrap_focus_out(editor.focusOutEvent, lambda e=editor, p=field_path: self.fieldValueEdited.emit(p, e.toPlainText()))
            else:
                editor = NexusTextInput(self._container)
                editor.setText('' if value is None else str(value))
                editor.setPlaceholderText(placeholder)
                editor.editingFinished.connect(lambda e=editor, p=field_path: self.fieldValueEdited.emit(p, e.text()))
        editor.setEnabled(editable)
        self._editors[field_path] = editor
        return editor

    def _wrap_focus_out(self, original_handler, callback):
        def wrapped(event):
            callback()
            return original_handler(event)
        return wrapped