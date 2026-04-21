# ============================================================================
# Nexus
# File: plugins/owner/NoDE/node_plugin/node_views.py
# Description: Source module for node plugin functionality.
# Part of: NoDE Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Union

from .definitions import NodeDefinition, NodeDefinitionRegistry


@dataclass
class NodeConnectionCategoryRule:
    source_category: str = "*"
    target_category: str = "*"


@dataclass
class NodeConnectionDataTypeRule:
    source_data_type: str = "*"
    target_data_type: str = "*"




@dataclass
class NodeConnectionKindRule:
    source_connection_kind: str = "*"
    target_connection_kind: str = "*"


@dataclass
class NodeConnectionStyle:
    color_role: Optional[str] = None
    width: Optional[float] = None
    pen_style: str = "solid"

@dataclass
class NodeViewRules:
    allow_cycles: bool = True
    allow_self_connections: bool = False
    max_nodes: Optional[int] = None
    max_nodes_per_type: Dict[str, int] = field(default_factory=dict)
    required_categories: List[str] = field(default_factory=list)
    required_type_ids: List[str] = field(default_factory=list)
    enforce_data_type_compatibility: bool = False
    allowed_connection_category_rules: List[NodeConnectionCategoryRule] = field(default_factory=list)
    blocked_connection_category_rules: List[NodeConnectionCategoryRule] = field(default_factory=list)
    allowed_connection_data_type_rules: List[NodeConnectionDataTypeRule] = field(default_factory=list)
    blocked_connection_data_type_rules: List[NodeConnectionDataTypeRule] = field(default_factory=list)
    allowed_connection_kind_rules: List[NodeConnectionKindRule] = field(default_factory=list)
    blocked_connection_kind_rules: List[NodeConnectionKindRule] = field(default_factory=list)
    cycle_checked_connection_kinds: List[str] = field(default_factory=lambda: ["exec", "requirement"])


@dataclass
class NodeViewDefinition:
    view_id: str
    name: str
    description: str = ""
    include_categories: List[str] = field(default_factory=list)
    exclude_categories: List[str] = field(default_factory=list)
    include_type_ids: List[str] = field(default_factory=list)
    exclude_type_ids: List[str] = field(default_factory=list)
    include_source_subdirs: List[str] = field(default_factory=list)
    is_default: bool = False
    rules: NodeViewRules = field(default_factory=NodeViewRules)
    connection_styles: Dict[str, NodeConnectionStyle] = field(default_factory=dict)
    source_path: Optional[str] = None


class NodeViewRegistry:
    def __init__(self):
        self._views = {}  # type: Dict[str, NodeViewDefinition]

    def clear(self):
        self._views.clear()

    def register(self, view_definition: NodeViewDefinition):
        if not view_definition.view_id:
            raise ValueError("Node view is missing 'view_id'")
        if not view_definition.name:
            raise ValueError("Node view '%s' is missing 'name'" % view_definition.view_id)
        existing = self._views.get(view_definition.view_id)
        if existing is not None:
            raise ValueError(
                "Duplicate node view '%s' loaded from %s; already provided by %s" % (
                    view_definition.view_id,
                    view_definition.source_path or "<unknown>",
                    existing.source_path or "<unknown>",
                )
            )
        self._views[view_definition.view_id] = view_definition

    def get(self, view_id: Optional[str]) -> Optional[NodeViewDefinition]:
        if not view_id:
            return None
        return self._views.get(view_id)

    def require(self, view_id: str) -> NodeViewDefinition:
        view_definition = self.get(view_id)
        if view_definition is None:
            raise KeyError("Unknown node view: %s" % view_id)
        return view_definition

    def all_views(self) -> List[NodeViewDefinition]:
        return sorted(self._views.values(), key=lambda view: (0 if view.is_default else 1, view.name.lower(), view.view_id.lower()))

    def default_view(self) -> Optional[NodeViewDefinition]:
        for view in self.all_views():
            if view.is_default:
                return view
        views = self.all_views()
        return views[0] if views else None


