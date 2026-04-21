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
# File: action_dispatcher.py
# Description: Routes action requests to registered handlers and publishes action lifecycle events.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .action_contract import (
    ACTION_STATUS_FAILED,
    ACTION_STATUS_HANDLED,
    ActionHandlerSpec,
    build_action_result,
    normalize_action_request,
    normalize_action_result,
)
from .action_requests import ACTION_REQUEST_EVENT

ACTION_HANDLED_EVENT = "action.handled"
ACTION_UNHANDLED_EVENT = "action.unhandled"
ACTION_FAILED_EVENT = "action.failed"


@dataclass
class ActionHandlerRegistration:
    action_type: str
    callback: Callable[[Dict[str, Any]], Any]
    plugin_id: Optional[str] = None
    source_plugin_id: Optional[str] = None
    target_kind: Optional[str] = None
    target_contract: Optional[str] = None
    name: Optional[str] = None


class ActionHandlerScope:
    """Utility for grouping plugin-owned action registrations."""

    def __init__(self, dispatcher: Optional['ActionDispatcher'] = None):
        self.dispatcher = dispatcher
        self._registrations: List[ActionHandlerRegistration] = []

    def register(self, **kwargs) -> Optional[ActionHandlerRegistration]:
        if self.dispatcher is None:
            return None
        registration = self.dispatcher.register_handler(**kwargs)
        if registration is not None:
            self._registrations.append(registration)
        return registration

    def register_many(self, *specs: ActionHandlerSpec) -> List[ActionHandlerRegistration]:
        created = []
        for spec in specs:
            registration = self.register(
                action_type=spec.action_type,
                callback=spec.callback,
                plugin_id=spec.plugin_id,
                source_plugin_id=spec.source_plugin_id,
                target_kind=spec.target_kind,
                target_contract=spec.target_contract,
                name=spec.name,
            )
            if registration is not None:
                created.append(registration)
        return created

    def clear(self):
        if self.dispatcher is None:
            self._registrations.clear()
            return
        for registration in list(self._registrations):
            self.dispatcher.unregister_handler(registration)
        self._registrations.clear()


