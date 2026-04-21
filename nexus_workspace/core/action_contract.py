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
# File: action_contract.py
# Description: Defines action request and result contracts plus helpers for normalizing action payloads.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import uuid

ACTION_REQUEST_CONTRACT = 'action.request.v1'
ACTION_RESULT_CONTRACT = 'action.result.v1'

PROPERTY_EDIT_REQUEST = 'property.edit.requested'

ACTION_STATUS_HANDLED = 'handled'
ACTION_STATUS_UNHANDLED = 'unhandled'
ACTION_STATUS_FAILED = 'failed'


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_or_none(value: Any) -> Optional[str]:
    if value in (None, ''):
        return None
    return str(value)


def build_action_request(
    *,
    action_type: str,
    target: Optional[Dict[str, Any]] = None,
    payload: Optional[Dict[str, Any]] = None,
    source: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    contract: str = ACTION_REQUEST_CONTRACT,
) -> Dict[str, Any]:
    normalized_payload = dict(_coerce_mapping(payload))
    return {
        'contract': contract,
        'request_id': _string_or_none(request_id) or str(uuid.uuid4()),
        'action_type': str(action_type or ''),
        'target': dict(_coerce_mapping(target)),
        'payload': normalized_payload,
        'source': dict(_coerce_mapping(source)),
        'meta': dict(_coerce_mapping(meta)),
        # Legacy compatibility keys. These can be retired later.
        'event_type': str(action_type or ''),
        **({'value': normalized_payload.get('value')} if 'value' in normalized_payload else {}),
    }



def normalize_action_request(value: Any) -> Dict[str, Any]:
    mapping = _coerce_mapping(value)
    action_type = _string_or_none(mapping.get('action_type')) or _string_or_none(mapping.get('event_type')) or ''
    payload = dict(_coerce_mapping(mapping.get('payload')))
    if 'value' in mapping and 'value' not in payload:
        payload['value'] = mapping.get('value')
    normalized = build_action_request(
        action_type=action_type,
        target=mapping.get('target'),
        payload=payload,
        source=mapping.get('source'),
        meta=mapping.get('meta'),
        request_id=_string_or_none(mapping.get('request_id')),
        contract=_string_or_none(mapping.get('contract')) or ACTION_REQUEST_CONTRACT,
    )
    return normalized



def build_action_result(
    *,
    request: Optional[Dict[str, Any]] = None,
    status: str = ACTION_STATUS_UNHANDLED,
    handled: Optional[bool] = None,
    handler_name: Optional[str] = None,
    plugin_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    contract: str = ACTION_RESULT_CONTRACT,
) -> Dict[str, Any]:
    request = normalize_action_request(request)
    if handled is None:
        handled = status == ACTION_STATUS_HANDLED
    return {
        'contract': contract,
        'request_id': request.get('request_id'),
        'action_type': request.get('action_type'),
        'status': str(status or ACTION_STATUS_UNHANDLED),
        'handled': bool(handled),
        'handler_name': _string_or_none(handler_name),
        'plugin_id': _string_or_none(plugin_id),
        'data': dict(_coerce_mapping(data)),
        'error': _string_or_none(error),
    }



def normalize_action_result(
    value: Any,
    *,
    request: Optional[Dict[str, Any]] = None,
    handler_name: Optional[str] = None,
    plugin_id: Optional[str] = None,
) -> Dict[str, Any]:
    if isinstance(value, bool):
        return build_action_result(
            request=request,
            status=ACTION_STATUS_HANDLED if value else ACTION_STATUS_UNHANDLED,
            handled=bool(value),
            handler_name=handler_name,
            plugin_id=plugin_id,
        )
    if isinstance(value, dict):
        status = _string_or_none(value.get('status'))
        handled = value.get('handled') if 'handled' in value else None
        data = dict(_coerce_mapping(value.get('data')))
        if not data:
            reserved = {'contract', 'request_id', 'action_type', 'status', 'handled', 'handler_name', 'plugin_id', 'data', 'error'}
            data = {k: v for k, v in value.items() if k not in reserved}
        return build_action_result(
            request=request,
            status=status or (ACTION_STATUS_HANDLED if bool(handled) else ACTION_STATUS_UNHANDLED),
            handled=handled,
            handler_name=_string_or_none(value.get('handler_name')) or handler_name,
            plugin_id=_string_or_none(value.get('plugin_id')) or plugin_id,
            data=data,
            error=_string_or_none(value.get('error')),
            contract=_string_or_none(value.get('contract')) or ACTION_RESULT_CONTRACT,
        )
    return build_action_result(
        request=request,
        status=ACTION_STATUS_UNHANDLED,
        handled=False,
        handler_name=handler_name,
        plugin_id=plugin_id,
    )


@dataclass
class ActionHandlerSpec:
    action_type: str
    callback: Any
    plugin_id: Optional[str] = None
    source_plugin_id: Optional[str] = None
    target_kind: Optional[str] = None
    target_contract: Optional[str] = None
    name: Optional[str] = None