class NodeViewLoader:
    def __init__(self, registry: NodeViewRegistry):
        self.registry = registry

    def load_directory(self, directory: Union[str, Path], recursive: bool = True) -> List[NodeViewDefinition]:
        base = Path(directory)
        if not base.exists():
            return []
        pattern = "**/*.json" if recursive else "*.json"
        loaded = []
        for file_path in sorted(base.glob(pattern)):
            loaded.append(self.load_file(file_path))
        return loaded

    def load_file(self, path: Union[str, Path]) -> NodeViewDefinition:
        file_path = Path(path)
        data = json.loads(file_path.read_text(encoding="utf-8"))
        rules_data = data.get("rules", {}) or {}
        connection_styles_data = data.get("connection_styles", {}) or {}
        definition = NodeViewDefinition(
            view_id=data["view_id"],
            name=data["name"],
            description=data.get("description", ""),
            include_categories=list(data.get("include_categories", []) or []),
            exclude_categories=list(data.get("exclude_categories", []) or []),
            include_type_ids=list(data.get("include_type_ids", []) or []),
            exclude_type_ids=list(data.get("exclude_type_ids", []) or []),
            include_source_subdirs=list(data.get("include_source_subdirs", []) or []),
            is_default=bool(data.get("is_default", False)),
            rules=NodeViewRules(
                allow_cycles=bool(rules_data.get("allow_cycles", True)),
                allow_self_connections=bool(rules_data.get("allow_self_connections", False)),
                max_nodes=rules_data.get("max_nodes"),
                max_nodes_per_type=dict(rules_data.get("max_nodes_per_type", {}) or {}),
                required_categories=list(rules_data.get("required_categories", []) or []),
                required_type_ids=list(rules_data.get("required_type_ids", []) or []),
                enforce_data_type_compatibility=bool(rules_data.get("enforce_data_type_compatibility", False)),
                allowed_connection_category_rules=[self._parse_category_rule(item) for item in list(rules_data.get("allowed_connection_category_rules", []) or [])],
                blocked_connection_category_rules=[self._parse_category_rule(item) for item in list(rules_data.get("blocked_connection_category_rules", []) or [])],
                allowed_connection_data_type_rules=[self._parse_data_type_rule(item) for item in list(rules_data.get("allowed_connection_data_type_rules", []) or [])],
                blocked_connection_data_type_rules=[self._parse_data_type_rule(item) for item in list(rules_data.get("blocked_connection_data_type_rules", []) or [])],
                allowed_connection_kind_rules=[self._parse_connection_kind_rule(item) for item in list(rules_data.get("allowed_connection_kind_rules", []) or [])],
                blocked_connection_kind_rules=[self._parse_connection_kind_rule(item) for item in list(rules_data.get("blocked_connection_kind_rules", []) or [])],
                cycle_checked_connection_kinds=[str(item).strip().lower() for item in list(rules_data.get("cycle_checked_connection_kinds", ["exec", "requirement"]) or ["exec", "requirement"]) if str(item).strip()],
            ),
            connection_styles={str(kind).strip().lower(): self._parse_connection_style(style) for kind, style in dict(connection_styles_data).items() if str(kind).strip()},
            source_path=str(file_path),
        )
        self.registry.register(definition)
        return definition

    @staticmethod
    def _parse_category_rule(data):
        data = data or {}
        return NodeConnectionCategoryRule(
            source_category=str(data.get("source_category", "*") or "*"),
            target_category=str(data.get("target_category", "*") or "*"),
        )

    @staticmethod
    def _parse_data_type_rule(data):
        data = data or {}
        return NodeConnectionDataTypeRule(
            source_data_type=str(data.get("source_data_type", "*") or "*"),
            target_data_type=str(data.get("target_data_type", "*") or "*"),
        )

    @staticmethod
    def _parse_connection_kind_rule(data):
        data = data or {}
        return NodeConnectionKindRule(
            source_connection_kind=str(data.get("source_connection_kind", "*") or "*"),
            target_connection_kind=str(data.get("target_connection_kind", "*") or "*"),
        )

    @staticmethod
    def _parse_connection_style(data):
        data = data or {}
        width = data.get("width")
        try:
            width = float(width) if width is not None else None
        except (TypeError, ValueError):
            width = None
        return NodeConnectionStyle(
            color_role=(str(data.get("color_role")).strip() if data.get("color_role") is not None else None),
            width=width,
            pen_style=str(data.get("pen_style", "solid") or "solid").strip().lower(),
        )


