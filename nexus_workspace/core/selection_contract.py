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
# File: selection_contract.py
# Description: Defines selection payload contracts and helpers for normalized selection data.
#============================================================================

from __future__ import annotations

from typing import Any, Dict, Optional


SELECTION_CURRENT_KEY = 'selection.current'
SELECTION_CURRENT_CONTRACT = 'selection.current.v1'


REQUIRED_SELECTION_FIELDS = (
    'contract',
    'id',
    'kind',
    'display_name',
    'source',
    'properties',
    'metadata',
)


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_or_none(value: Any) -> Optional[str]:
    if value in (None, ''):
        return None
    return str(value)


def build_selection_payload(
    *,
    object_id: Any,
    kind: str,
    display_name: Any = None,
    source: Optional[Dict[str, Any]] = None,
    properties: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    contract: str = SELECTION_CURRENT_CONTRACT,
) -> Dict[str, Any]:
    normalized_source = {
        'plugin_id': _string_or_none(_coerce_mapping(source).get('plugin_id')),
        'tool_id': _string_or_none(_coerce_mapping(source).get('tool_id')),
        'tool_title': _string_or_none(_coerce_mapping(source).get('tool_title')),
    }
    payload = {
        'contract': contract,
        'id': _string_or_none(object_id) or '',
        'kind': _string_or_none(kind) or 'selection',
        'display_name': _string_or_none(display_name) or _string_or_none(object_id) or 'Selection',
        'source': normalized_source,
        'properties': dict(_coerce_mapping(properties)),
        'metadata': dict(_coerce_mapping(metadata)),
    }
    return payload



def validate_selection_payload(payload: Any) -> Dict[str, Any]:
    issues = []
    if payload is None:
        return {'valid': True, 'issues': [], 'normalized': None}
    if not isinstance(payload, dict):
        return {'valid': False, 'issues': ['payload is not a dictionary'], 'normalized': None}

    normalized = normalize_selection_payload(payload)
    for field in REQUIRED_SELECTION_FIELDS:
        if field not in normalized:
            issues.append(f'missing field: {field}')

    if not normalized.get('id'):
        issues.append('missing field: id')
    if not normalized.get('kind'):
        issues.append('missing field: kind')
    if not isinstance(normalized.get('source'), dict):
        issues.append('source must be a dictionary')
    if not isinstance(normalized.get('properties'), dict):
        issues.append('properties must be a dictionary')
    if not isinstance(normalized.get('metadata'), dict):
        issues.append('metadata must be a dictionary')
    if normalized.get('contract') != SELECTION_CURRENT_CONTRACT:
        issues.append(f"unexpected contract: {normalized.get('contract')}")

    return {
        'valid': not issues,
        'issues': issues,
        'normalized': normalized,
    }



def normalize_selection_payload(payload: Any) -> Optional[Dict[str, Any]]:
    if payload in (None, False):
        return None
    if not isinstance(payload, dict):
        return None

    source_in = _coerce_mapping(payload.get('source'))
    legacy_meta = _coerce_mapping(payload.get('meta'))
    metadata = dict(_coerce_mapping(payload.get('metadata')))
    if not metadata and legacy_meta:
        metadata = dict(legacy_meta)

    if 'contract' not in payload and metadata.get('contract'):
        contract = metadata.get('contract')
    else:
        contract = payload.get('contract') or SELECTION_CURRENT_CONTRACT

    normalized = {
        'contract': contract,
        'id': _string_or_none(payload.get('id')) or '',
        'kind': _string_or_none(payload.get('kind')) or _string_or_none(payload.get('type')) or 'selection',
        'display_name': _string_or_none(payload.get('display_name')) or _string_or_none(payload.get('title')) or _string_or_none(payload.get('id')) or 'Selection',
        'source': {
            'plugin_id': _string_or_none(source_in.get('plugin_id')) or _string_or_none(payload.get('source_plugin')),
            'tool_id': _string_or_none(source_in.get('tool_id')) or _string_or_none(payload.get('source_tool_id')),
            'tool_title': _string_or_none(source_in.get('tool_title')) or _string_or_none(payload.get('source_title')) or _string_or_none(payload.get('source_tool')),
        },
        'properties': dict(_coerce_mapping(payload.get('properties'))),
        'metadata': metadata,
    }
    return normalized


class SelectionPublisher:
    """Helper for publishing the canonical shared selection contract."""

    def __init__(self, plugin_context=None, tool=None, plugin_id: Optional[str] = None):
        self.plugin_context = plugin_context
        self.tool = tool
        self.plugin_id = plugin_id

    def publish(
        self,
        *,
        object_id: Any,
        kind: str,
        display_name: Any = None,
        properties: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        data_store = getattr(self.plugin_context, 'data_store', None) if self.plugin_context is not None else None
        payload = build_selection_payload(
            object_id=object_id,
            kind=kind,
            display_name=display_name,
            source=self._compose_source(source),
            properties=properties,
            metadata=metadata,
        )
        if data_store is not None:
            data_store.set_selection_current(payload)
        return payload

    def clear(self):
        data_store = getattr(self.plugin_context, 'data_store', None) if self.plugin_context is not None else None
        if data_store is not None:
            data_store.set_selection_current(None)

    def _compose_source(self, source: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        base = dict(_coerce_mapping(source))
        if not base.get('plugin_id'):
            base['plugin_id'] = self.plugin_id or getattr(getattr(self.tool, '__class__', None), 'plugin_id', None)
        if not base.get('tool_id'):
            base['tool_id'] = self._tool_identifier()
        if not base.get('tool_title'):
            base['tool_title'] = self._tool_title()
        return base

    def _tool_identifier(self) -> Optional[str]:
        tool = self.tool
        if tool is None:
            return None
        if hasattr(tool, 'objectName'):
            try:
                name = tool.objectName()
                if name:
                    return str(name)
            except Exception:
                pass
        return f'{tool.__class__.__name__}:{id(tool)}'

    def _tool_title(self) -> Optional[str]:
        tool = self.tool
        if tool is None:
            return None
        if hasattr(tool, 'editor_title'):
            try:
                return tool.editor_title()
            except Exception:
                pass
        if hasattr(tool, 'windowTitle'):
            try:
                return tool.windowTitle()
            except Exception:
                pass
        return None