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
# File: data_model.py
# Description: Builds generic inspectable data model structures and editor metadata for property-driven UIs.
#============================================================================

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .inspectable_contract import build_field_descriptor, build_inspectable_object, build_section, infer_value_type

DATA_MODEL_CONTRACT = 'data.model.v1'


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _string_or_none(value: Any) -> Optional[str]:
    if value in (None, ''):
        return None
    return str(value)


def _normalize_editor(editor: Any, *, value_type: str) -> Optional[Dict[str, Any]]:
    if not isinstance(editor, dict):
        return None
    kind = _string_or_none(editor.get('kind')) or _default_editor_kind(value_type)
    normalized: Dict[str, Any] = {
        'kind': kind,
        'placeholder': _string_or_none(editor.get('placeholder')),
        'multiline': bool(editor.get('multiline', False)),
        'clearable': bool(editor.get('clearable', True)),
    }
    options = []
    for option in _coerce_list(editor.get('options')):
        if isinstance(option, dict):
            options.append({
                'value': option.get('value'),
                'label': _string_or_none(option.get('label')) or str(option.get('value')),
            })
        else:
            options.append({'value': option, 'label': str(option)})
    if options:
        normalized['options'] = options
    numeric = _coerce_mapping(editor.get('numeric'))
    if numeric:
        normalized['numeric'] = {
            'minimum': numeric.get('minimum'),
            'maximum': numeric.get('maximum'),
            'decimals': int(numeric.get('decimals', 0) or 0),
            'step': numeric.get('step'),
        }
    return normalized


def _default_editor_kind(value_type: str) -> str:
    value_type = str(value_type or 'string')
    if value_type == 'bool':
        return 'bool'
    if value_type in {'int', 'float'}:
        return 'number'
    return 'text'


def build_data_field(
    *,
    field_path: str,
    label: str,
    value: Any = None,
    value_type: Optional[str] = None,
    editable: bool = False,
    required: bool = False,
    description: Optional[str] = None,
    placeholder: Optional[str] = None,
    category: Optional[str] = None,
    editor: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    resolved_type = str(value_type or infer_value_type(value) or 'string')
    resolved_editor = dict(editor or {})
    if placeholder and 'placeholder' not in resolved_editor:
        resolved_editor['placeholder'] = placeholder
    return {
        'field_path': str(field_path or ''),
        'label': str(label or field_path or 'Value'),
        'value': value,
        'value_type': resolved_type,
        'editable': bool(editable),
        'required': bool(required),
        'description': _string_or_none(description),
        'category': _string_or_none(category),
        'editor': _normalize_editor(resolved_editor, value_type=resolved_type),
        'metadata': dict(_coerce_mapping(metadata)),
    }


def build_data_section(*, section_id: str, title: str, fields: Optional[Iterable[Dict[str, Any]]] = None, description: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        'id': str(section_id or title or 'section'),
        'title': str(title or section_id or 'Section'),
        'description': _string_or_none(description),
        'fields': [normalize_data_field(field) for field in (fields or []) if normalize_data_field(field) is not None],
        'metadata': dict(_coerce_mapping(metadata)),
    }


def build_data_model(
    *,
    model_id: Any,
    model_type: str,
    display_name: Optional[str] = None,
    sections: Optional[Iterable[Dict[str, Any]]] = None,
    summary: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    contract: str = DATA_MODEL_CONTRACT,
) -> Dict[str, Any]:
    return {
        'contract': contract,
        'id': _string_or_none(model_id) or '',
        'model_type': _string_or_none(model_type) or 'object',
        'display_name': _string_or_none(display_name) or _string_or_none(model_id) or 'Object',
        'summary': dict(_coerce_mapping(summary)),
        'sections': [normalize_data_section(section) for section in _coerce_list(sections)],
        'metadata': dict(_coerce_mapping(metadata)),
    }


def normalize_data_field(field: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(field, dict):
        return None
    field_path = _string_or_none(field.get('field_path')) or _string_or_none(field.get('path')) or ''
    value = field.get('value')
    value_type = _string_or_none(field.get('value_type')) or infer_value_type(value)
    return {
        'field_path': field_path,
        'label': _string_or_none(field.get('label')) or field_path.rsplit('.', 1)[-1] or 'Value',
        'value': value,
        'value_type': value_type,
        'editable': bool(field.get('editable', False)),
        'required': bool(field.get('required', False)),
        'description': _string_or_none(field.get('description')),
        'category': _string_or_none(field.get('category')),
        'editor': _normalize_editor(field.get('editor'), value_type=value_type),
        'metadata': dict(_coerce_mapping(field.get('metadata'))),
    }


def normalize_data_section(section: Any) -> Dict[str, Any]:
    section_map = _coerce_mapping(section)
    fields = []
    for field in _coerce_list(section_map.get('fields')):
        normalized = normalize_data_field(field)
        if normalized is not None:
            fields.append(normalized)
    return {
        'id': _string_or_none(section_map.get('id')) or _string_or_none(section_map.get('title')) or 'section',
        'title': _string_or_none(section_map.get('title')) or _string_or_none(section_map.get('id')) or 'Section',
        'description': _string_or_none(section_map.get('description')),
        'fields': fields,
        'metadata': dict(_coerce_mapping(section_map.get('metadata'))),
    }


def normalize_data_model(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    contract = _string_or_none(value.get('contract')) or DATA_MODEL_CONTRACT
    normalized = {
        'contract': contract,
        'id': _string_or_none(value.get('id')) or '',
        'model_type': _string_or_none(value.get('model_type')) or _string_or_none(value.get('object_type')) or 'object',
        'display_name': _string_or_none(value.get('display_name')) or _string_or_none(value.get('id')) or 'Object',
        'summary': dict(_coerce_mapping(value.get('summary'))),
        'sections': [normalize_data_section(section) for section in _coerce_list(value.get('sections'))],
        'metadata': dict(_coerce_mapping(value.get('metadata'))),
    }
    if normalized['contract'] != DATA_MODEL_CONTRACT:
        return None
    return normalized


def data_model_to_inspectable(value: Any) -> Optional[Dict[str, Any]]:
    model = normalize_data_model(value)
    if model is None:
        return None
    sections = []
    for section in model.get('sections') or []:
        inspectable_fields = []
        for field in section.get('fields') or []:
            inspectable_fields.append(build_field_descriptor(
                field_path=field.get('field_path') or '',
                label=field.get('label') or field.get('field_path') or 'Value',
                value=field.get('value'),
                value_type=field.get('value_type') or infer_value_type(field.get('value')),
                editable=bool(field.get('editable', False)),
                category=field.get('category'),
                description=field.get('description'),
                editor=field.get('editor'),
            ))
        sections.append(build_section(
            section_id=section.get('id') or section.get('title') or 'section',
            title=section.get('title') or section.get('id') or 'Section',
            fields=inspectable_fields,
        ))
    metadata = dict(model.get('metadata') or {})
    metadata['data_model_contract'] = model.get('contract')
    return build_inspectable_object(
        object_id=model.get('id') or '',
        object_type=model.get('model_type') or 'object',
        display_name=model.get('display_name') or model.get('id') or 'Object',
        sections=sections,
        summary=dict(model.get('summary') or {}),
        metadata=metadata,
    )