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
# File: plugin_contract.py
# Description: Defines plugin manifest contracts and normalized plugin metadata helpers.
#============================================================================

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .command_contract import CommandContribution

PLUGIN_MANIFEST_CONTRACT = "plugin.manifest.v1"


@dataclass(frozen=True)
class CapabilityDescriptor:
    name: str
    kind: str
    description: str = ""
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'name': self.name,
            'kind': self.kind,
            'description': self.description,
            'metadata': dict(self.metadata or {}),
        }


@dataclass(frozen=True)
class ToolContribution:
    tool_type_id: str
    display_name: str
    description: str = ""
    widget_type: str = "tool"
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'tool_type_id': self.tool_type_id,
            'display_name': self.display_name,
            'description': self.description,
            'widget_type': self.widget_type,
            'metadata': dict(self.metadata or {}),
        }


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    display_name: str
    version: str = "1.0.0"
    description: str = ""
    tools: List[ToolContribution] = field(default_factory=list)
    publishes: List[str] = field(default_factory=list)
    consumes: List[str] = field(default_factory=list)
    handles_actions: List[str] = field(default_factory=list)
    persists: List[str] = field(default_factory=list)
    commands: List[CommandContribution] = field(default_factory=list)
    capabilities: List[CapabilityDescriptor] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'contract': PLUGIN_MANIFEST_CONTRACT,
            'plugin_id': self.plugin_id,
            'display_name': self.display_name,
            'version': self.version,
            'description': self.description,
            'tools': [tool.to_dict() for tool in self.tools],
            'publishes': list(self.publishes or []),
            'consumes': list(self.consumes or []),
            'handles_actions': list(self.handles_actions or []),
            'persists': list(self.persists or []),
            'commands': [command.to_dict() for command in self.commands],
            'capabilities': [cap.to_dict() for cap in self.capabilities],
            'metadata': dict(self.metadata or {}),
        }


def build_capability(name: str, kind: str, description: str = "", metadata: Optional[Dict[str, object]] = None) -> CapabilityDescriptor:
    return CapabilityDescriptor(name=name, kind=kind, description=description, metadata=dict(metadata or {}))


def build_tool_contribution(tool_type_id: str, display_name: str, description: str = "", widget_type: str = "tool", metadata: Optional[Dict[str, object]] = None) -> ToolContribution:
    return ToolContribution(tool_type_id=tool_type_id, display_name=display_name, description=description, widget_type=widget_type, metadata=dict(metadata or {}))


def build_plugin_manifest(*, plugin_id: str, display_name: str, version: str = "1.0.0", description: str = "", tools: Optional[List[ToolContribution]] = None, publishes: Optional[List[str]] = None, consumes: Optional[List[str]] = None, handles_actions: Optional[List[str]] = None, persists: Optional[List[str]] = None, commands: Optional[List[CommandContribution]] = None, capabilities: Optional[List[CapabilityDescriptor]] = None, metadata: Optional[Dict[str, object]] = None) -> PluginManifest:
    return PluginManifest(
        plugin_id=plugin_id,
        display_name=display_name,
        version=version,
        description=description,
        tools=list(tools or []),
        publishes=list(publishes or []),
        consumes=list(consumes or []),
        handles_actions=list(handles_actions or []),
        persists=list(persists or []),
        commands=list(commands or []),
        capabilities=list(capabilities or []),
        metadata=dict(metadata or {}),
    )
