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
# File: command_contract.py
# Description: Defines command metadata, command payload contracts, and command normalization helpers.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

COMMAND_DESCRIPTOR_CONTRACT = "command.descriptor.v1"
COMMAND_REGISTRY_CONTRACT = "platform.command_registry.v1"
COMMAND_AVAILABILITY_CONTRACT = "command.availability.v1"
COMMAND_AVAILABLE_CONTRACT = COMMAND_AVAILABILITY_CONTRACT
COMMAND_EXECUTION_RESULT_CONTRACT = "command.execution_result.v1"
SHORTCUT_REGISTRY_CONTRACT = "platform.shortcut_registry.v1"

COMMAND_REGISTRY_KEY = 'platform.command_registry'
COMMAND_AVAILABLE_KEY = 'context.available_commands'
COMMAND_RECENT_KEY = 'platform.commands.recent'
SHORTCUT_REGISTRY_KEY = 'platform.shortcut_registry'


def _string_or_none(value: Any) -> Optional[str]:
    if value in (None, ''):
        return None
    return str(value)


def _string_list(values) -> List[str]:
    result = []
    for value in values or []:
        normalized = _string_or_none(value)
        if normalized:
            result.append(normalized)
    return result


@dataclass(frozen=True)
class CommandDescriptor:
    command_id: str
    title: str
    description: str = ''
    plugin_id: Optional[str] = None
    tool_type_id: Optional[str] = None
    category: str = 'General'
    shortcut: Optional[str] = None
    requires_active_tool: bool = False
    requires_inspectable_target: bool = False
    requires_selection_kind: Optional[str] = None
    required_capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            'contract': COMMAND_DESCRIPTOR_CONTRACT,
            'command_id': self.command_id,
            'title': self.title,
            'description': self.description,
            'plugin_id': self.plugin_id,
            'tool_type_id': self.tool_type_id,
            'category': self.category,
            'shortcut': self.shortcut,
            'requires_active_tool': self.requires_active_tool,
            'requires_inspectable_target': self.requires_inspectable_target,
            'requires_selection_kind': self.requires_selection_kind,
            'required_capabilities': list(self.required_capabilities or []),
            'metadata': dict(self.metadata or {}),
            'keywords': list(self.keywords or []),
        }


@dataclass(frozen=True)
class CommandContribution:
    command_id: str
    title: str
    description: str = ''
    category: str = 'General'
    shortcut: Optional[str] = None
    tool_type_id: Optional[str] = None
    requires_active_tool: bool = False
    requires_inspectable_target: bool = False
    requires_selection_kind: Optional[str] = None
    required_capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            'command_id': self.command_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'shortcut': self.shortcut,
            'tool_type_id': self.tool_type_id,
            'requires_active_tool': self.requires_active_tool,
            'requires_inspectable_target': self.requires_inspectable_target,
            'requires_selection_kind': self.requires_selection_kind,
            'required_capabilities': list(self.required_capabilities or []),
            'metadata': dict(self.metadata or {}),
            'keywords': list(self.keywords or []),
        }


def build_command_contribution(*, command_id: str, title: str, description: str = '', category: str = 'General', shortcut: Optional[str] = None, tool_type_id: Optional[str] = None, requires_active_tool: bool = False, requires_inspectable_target: bool = False, requires_selection_kind: Optional[str] = None, required_capabilities=None, metadata=None, keywords=None) -> CommandContribution:
    return CommandContribution(
        command_id=str(command_id or ''),
        title=str(title or command_id or 'Command'),
        description=str(description or ''),
        category=str(category or 'General'),
        shortcut=_string_or_none(shortcut),
        tool_type_id=_string_or_none(tool_type_id),
        requires_active_tool=bool(requires_active_tool),
        requires_inspectable_target=bool(requires_inspectable_target),
        requires_selection_kind=_string_or_none(requires_selection_kind),
        required_capabilities=_string_list(required_capabilities),
        metadata=dict(metadata or {}),
        keywords=_string_list(keywords),
    )


def build_command_descriptor(*, command_id: str, title: str, description: str = '', plugin_id: Optional[str] = None, tool_type_id: Optional[str] = None, category: str = 'General', shortcut: Optional[str] = None, requires_active_tool: bool = False, requires_inspectable_target: bool = False, requires_selection_kind: Optional[str] = None, required_capabilities=None, metadata=None, keywords=None) -> CommandDescriptor:
    return CommandDescriptor(
        command_id=str(command_id or ''),
        title=str(title or command_id or 'Command'),
        description=str(description or ''),
        plugin_id=_string_or_none(plugin_id),
        tool_type_id=_string_or_none(tool_type_id),
        category=str(category or 'General'),
        shortcut=_string_or_none(shortcut),
        requires_active_tool=bool(requires_active_tool),
        requires_inspectable_target=bool(requires_inspectable_target),
        requires_selection_kind=_string_or_none(requires_selection_kind),
        required_capabilities=_string_list(required_capabilities),
        metadata=dict(metadata or {}),
        keywords=_string_list(keywords),
    )


def build_command_registry(commands=None, categories=None):
    normalized = []
    for command in commands or []:
        if hasattr(command, 'to_dict'):
            normalized.append(command.to_dict())
        elif isinstance(command, dict):
            normalized.append(dict(command))
    return {
        'contract': COMMAND_REGISTRY_CONTRACT,
        'commands': normalized,
        'categories': list(categories or sorted({item.get('category') or 'General' for item in normalized})),
    }


def build_command_availability(command: Any, *, available: bool, reason: Optional[str] = None, context=None):
    descriptor = command.to_dict() if hasattr(command, 'to_dict') else dict(command or {})
    return {
        'contract': COMMAND_AVAILABILITY_CONTRACT,
        'command_id': descriptor.get('command_id'),
        'title': descriptor.get('title'),
        'category': descriptor.get('category') or 'General',
        'plugin_id': descriptor.get('plugin_id'),
        'tool_type_id': descriptor.get('tool_type_id'),
        'shortcut': descriptor.get('shortcut'),
        'available': bool(available),
        'reason': _string_or_none(reason),
        'context': dict(context or {}),
        'descriptor': descriptor,
    }


def build_command_execution_result(*, command_id: str, handled: bool, status: str = 'unhandled', error: Optional[str] = None, data=None):
    return {
        'contract': COMMAND_EXECUTION_RESULT_CONTRACT,
        'command_id': str(command_id or ''),
        'handled': bool(handled),
        'status': str(status or ('handled' if handled else 'unhandled')),
        'error': _string_or_none(error),
        'data': dict(data or {}),
    }


def build_shortcut_registry(entries=None):
    return {
        'contract': SHORTCUT_REGISTRY_CONTRACT,
        'entries': [dict(item) for item in (entries or [])],
    }