class FilteredNodeDefinitionRegistry(NodeDefinitionRegistry):
    def __init__(self, base_registry: NodeDefinitionRegistry, definitions: Sequence[NodeDefinition], view_definition: Optional[NodeViewDefinition] = None):
        super().__init__()
        self._base_registry = base_registry
        self._view_definition = view_definition
        for definition in definitions:
            self._definitions[definition.type_id] = definition

    @property
    def base_registry(self) -> NodeDefinitionRegistry:
        return self._base_registry

    @property
    def view_definition(self) -> Optional[NodeViewDefinition]:
        return self._view_definition


class NodeViewSession:
    def __init__(self, base_registry: NodeDefinitionRegistry, view_registry: NodeViewRegistry, select_default_on_reset: bool = False):
        self._base_registry = base_registry
        self._view_registry = view_registry
        self._select_default_on_reset = bool(select_default_on_reset)
        self._active_view_id = None  # type: Optional[str]
        self._active_registry = FilteredNodeDefinitionRegistry(base_registry, [], view_definition=None)
        if self._select_default_on_reset:
            self.set_active_view_id(None)
        else:
            self._set_active_view_definition(None)

    def available_views(self) -> List[NodeViewDefinition]:
        return self._view_registry.all_views()

    def active_view_id(self) -> Optional[str]:
        return self._active_view_id

    def active_view(self) -> Optional[NodeViewDefinition]:
        return self._view_registry.get(self._active_view_id) if self._active_view_id else None

    def active_registry(self) -> NodeDefinitionRegistry:
        return self._active_registry

    def _set_active_view_definition(self, view_definition: Optional[NodeViewDefinition]) -> Optional[NodeViewDefinition]:
        self._active_view_id = view_definition.view_id if view_definition is not None else None
        filtered = _filter_definitions(self._base_registry.all_definitions(), view_definition)
        self._active_registry = FilteredNodeDefinitionRegistry(self._base_registry, filtered, view_definition=view_definition)
        return view_definition

    def set_active_view_id(self, view_id: Optional[str]) -> Optional[NodeViewDefinition]:
        if not view_id and self._select_default_on_reset:
            default_view = self._view_registry.default_view()
            view_id = default_view.view_id if default_view is not None else None
        view_definition = self._view_registry.get(view_id) if view_id else None
        return self._set_active_view_definition(view_definition)


def _filter_definitions(definitions: Iterable[NodeDefinition], view_definition: Optional[NodeViewDefinition]) -> List[NodeDefinition]:
    if view_definition is None:
        return list(definitions)

    include_categories = set(view_definition.include_categories)
    exclude_categories = set(view_definition.exclude_categories)
    include_type_ids = set(view_definition.include_type_ids)
    exclude_type_ids = set(view_definition.exclude_type_ids)
    include_source_subdirs = [segment.replace('\\', '/').strip('/').lower() for segment in view_definition.include_source_subdirs if segment]

    filtered = []
    for definition in definitions:
        if exclude_type_ids and definition.type_id in exclude_type_ids:
            continue
        if exclude_categories and definition.category in exclude_categories:
            continue
        if include_type_ids and definition.type_id not in include_type_ids:
            continue
        if include_categories and definition.category not in include_categories:
            continue
        if include_source_subdirs:
            source_path = (definition.source_path or '').replace('\\', '/').lower()
            if not any('/%s/' % segment in source_path or source_path.endswith('/%s' % segment) for segment in include_source_subdirs):
                continue
        filtered.append(definition)
    return filtered


from .definitions import NODE_REGISTRY

NODE_VIEW_REGISTRY = NodeViewRegistry()
NODE_VIEW_MANIFESTS_DIR = Path(__file__).resolve().parent / "node_view_manifests"
NODE_VIEW_LOADER = NodeViewLoader(NODE_VIEW_REGISTRY)
def load_node_views(clear_existing=True):
    if clear_existing:
        NODE_VIEW_REGISTRY.clear()
    NODE_VIEW_LOADER.load_directory(NODE_VIEW_MANIFESTS_DIR, recursive=True)
    return NODE_VIEW_REGISTRY


load_node_views(clear_existing=True)
