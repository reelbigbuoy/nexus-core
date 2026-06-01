# ============================================================================
#
# Nexus Core
# File: tab_groups.py
# Description: Workspace tab group models and scoped data bus management.
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional
import uuid

from nexus_workspace.core.data_store import DataStore


def _group_id() -> str:
    return f"group_{uuid.uuid4().hex[:12]}"


DEFAULT_GROUP_COLORS = [
    "#4B8DFF",
    "#F59E0B",
    "#10B981",
    "#A855F7",
    "#EF4444",
    "#14B8A6",
]


@dataclass
class TabGroup:
    """Persistent workspace-level grouping for tool tabs."""

    group_id: str = field(default_factory=_group_id)
    label: str = "Group"
    color: str = "#4B8DFF"
    tool_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "group_id": self.group_id,
            "label": self.label,
            "color": self.color,
            "tool_ids": list(self.tool_ids),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, object]) -> "TabGroup":
        group_id = str(payload.get("group_id") or payload.get("id") or _group_id())
        label = str(payload.get("label") or "Group")
        color = str(payload.get("color") or "#4B8DFF")
        tool_ids = [str(tool_id) for tool_id in list(payload.get("tool_ids") or payload.get("members") or []) if tool_id]
        return cls(group_id=group_id, label=label, color=color, tool_ids=tool_ids)


@dataclass
class TabGroupContext:
    """Runtime context owned by a workspace tab group."""

    group_id: str
    label: str
    color: str
    members: List[str]
    data_bus: DataStore


class NullDataStore(DataStore):
    """No-op DataStore used when a tool is not currently assigned to a group."""

    def __init__(self):
        super().__init__(event_bus=None)

    def set(self, key: str, value, publish_event: bool = True):
        return None

    def publish(self, key: str, value, publish_event: bool = True):
        return None

    def remove(self, key: str):
        return None

    def clear(self):
        return None

    def subscribe(self, key: str, callback):
        return callback

    def unsubscribe(self, key: str, callback):
        return None

    def subscribe_all(self, callback):
        return callback

    def unsubscribe_all(self, callback):
        return None


class TabGroupManager:
    """Single authority for workspace tab group membership and group data stores."""

    def __init__(self, model, event_bus=None):
        self.model = model
        self.event_bus = event_bus
        self._stores: Dict[str, DataStore] = {}
        self._null_store = NullDataStore()

    def set_model(self, model):
        self.model = model
        self.prune_missing_tools()

    def create_group(self, label: Optional[str] = None, color: Optional[str] = None, group_id: Optional[str] = None) -> TabGroup:
        group = TabGroup(
            group_id=group_id or _group_id(),
            label=label or self._next_default_label(),
            color=color or self._next_default_color(),
        )
        self.model.tab_groups[group.group_id] = group
        self._ensure_store(group.group_id)
        return group

    def delete_group(self, group_id: str, *, clear_store: bool = True) -> bool:
        if group_id not in self.model.tab_groups:
            return False
        self.model.tab_groups.pop(group_id, None)
        if clear_store:
            store = self._stores.pop(group_id, None)
            if store is not None:
                store.clear()
        return True

    def rename_group(self, group_id: str, label: str) -> bool:
        group = self.model.tab_groups.get(group_id)
        if group is None:
            return False
        group.label = str(label or group.label)
        return True

    def change_color(self, group_id: str, color: str) -> bool:
        group = self.model.tab_groups.get(group_id)
        if group is None:
            return False
        group.color = str(color or group.color)
        return True

    def add_tool(self, group_id: str, tool_id: str) -> bool:
        group = self.model.tab_groups.get(group_id)
        if group is None or tool_id not in self.model.tools:
            return False
        self.remove_tool(tool_id)
        group.tool_ids.append(tool_id)
        self._ensure_store(group_id)
        return True

    def remove_tool(self, tool_id: str) -> Optional[str]:
        for group in self.model.tab_groups.values():
            if tool_id in group.tool_ids:
                group.tool_ids = [existing for existing in group.tool_ids if existing != tool_id]
                return group.group_id
        return None

    def move_tool(self, tool_id: str, target_group_id: str) -> bool:
        return self.add_tool(target_group_id, tool_id)

    def get_group(self, group_id: str) -> Optional[TabGroup]:
        return self.model.tab_groups.get(group_id)

    def get_group_for_tool(self, tool_id: str) -> Optional[TabGroup]:
        for group in self.model.tab_groups.values():
            if tool_id in group.tool_ids:
                return group
        return None

    def get_store(self, group_id: str) -> DataStore:
        if group_id not in self.model.tab_groups:
            return self._null_store
        return self._ensure_store(group_id)

    def get_store_for_tool(self, tool_id: str) -> DataStore:
        group = self.get_group_for_tool(tool_id)
        if group is None:
            return self._null_store
        return self._ensure_store(group.group_id)

    def get_context(self, group_id: str) -> Optional[TabGroupContext]:
        group = self.model.tab_groups.get(group_id)
        if group is None:
            return None
        return TabGroupContext(
            group_id=group.group_id,
            label=group.label,
            color=group.color,
            members=list(group.tool_ids),
            data_bus=self._ensure_store(group.group_id),
        )

    def get_context_for_tool(self, tool_id: str) -> Optional[TabGroupContext]:
        group = self.get_group_for_tool(tool_id)
        if group is None:
            return None
        return self.get_context(group.group_id)

    def serialize(self) -> List[Dict[str, object]]:
        self.prune_missing_tools()
        return [group.to_dict() for group in self.model.tab_groups.values()]

    def restore(self, payloads: Iterable[Dict[str, object]]):
        self.model.tab_groups.clear()
        for payload in payloads or []:
            try:
                group = TabGroup.from_dict(dict(payload or {}))
            except Exception:
                continue
            self.model.tab_groups[group.group_id] = group
            self._ensure_store(group.group_id)
        self.prune_missing_tools()

    def prune_missing_tools(self):
        live_tool_ids = set(getattr(self.model, "tools", {}).keys())
        for group in self.model.tab_groups.values():
            group.tool_ids = [tool_id for tool_id in group.tool_ids if tool_id in live_tool_ids]

    def _ensure_store(self, group_id: str) -> DataStore:
        if group_id not in self._stores:
            self._stores[group_id] = DataStore(event_bus=self.event_bus)
        return self._stores[group_id]

    def _next_default_color(self) -> str:
        index = len(self.model.tab_groups) % len(DEFAULT_GROUP_COLORS)
        return DEFAULT_GROUP_COLORS[index]

    def _next_default_label(self) -> str:
        return f"Group {len(self.model.tab_groups) + 1}"