class ActionDispatcher:
    """Route action requests to registered handlers.

    This service decouples request publishers from mutation consumers. Widgets and
    platform tools publish intent once; plugins register the action types they can
    handle. The dispatcher performs lightweight routing using the request target
    metadata and emits diagnostic events for observability.
    """

    def __init__(self, event_bus=None, data_store=None, max_history: int = 200):
        self.event_bus = event_bus
        self.data_store = data_store
        self._registrations: List[ActionHandlerRegistration] = []
        self._event_subscription = None
        self._recent_activity: List[Dict[str, Any]] = []
        self._max_history = max(10, int(max_history or 200))
        if self.event_bus is not None:
            self._event_subscription = self.event_bus.subscribe(ACTION_REQUEST_EVENT, self.dispatch)
        self._publish_diagnostics()

    def set_data_store(self, data_store):
        self.data_store = data_store
        self._publish_diagnostics()

    def create_handler_scope(self) -> ActionHandlerScope:
        return ActionHandlerScope(self)

    def register_handler(
        self,
        *,
        action_type: str,
        callback: Callable[[Dict[str, Any]], Any],
        plugin_id: Optional[str] = None,
        source_plugin_id: Optional[str] = None,
        target_kind: Optional[str] = None,
        target_contract: Optional[str] = None,
        name: Optional[str] = None,
    ) -> ActionHandlerRegistration:
        registration = ActionHandlerRegistration(
            action_type=str(action_type or ''),
            callback=callback,
            plugin_id=plugin_id or None,
            source_plugin_id=source_plugin_id or None,
            target_kind=target_kind or None,
            target_contract=target_contract or None,
            name=name or getattr(callback, '__name__', 'handler'),
        )
        self._registrations.append(registration)
        self._publish_diagnostics()
        return registration

    def unregister_handler(self, registration: Optional[ActionHandlerRegistration]):
        if registration in self._registrations:
            self._registrations.remove(registration)
            self._publish_diagnostics()

    def handler_snapshot(self) -> List[Dict[str, Any]]:
        handlers = []
        for registration in self._registrations:
            handlers.append({
                'action_type': registration.action_type,
                'plugin_id': registration.plugin_id,
                'source_plugin_id': registration.source_plugin_id,
                'target_kind': registration.target_kind,
                'target_contract': registration.target_contract,
                'name': registration.name,
            })
        return handlers

    def recent_activity(self) -> List[Dict[str, Any]]:
        return list(self._recent_activity)

    def diagnostics_snapshot(self) -> Dict[str, Any]:
        return {
            'contract': 'platform.action_dispatcher.v1',
            'handlers': self.handler_snapshot(),
            'recent_activity': self.recent_activity(),
        }

    def dispatch(self, request: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        request = normalize_action_request(request)
        action_type = str(request.get('action_type') or '')
        target = request.get('target') if isinstance(request.get('target'), dict) else {}
        source = request.get('source') if isinstance(request.get('source'), dict) else {}
        target_plugin = target.get('source_plugin')
        target_kind = target.get('selection_kind')
        target_contract = target.get('selection_contract')
        source_plugin = source.get('plugin_id')

        matched = [
            registration
            for registration in list(self._registrations)
            if self._matches(registration, action_type, target_plugin, target_kind, target_contract, source_plugin)
        ]

        if not matched:
            result = {'handled': False, 'status': 'unhandled', 'handler_count': 0, 'request': request, 'results': []}
            self._record_activity(request, result)
            self._emit(ACTION_UNHANDLED_EVENT, {
                'request': request,
                'reason': 'no_handler_registered',
            })
            return result

        handled = False
        results = []
        for registration in matched:
            try:
                result = registration.callback(request)
                normalized_result = normalize_action_result(
                    result,
                    request=request,
                    handler_name=registration.name,
                    plugin_id=registration.plugin_id,
                )
                results.append(normalized_result)
                if normalized_result.get('status') == ACTION_STATUS_HANDLED or normalized_result.get('handled'):
                    handled = True
            except Exception as exc:
                normalized_result = build_action_result(
                    request=request,
                    status=ACTION_STATUS_FAILED,
                    handled=False,
                    handler_name=registration.name,
                    plugin_id=registration.plugin_id,
                    error=str(exc),
                )
                results.append(normalized_result)
                self._emit(ACTION_FAILED_EVENT, {
                    'request': request,
                    'result': normalized_result,
                })

        event_type = ACTION_HANDLED_EVENT if handled else ACTION_UNHANDLED_EVENT
        self._emit(event_type, {
            'request': request,
            'results': results,
            'handled': handled,
            'handler_count': len(matched),
        })
        final_result = {
            'handled': handled,
            'handler_count': len(matched),
            'status': ACTION_STATUS_HANDLED if handled else 'unhandled',
            'request': request,
            'results': results,
        }
        self._record_activity(request, final_result)
        return final_result

    def shutdown(self):
        if self.event_bus is not None and self._event_subscription is not None:
            try:
                self.event_bus.unsubscribe(ACTION_REQUEST_EVENT, self._event_subscription)
            except Exception:
                pass
            self._event_subscription = None

    def _matches(self, registration: ActionHandlerRegistration, action_type: str, target_plugin: Optional[str], target_kind: Optional[str], target_contract: Optional[str], source_plugin: Optional[str]) -> bool:
        if registration.action_type != action_type:
            return False
        if registration.plugin_id and registration.plugin_id != target_plugin:
            return False
        if registration.source_plugin_id and registration.source_plugin_id != source_plugin:
            return False
        if registration.target_kind and registration.target_kind != target_kind:
            return False
        if registration.target_contract and registration.target_contract != target_contract:
            return False
        return True

    def _emit(self, event_type: str, payload: Dict[str, Any]):
        if self.event_bus is not None:
            self.event_bus.publish(event_type, payload)

    def _record_activity(self, request: Dict[str, Any], result: Dict[str, Any]):
        self._recent_activity.append({
            'request': request,
            'result': result,
        })
        if len(self._recent_activity) > self._max_history:
            self._recent_activity = self._recent_activity[-self._max_history:]
        self._publish_diagnostics()

    def _publish_diagnostics(self):
        if self.data_store is None:
            return
        try:
            snapshot = self.diagnostics_snapshot()
            self.data_store.set('platform.action_dispatcher', snapshot, publish_event=False)
            self.data_store.set('platform.action_handlers', snapshot.get('handlers', []), publish_event=False)
            self.data_store.set('platform.actions.recent', snapshot.get('recent_activity', []), publish_event=False)
        except Exception:
            pass