# ============================================================================
# Nexus
# File: plugins/owner/NoDE/node_plugin/definitions.py
# Description: Source module for node plugin functionality.
# Part of: NoDE Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from PyQt5 import QtCore


@dataclass
class NodePortDefinition:
    id: str
    name: str
    direction: str
    data_type: str = "any"
    connection_kind: Optional[str] = None
    multi_connection: bool = False
    required: bool = False
    default_value: Any = None

    def resolved_connection_kind(self) -> str:
        kind = str(self.connection_kind or '').strip().lower()
        if kind:
            return kind
        data_type = str(self.data_type or 'any').strip().lower()
        if data_type == 'exec':
            return 'exec'
        if data_type == 'requirement':
            return 'requirement'
        return 'data'


@dataclass
class NodePropertyDefinition:
    name: str
    label: str
    property_type: str = "string"
    default: Any = None
    options: List[Any] = field(default_factory=list)
    multiline: bool = False


@dataclass
class NodeVisualDefinition:
    color: Optional[str] = None
    icon: Optional[str] = None
    compact: bool = False


@dataclass
class NodeDefinition:
    type_id: str
    name: str
    category: str
    description: str = ""
    inputs: List[NodePortDefinition] = field(default_factory=list)
    outputs: List[NodePortDefinition] = field(default_factory=list)
    properties: List[NodePropertyDefinition] = field(default_factory=list)
    visual: NodeVisualDefinition = field(default_factory=NodeVisualDefinition)
    tags: List[str] = field(default_factory=list)
    defaults: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    behavior_key: Optional[str] = None
    source_path: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Compatibility alias for older NoDE UI code."""
        return self.name

    def default_properties(self):
        merged = {prop.name: prop.default for prop in self.properties}
        merged.update(self.defaults)
        return merged

    def create_node_entry(self, pos=None, node_id=None, title=None, properties=None):
        pos = pos or QtCore.QPointF(0, 0)
        merged_properties = self.default_properties()
        if properties:
            merged_properties.update(properties)
        return {
            "node_data": TestNodeData(
                node_type=self.type_id,
                title=title or self.display_name,
                properties=merged_properties,
                node_id=node_id,
                x=pos.x(),
                y=pos.y(),
            ).to_dict(),
            "inputs": [port.name for port in self.inputs],
            "outputs": [port.name for port in self.outputs],
        }


class NodeDefinitionRegistry:
    def __init__(self):
        self._definitions = {}  # type: Dict[str, NodeDefinition]

    def clear(self):
        self._definitions.clear()

    def register(self, definition: NodeDefinition):
        self._validate(definition)
        existing = self._definitions.get(definition.type_id)
        if existing is not None:
            existing_source = existing.source_path or "<unknown>"
            new_source = definition.source_path or "<unknown>"
            raise ValueError(f"Duplicate node type '{definition.type_id}' loaded from {new_source}; already provided by {existing_source}")
        self._definitions[definition.type_id] = definition

    def unregister(self, type_id: str):
        self._definitions.pop(type_id, None)

    def get(self, type_id: str):
        return self._definitions.get(type_id)

    def require(self, type_id: str) -> NodeDefinition:
        definition = self.get(type_id)
        if definition is None:
            raise KeyError(f"Unknown node type: {type_id}")
        return definition

    def all_definitions(self):
        return sorted(self._definitions.values(), key=lambda d: (d.category.lower(), d.display_name.lower()))

    def grouped_definitions(self):
        grouped = {}
        for definition in self.all_definitions():
            grouped.setdefault(definition.category, []).append(definition)
        return grouped

    def search(self, query: str):
        needle = (query or "").strip().lower()
        if not needle:
            return self.all_definitions()
        return [
            definition for definition in self.all_definitions()
            if needle in " ".join([
                definition.type_id,
                definition.display_name,
                definition.category,
                definition.description,
                *definition.tags,
            ]).lower()
        ]

    def _validate(self, definition: NodeDefinition):
        if not definition.type_id:
            raise ValueError("Node definition is missing 'type_id'")
        if not definition.name:
            raise ValueError(f"Node definition '{definition.type_id}' is missing 'name'")
        if not definition.category:
            raise ValueError(f"Node definition '{definition.type_id}' is missing 'category'")

        seen_port_ids = set()  # type: Set[str]
        for port in definition.inputs:
            if port.direction != "input":
                raise ValueError(f"Input port '{port.id}' on '{definition.type_id}' must use direction='input'")
            if port.id in seen_port_ids:
                raise ValueError(f"Duplicate port id '{port.id}' on '{definition.type_id}'")
            seen_port_ids.add(port.id)
        for port in definition.outputs:
            if port.direction != "output":
                raise ValueError(f"Output port '{port.id}' on '{definition.type_id}' must use direction='output'")
            if port.id in seen_port_ids:
                raise ValueError(f"Duplicate port id '{port.id}' on '{definition.type_id}'")
            seen_port_ids.add(port.id)

        seen_prop_names = set()  # type: Set[str]
        for prop in definition.properties:
            if not prop.name:
                raise ValueError(f"A property on '{definition.type_id}' is missing 'name'")
            if prop.name in seen_prop_names:
                raise ValueError(f"Duplicate property name '{prop.name}' on '{definition.type_id}'")
            seen_prop_names.add(prop.name)


class NodeDefinitionLoader:
    def __init__(self, registry: NodeDefinitionRegistry):
        self.registry = registry

    def load_file(self, path: Union[str, Path]) -> NodeDefinition:
        file_path = Path(path)
        data = json.loads(file_path.read_text(encoding="utf-8"))
        definition = self._parse_definition(data, source_path=str(file_path))
        self.registry.register(definition)
        return definition

    def load_directory(self, directory: Union[str, Path], recursive: bool = True):
        base = Path(directory)
        if not base.exists():
            return []
        pattern = "**/*.json" if recursive else "*.json"
        loaded = []
        for file_path in sorted(base.glob(pattern)):
            loaded.append(self.load_file(file_path))
        return loaded

    def _parse_definition(self, data: dict, source_path: Optional[str] = None) -> NodeDefinition:
        visual_data = data.get("visual", {}) or {}
        definition = NodeDefinition(
            type_id=data["type_id"],
            name=data["name"],
            category=data["category"],
            description=data.get("description", ""),
            inputs=[self._parse_port(item) for item in data.get("inputs", [])],
            outputs=[self._parse_port(item) for item in data.get("outputs", [])],
            properties=[self._parse_property(item) for item in data.get("properties", [])],
            visual=NodeVisualDefinition(
                color=visual_data.get("color"),
                icon=visual_data.get("icon"),
                compact=bool(visual_data.get("compact", False)),
            ),
            tags=list(data.get("tags", [])),
            defaults=dict(data.get("defaults", {})),
            metadata=dict(data.get("metadata", {}) or {}),
            behavior_key=data.get("behavior_key"),
            source_path=source_path,
        )
        return definition

    def _parse_port(self, data: dict) -> NodePortDefinition:
        return NodePortDefinition(
            id=data.get("id") or self._stable_id_from_name(data["name"]),
            name=data["name"],
            direction=data["direction"],
            data_type=data.get("data_type", "any"),
            connection_kind=data.get("connection_kind"),
            multi_connection=bool(data.get("multi_connection", False)),
            required=bool(data.get("required", False)),
            default_value=data.get("default_value"),
        )

    def _parse_property(self, data: dict) -> NodePropertyDefinition:
        return NodePropertyDefinition(
            name=data["name"],
            label=data.get("label", data["name"]),
            property_type=data.get("property_type", "string"),
            default=data.get("default"),
            options=list(data.get("options", []) or []),
            multiline=bool(data.get("multiline", False)),
        )

    @staticmethod
    def _stable_id_from_name(name: str) -> str:
        return name.strip().lower().replace(" ", "_")


NODE_REGISTRY = NodeDefinitionRegistry()
NODE_DEFINITIONS_DIR = Path(__file__).resolve().parent / "node_definitions"
NODE_DEFINITION_LOADER = NodeDefinitionLoader(NODE_REGISTRY)


def load_external_node_definitions(clear_existing: bool = True):
    if clear_existing:
        NODE_REGISTRY.clear()
    NODE_DEFINITION_LOADER.load_directory(NODE_DEFINITIONS_DIR, recursive=True)
    return NODE_REGISTRY


class TestNodeData:
    def __init__(self, node_type: str, title: str, properties=None, node_id=None, x=0.0, y=0.0):
        self.node_id = node_id or str(uuid.uuid4())
        self.node_type = node_type
        self.title = title
        self.properties = properties or {}
        self.x = x
        self.y = y

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "title": self.title,
            "properties": self.properties,
            "x": self.x,
            "y": self.y,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            node_id=data.get("node_id"),
            node_type=data.get("node_type", "generic"),
            title=data.get("title", "Node"),
            properties=data.get("properties", {}),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
        )


def node_definition_for_type(node_type):
    return NODE_REGISTRY.get(node_type)


def create_node_entry(node_type, pos=None, node_id=None, title=None, properties=None, inputs=None, outputs=None):
    definition = node_definition_for_type(node_type)
    if definition is not None:
        entry = definition.create_node_entry(pos=pos, node_id=node_id, title=title, properties=properties)
        if inputs is not None:
            entry["inputs"] = list(inputs)
        if outputs is not None:
            entry["outputs"] = list(outputs)
        return entry

    pos = pos or QtCore.QPointF(0, 0)
    return {
        "node_data": TestNodeData(
            node_type=node_type,
            title=title or "Node",
            properties=dict(properties or {}),
            node_id=node_id,
            x=pos.x(),
            y=pos.y(),
        ).to_dict(),
        "inputs": list(inputs or ["In"]),
        "outputs": list(outputs or ["Out"]),
    }


load_external_node_definitions(clear_existing=True)
