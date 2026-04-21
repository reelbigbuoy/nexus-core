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
# File: inspectable_contract.py
# Description: Defines generic inspectable object, section, and field descriptors for inspectors.
#============================================================================

from __future__ import annotations

from typing import Any, Dict, List, Optional

INSPECTABLE_OBJECT_CONTRACT = 'inspectable.object.v1'


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _string_or_none(value: Any) -> Optional[str]:
    if value in (None, ''):
        return None
    return str(value)


def _normalize_editor(editor: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(editor, dict):
        return None
    normalized = {
        'kind': _string_or_none(editor.get('kind')) or 'text',
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



def build_field_descriptor(
    *,
    field_path: str,
    label: str,
    value: Any,
    value_type: str,
    editable: bool = False,
    category: Optional[str] = None,
    description: Optional[str] = None,
    editor: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        'field_path': str(field_path or ''),
        'label': str(label or field_path or 'Value'),
        'value': value,
        'value_type': str(value_type or 'string'),
        'editable': bool(editable),
        'category': _string_or_none(category),
        'description': _string_or_none(description),
        'editor': _normalize_editor(editor),
    }



def build_section(*, section_id: str, title: str, fields: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    return {
        'id': str(section_id or title or 'section'),
        'title': str(title or section_id or 'Section'),
        'fields': list(fields or []),
    }



def build_inspectable_object(
    *,
    object_id: Any,
    object_type: str,
    display_name: Optional[str] = None,
    sections: Optional[List[Dict[str, Any]]] = None,
    summary: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    contract: str = INSPECTABLE_OBJECT_CONTRACT,
) -> Dict[str, Any]:
    return {
        'contract': contract,
        'id': _string_or_none(object_id) or '',
        'object_type': _string_or_none(object_type) or 'object',
        'display_name': _string_or_none(display_name) or _string_or_none(object_id) or 'Object',
        'summary': dict(_coerce_mapping(summary)),
        'sections': [normalize_section(section) for section in _coerce_list(sections)],
        'metadata': dict(_coerce_mapping(metadata)),
    }



def normalize_field_descriptor(field: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(field, dict):
        return None
    field_path = _string_or_none(field.get('field_path')) or _string_or_none(field.get('path')) or ''
    label = _string_or_none(field.get('label')) or field_path.rsplit('.', 1)[-1] or 'Value'
    return {
        'field_path': field_path,
        'label': label,
        'value': field.get('value'),
        'value_type': _string_or_none(field.get('value_type')) or infer_value_type(field.get('value')),
        'editable': bool(field.get('editable', False)),
        'category': _string_or_none(field.get('category')),
        'description': _string_or_none(field.get('description')),
        'editor': _normalize_editor(field.get('editor')),
    }



def normalize_section(section: Any) -> Dict[str, Any]:
    section_map = _coerce_mapping(section)
    fields = []
    for field in _coerce_list(section_map.get('fields')):
        normalized = normalize_field_descriptor(field)
        if normalized is not None:
            fields.append(normalized)
    return {
        'id': _string_or_none(section_map.get('id')) or _string_or_none(section_map.get('title')) or 'section',
        'title': _string_or_none(section_map.get('title')) or _string_or_none(section_map.get('id')) or 'Section',
        'fields': fields,
    }



def normalize_inspectable_object(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    contract = _string_or_none(value.get('contract')) or INSPECTABLE_OBJECT_CONTRACT
    normalized = {
        'contract': contract,
        'id': _string_or_none(value.get('id')) or '',
        'object_type': _string_or_none(value.get('object_type')) or _string_or_none(value.get('kind')) or 'object',
        'display_name': _string_or_none(value.get('display_name')) or _string_or_none(value.get('id')) or 'Object',
        'summary': dict(_coerce_mapping(value.get('summary'))),
        'sections': [normalize_section(section) for section in _coerce_list(value.get('sections'))],
        'metadata': dict(_coerce_mapping(value.get('metadata'))),
    }
    if normalized['contract'] != INSPECTABLE_OBJECT_CONTRACT:
        return None
    return normalized



def infer_value_type(value: Any) -> str:
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, int) and not isinstance(value, bool):
        return 'int'
    if isinstance(value, float):
        return 'float'
    if isinstance(value, (list, tuple, set)):
        return 'list'
    if isinstance(value, dict):
        return 'object'
    return 'string'