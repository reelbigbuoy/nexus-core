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
# File: command_service.py
# Description: Registers commands and dispatches command execution within the application context.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .command_contract import (
    COMMAND_AVAILABLE_KEY,
    COMMAND_RECENT_KEY,
    COMMAND_REGISTRY_KEY,
    SHORTCUT_REGISTRY_KEY,
    CommandDescriptor,
    build_command_availability,
    build_command_descriptor,
    build_command_execution_result,
    build_command_registry,
    build_shortcut_registry,
)
from .context_contract import CONTEXT_ACTIVE_TOOL_KEY, CONTEXT_INSPECTABLE_TARGET_KEY


@dataclass
class CommandRegistration:
    descriptor: CommandDescriptor
    callback: Callable[[Dict[str, Any]], Any]
    availability_callback: Optional[Callable[[Dict[str, Any]], bool]] = None


class CommandService:
    def __init__(self, data_store=None, plugin_manager=None, workspace_manager=None, max_history: int = 100):
        self.data_store = data_store
        self.plugin_manager = plugin_manager
        self.workspace_manager = workspace_manager
        self._registrations: Dict[str, CommandRegistration] = {}
        self._subscriptions = []
        self._recent: List[Dict[str, Any]] = []
        self._shortcut_overrides: Dict[str, str] = {}
        self._max_history = max(10, int(max_history or 100))
        self._connect()
        self._publish_snapshots()

    def _connect(self):
        if self.data_store is None:
            return
        self._subscriptions.append(self.data_store.subscribe(CONTEXT_ACTIVE_TOOL_KEY, lambda _payload: self._publish_snapshots()))
        self._subscriptions.append(self.data_store.subscribe(CONTEXT_INSPECTABLE_TARGET_KEY, lambda _payload: self._publish_snapshots()))
        self._subscriptions.append(self.data_store.subscribe('platform.plugin_registry', lambda _payload: self._publish_snapshots()))

    def register_command(self, *, command_id: str, title: str, callback, description: str = '', plugin_id: Optional[str] = None, tool_type_id: Optional[str] = None, category: str = 'General', shortcut: Optional[str] = None, requires_active_tool: bool = False, requires_inspectable_target: bool = False, requires_selection_kind: Optional[str] = None, required_capabilities=None, metadata=None, keywords=None, availability_callback=None):
        descriptor = build_command_descriptor(
            command_id=command_id,
            title=title,
            description=description,
            plugin_id=plugin_id,
            tool_type_id=tool_type_id,
            category=category,
            shortcut=shortcut,
            requires_active_tool=requires_active_tool,
            requires_inspectable_target=requires_inspectable_target,
            requires_selection_kind=requires_selection_kind,
            required_capabilities=required_capabilities,
            metadata=metadata,
            keywords=keywords,
        )
        registration = CommandRegistration(descriptor=descriptor, callback=callback, availability_callback=availability_callback)
        self._registrations[descriptor.command_id] = registration
        self._publish_snapshots()
        return registration

    def unregister_command(self, command_id: str):
        if command_id in self._registrations:
            self._registrations.pop(command_id, None)
            self._shortcut_overrides.pop(command_id, None)
            self._publish_snapshots()

    def shortcut_bindings(self) -> Dict[str, str]:
        return dict(self._shortcut_overrides)

    def set_shortcut_bindings(self, bindings=None):
        self._shortcut_overrides = {
            str(command_id): str(shortcut)
            for command_id, shortcut in dict(bindings or {}).items()
            if str(command_id).strip() and str(shortcut).strip()
        }
        self._publish_snapshots()

    def set_shortcut_override(self, command_id: str, shortcut: str):
        command_id = str(command_id or '').strip()
        shortcut = str(shortcut or '').strip()
        if not command_id:
            return
        if shortcut:
            self._shortcut_overrides[command_id] = shortcut
        else:
            self._shortcut_overrides.pop(command_id, None)
        self._publish_snapshots()

    def clear_shortcut_override(self, command_id: str):
        command_id = str(command_id or '').strip()
        if command_id in self._shortcut_overrides:
            self._shortcut_overrides.pop(command_id, None)
            self._publish_snapshots()

    def command_descriptors(self) -> List[Dict[str, Any]]:
        return [self._effective_descriptor_dict(registration.descriptor) for registration in sorted(self._registrations.values(), key=lambda item: ((item.descriptor.category or ''), (item.descriptor.title or ''), item.descriptor.command_id))]

    def current_context(self) -> Dict[str, Any]:
        if self.data_store is None:
            return {}
        active_tool = self.data_store.get(CONTEXT_ACTIVE_TOOL_KEY) or {}
        inspectable_target = self.data_store.get(CONTEXT_INSPECTABLE_TARGET_KEY) or {}
        return {
            'active_tool': active_tool,
            'inspectable_target': inspectable_target,
        }

    def available_commands(self) -> List[Dict[str, Any]]:
        context = self.current_context()
        active_tool = context.get('active_tool') if isinstance(context.get('active_tool'), dict) else {}
        inspectable_target = context.get('inspectable_target') if isinstance(context.get('inspectable_target'), dict) else {}
        capabilities = self._active_capabilities(active_tool)
        available = []
        for registration in sorted(self._registrations.values(), key=lambda item: ((item.descriptor.category or ''), (item.descriptor.title or ''), item.descriptor.command_id)):
            ok, reason = self._is_available(registration, active_tool, inspectable_target, capabilities, context)
            if ok:
                available.append(build_command_availability(self._effective_descriptor_dict(registration.descriptor), available=True, reason=reason, context=self._small_context(context)))
        return available

    def available_commands_for_shortcut(self, shortcut: str) -> List[Dict[str, Any]]:
        normalized = str(shortcut or '').strip().lower()
        if not normalized:
            return []
        return [item for item in self.available_commands() if normalized == str(((item.get('descriptor') or {}).get('shortcut') or item.get('shortcut') or '')).strip().lower()]

    def search_available_commands(self, query: str = '') -> List[Dict[str, Any]]:
        commands = self.available_commands()
        query = str(query or '').strip().lower()
        if not query:
            return commands
        tokens = [token for token in query.split() if token]
        ranked = []
        for item in commands:
            descriptor = item.get('descriptor') if isinstance(item, dict) else {}
            haystack_parts = [
                descriptor.get('title') or item.get('title') or '',
                descriptor.get('description') or '',
                descriptor.get('category') or item.get('category') or '',
                descriptor.get('command_id') or item.get('command_id') or '',
                descriptor.get('shortcut') or item.get('shortcut') or '',
                ' '.join(descriptor.get('keywords') or []),
            ]
            haystack = ' '.join(str(part) for part in haystack_parts if part).lower()
            if all(token in haystack for token in tokens):
                score = 0
                title = str(descriptor.get('title') or item.get('title') or '').lower()
                command_id = str(descriptor.get('command_id') or item.get('command_id') or '').lower()
                category = str(descriptor.get('category') or item.get('category') or '').lower()
                if query == title:
                    score += 100
                if query and query in title:
                    score += 60
                if query and query in command_id:
                    score += 40
                if query and query in category:
                    score += 20
                score += max(0, 10 - len(title))
                ranked.append((score, item))
        ranked.sort(key=lambda pair: (-pair[0], (pair[1].get('category') or ''), (pair[1].get('title') or ''), (pair[1].get('command_id') or '')))
        return [item for _score, item in ranked]

    def command_registry_snapshot(self) -> Dict[str, Any]:
        return build_command_registry(commands=self.command_descriptors())

    def shortcut_registry_snapshot(self) -> Dict[str, Any]:
        entries = []
        for registration in sorted(self._registrations.values(), key=lambda item: ((item.descriptor.category or ''), (item.descriptor.title or ''), item.descriptor.command_id)):
            descriptor = registration.descriptor
            default_shortcut = str(descriptor.shortcut or '').strip()
            effective_shortcut = self.effective_shortcut(descriptor.command_id)
            override_shortcut = str(self._shortcut_overrides.get(descriptor.command_id) or '').strip()
            entries.append({
                'command_id': descriptor.command_id,
                'title': descriptor.title,
                'category': descriptor.category,
                'default_shortcut': default_shortcut,
                'shortcut': effective_shortcut,
                'override_shortcut': override_shortcut,
                'plugin_id': descriptor.plugin_id,
                'tool_type_id': descriptor.tool_type_id,
            })
        return build_shortcut_registry(entries)

    def effective_shortcut(self, command_id: str) -> str:
        registration = self._registrations.get(str(command_id or '').strip())
        if registration is None:
            return ''
        return str(self._shortcut_overrides.get(registration.descriptor.command_id) or registration.descriptor.shortcut or '').strip()

    def execute(self, command_id: str) -> Dict[str, Any]:
        registration = self._registrations.get(str(command_id or ''))
        if registration is None:
            result = build_command_execution_result(command_id=command_id, handled=False, status='unknown_command', error='Command is not registered.')
            self._record(result)
            return result
        context = self.current_context()
        active_tool = context.get('active_tool') if isinstance(context.get('active_tool'), dict) else {}
        inspectable_target = context.get('inspectable_target') if isinstance(context.get('inspectable_target'), dict) else {}
        capabilities = self._active_capabilities(active_tool)
        ok, reason = self._is_available(registration, active_tool, inspectable_target, capabilities, context)
        if not ok:
            result = build_command_execution_result(command_id=command_id, handled=False, status='unavailable', error=reason or 'Command is not currently available.')
            self._record(result)
            return result
        payload = {
            'command': self._effective_descriptor_dict(registration.descriptor),
            'context': context,
            'active_tool_widget': self._resolve_active_tool_widget(active_tool),
        }
        try:
            raw = registration.callback(payload)
            if isinstance(raw, dict) and raw.get('contract') == 'command.execution_result.v1':
                result = raw
            elif isinstance(raw, dict):
                handled = bool(raw.get('handled', True))
                result = build_command_execution_result(command_id=command_id, handled=handled, status=raw.get('status') or ('handled' if handled else 'unhandled'), error=raw.get('error'), data=raw.get('data') or {})
            elif isinstance(raw, bool):
                result = build_command_execution_result(command_id=command_id, handled=raw, status='handled' if raw else 'unhandled')
            else:
                result = build_command_execution_result(command_id=command_id, handled=True, status='handled')
        except Exception as exc:
            result = build_command_execution_result(command_id=command_id, handled=False, status='failed', error=str(exc))
        self._record(result)
        return result

    def _record(self, result: Dict[str, Any]):
        self._recent.append(dict(result))
        if len(self._recent) > self._max_history:
            self._recent = self._recent[-self._max_history:]
        self._publish_snapshots()

    def _publish_snapshots(self):
        if self.data_store is None:
            return
        try:
            self.data_store.set(COMMAND_REGISTRY_KEY, self.command_registry_snapshot(), publish_event=False)
            self.data_store.set(COMMAND_AVAILABLE_KEY, self.available_commands(), publish_event=False)
            self.data_store.set(COMMAND_RECENT_KEY, list(self._recent), publish_event=False)
            self.data_store.set(SHORTCUT_REGISTRY_KEY, self.shortcut_registry_snapshot(), publish_event=False)
        except Exception:
            pass

    def _small_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        active_tool = context.get('active_tool') if isinstance(context.get('active_tool'), dict) else {}
        inspectable_target = context.get('inspectable_target') if isinstance(context.get('inspectable_target'), dict) else {}
        return {
            'active_tool': {
                'tool_type_id': active_tool.get('tool_type_id'),
                'plugin_id': active_tool.get('plugin_id'),
                'tool_title': active_tool.get('tool_title'),
            },
            'inspectable_target': {
                'available': bool(inspectable_target),
                'selection_kind': inspectable_target.get('selection_kind') if isinstance(inspectable_target, dict) else None,
            },
        }

    def _active_capabilities(self, active_tool: Dict[str, Any]) -> List[str]:
        if self.plugin_manager is None or not isinstance(active_tool, dict):
            return []
        manifest = self.plugin_manager.plugin_manifest(active_tool.get('plugin_id')) if active_tool.get('plugin_id') else None
        if not isinstance(manifest, dict):
            return []
        return [str(item.get('name')) for item in (manifest.get('capabilities') or []) if isinstance(item, dict) and item.get('name')]

    def _is_available(self, registration: CommandRegistration, active_tool: Dict[str, Any], inspectable_target: Dict[str, Any], capabilities: List[str], context: Dict[str, Any]):
        descriptor = registration.descriptor
        if descriptor.requires_active_tool and not active_tool:
            return False, 'No active tool.'
        if descriptor.plugin_id and descriptor.plugin_id != (active_tool.get('plugin_id') if isinstance(active_tool, dict) else None):
            return False, 'Active tool belongs to a different plugin.'
        if descriptor.tool_type_id and descriptor.tool_type_id != (active_tool.get('tool_type_id') if isinstance(active_tool, dict) else None):
            return False, 'Active tool type does not match.'
        if descriptor.requires_inspectable_target and not inspectable_target:
            return False, 'No inspectable target is active.'
        if descriptor.requires_selection_kind and descriptor.requires_selection_kind != (inspectable_target.get('selection_kind') if isinstance(inspectable_target, dict) else None):
            return False, 'Selection kind does not match.'
        if descriptor.required_capabilities:
            missing = [name for name in descriptor.required_capabilities if name not in capabilities]
            if missing:
                return False, 'Missing active capabilities: %s' % ', '.join(missing)
        if registration.availability_callback is not None:
            try:
                ok = bool(registration.availability_callback(context))
            except Exception:
                ok = False
            if not ok:
                return False, 'Availability callback returned false.'
        return True, None

    def _resolve_active_tool_widget(self, active_tool: Dict[str, Any]):
        if self.workspace_manager is None or not isinstance(active_tool, dict):
            return None
        tool_id = active_tool.get('tool_id')
        if not tool_id:
            return None
        record = getattr(getattr(self.workspace_manager, 'model', None), 'tools', {}).get(tool_id)
        return getattr(record, 'widget', None) if record is not None else None

    def _effective_descriptor_dict(self, descriptor: CommandDescriptor) -> Dict[str, Any]:
        payload = descriptor.to_dict()
        payload['shortcut'] = self.effective_shortcut(descriptor.command_id) or None
        payload['default_shortcut'] = str(descriptor.shortcut or '').strip()
        payload['override_shortcut'] = str(self._shortcut_overrides.get(descriptor.command_id) or '').strip()
        return payload
