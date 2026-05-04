# ============================================================================
#
# Copyright (c) 2026 Reel Big Buoy Company
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Nexus Core
# File: templates.py
# Description: Shared graph template persistence and materialization helpers.
#
# ============================================================================

import copy
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from nexus_workspace.framework.qt import QtCore

from .graph_integrity import GraphIdRewriter, graph_json_safe


_TEMPLATE_SCHEMA_VERSION = 2
TEMPLATE_FILE_EXTENSION = ".nxtemplate"


def _safe_slug(value: str) -> str:
    text = str(value or "template").strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-._")
    return text or "template"


@dataclass(frozen=True)
class GraphTemplateSummary:
    template_id: str
    name: str
    description: str = ""
    category: str = "Templates"
    source: str = "user"
    path: str = ""
    tool_type_id: str = ""
    plugin_id: str = ""
    view_ids: tuple = ()
    node_types: tuple = ()


class GraphTemplateService:
    """Domain-neutral local template store for reusable graph snippets.

    Templates are saved as JSON graph snapshots with positions normalized to a
    local origin.  Insert/materialize regenerates all graph-local UUIDs and
    offsets nodes/route points to the requested cursor position.
    """

    def __init__(self, tool_type_id: str = "graph", plugin_id: str = "graph", parent=None):
        self.tool_type_id = _safe_slug(tool_type_id or "graph")
        self.plugin_id = _safe_slug(plugin_id or self.tool_type_id)
        self.parent = parent
        self._config_path = self._default_config_path()
        self._user_dir = self._default_user_template_dir()
        self._save_dir = self._user_dir
        self._load_dirs: List[Path] = []
        self._package_dirs: List[Path] = []
        self._load_library_config()

    def _default_config_path(self) -> Path:
        base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.AppDataLocation)
        if not base:
            base = os.path.join(os.path.expanduser("~"), ".nexus-core")
        path = Path(base) / "graph_templates"
        path.mkdir(parents=True, exist_ok=True)
        return path / f"{self.plugin_id}_template_libraries.json"

    def _default_user_template_dir(self) -> Path:
        base = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.AppDataLocation)
        if not base:
            base = os.path.join(os.path.expanduser("~"), ".nexus-core")
        path = Path(base) / "graph_templates" / self.plugin_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def user_template_dir(self) -> Path:
        return self.save_repository

    @property
    def save_repository(self) -> Path:
        self._save_dir.mkdir(parents=True, exist_ok=True)
        return self._save_dir

    def load_repositories(self) -> List[Path]:
        paths = []
        seen = set()
        for path in list(self._load_dirs) + [self.save_repository]:
            try:
                resolved = Path(path).expanduser().resolve()
            except Exception:
                resolved = Path(path)
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            if resolved.exists() and resolved.is_dir():
                paths.append(resolved)
        return paths

    def _load_library_config(self):
        try:
            if not self._config_path.exists():
                self._load_dirs = [self._user_dir]
                return
            with open(self._config_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            save_path = payload.get("save_repository")
            if save_path:
                self._save_dir = Path(save_path).expanduser()
            load_paths = payload.get("load_repositories") or []
            self._load_dirs = [Path(p).expanduser() for p in load_paths if p]
            if not self._load_dirs:
                self._load_dirs = [self._save_dir]
        except Exception:
            self._save_dir = self._user_dir
            self._load_dirs = [self._user_dir]

    def _save_library_config(self):
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "nexus.graph.template.libraries",
            "schema_version": 1,
            "extension": TEMPLATE_FILE_EXTENSION,
            "save_repository": str(self.save_repository),
            "load_repositories": [str(path) for path in self.load_repositories()],
        }
        with open(self._config_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def set_save_repository(self, path):
        candidate = Path(path).expanduser()
        candidate.mkdir(parents=True, exist_ok=True)
        self._save_dir = candidate
        if candidate not in self._load_dirs:
            self._load_dirs.append(candidate)
        self._save_library_config()

    def set_load_repositories(self, paths):
        self._load_dirs = []
        for path in paths or []:
            if not path:
                continue
            candidate = Path(path).expanduser()
            if candidate.exists() and candidate.is_dir() and candidate not in self._load_dirs:
                self._load_dirs.append(candidate)
        if self.save_repository not in self._load_dirs:
            self._load_dirs.append(self.save_repository)
        self._save_library_config()

    def add_package_template_dir(self, path):
        if not path:
            return
        candidate = Path(path)
        if candidate.exists() and candidate.is_dir() and candidate not in self._package_dirs:
            self._package_dirs.append(candidate)

    def list_templates(self, compatible_only: bool = True) -> List[GraphTemplateSummary]:
        summaries: Dict[str, GraphTemplateSummary] = {}
        sources = [("package", p) for p in self._package_dirs] + [("library", p) for p in self.load_repositories()]
        for source, directory in sources:
            for pattern in (f"*{TEMPLATE_FILE_EXTENSION}", "*.json"):
                for file_path in sorted(directory.glob(pattern)):
                    try:
                        payload = self._read_template_file(file_path)
                        if compatible_only and not self.is_template_compatible(payload):
                            continue
                        template_id = str(payload.get("id") or file_path.stem)
                        node_types = tuple(sorted(set(str(t) for t in (payload.get("node_types") or self._node_types_from_snapshot(payload.get("snapshot") or {})) if t)))
                        view_ids = tuple(str(v) for v in (payload.get("compatible_view_ids") or []) if v)
                        summaries[template_id] = GraphTemplateSummary(
                            template_id=template_id,
                            name=str(payload.get("name") or file_path.stem),
                            description=str(payload.get("description") or ""),
                            category=str(payload.get("category") or "Templates"),
                            source=source,
                            path=str(file_path),
                            tool_type_id=str(payload.get("tool_type_id") or ""),
                            plugin_id=str(payload.get("plugin_id") or ""),
                            view_ids=view_ids,
                            node_types=node_types,
                        )
                    except Exception:
                        continue
        return sorted(summaries.values(), key=lambda item: (item.category.lower(), item.name.lower()))

    def _node_types_from_snapshot(self, snapshot: dict) -> List[str]:
        node_types = []
        for node_entry in (snapshot or {}).get("nodes", []) or []:
            node_data = node_entry.get("node_data", {}) if isinstance(node_entry, dict) else {}
            node_type = node_data.get("node_type")
            if node_type:
                node_types.append(str(node_type))
        return node_types

    def is_template_compatible(self, payload: dict) -> bool:
        if not isinstance(payload, dict):
            return False
        node_types = payload.get("node_types") or self._node_types_from_snapshot(payload.get("snapshot") or {})
        parent = self.parent
        if parent is not None:
            active_view_id = getattr(parent, "active_node_view_id", lambda: None)()
            compatible_views = set(str(v) for v in (payload.get("compatible_view_ids") or []) if v)
            if compatible_views and active_view_id and str(active_view_id) not in compatible_views:
                return False
            checker = getattr(parent, "_node_type_allowed_in_registry", None)
            if callable(checker):
                return all(checker(node_type) for node_type in node_types)
        return True

    def _read_template_file(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("Template file is not a JSON object")
        if not isinstance(payload.get("snapshot"), dict):
            raise ValueError("Template file is missing snapshot")
        return payload

    def _path_for_template(self, name: str, template_id: Optional[str] = None) -> Path:
        slug = _safe_slug(name)
        if template_id:
            slug = _safe_slug(template_id)
        return self.save_repository / f"{slug}{TEMPLATE_FILE_EXTENSION}"

    def save_template(self, name: str, snapshot: dict, description: str = "", category: str = "Templates") -> GraphTemplateSummary:
        name = str(name or "").strip()
        if not name:
            raise ValueError("Template name is required")
        normalized_snapshot, origin = self.normalize_snapshot(snapshot)
        if not normalized_snapshot.get("nodes"):
            raise ValueError("A template must contain at least one node")
        template_id = str(uuid.uuid4())
        file_path = self._path_for_template(name)
        if file_path.exists():
            file_path = self._path_for_template(name, f"{_safe_slug(name)}-{template_id[:8]}")
        node_types = sorted(set(self._node_types_from_snapshot(normalized_snapshot)))
        active_view_id = None
        if self.parent is not None and hasattr(self.parent, "active_node_view_id"):
            try:
                active_view_id = self.parent.active_node_view_id()
            except Exception:
                active_view_id = None
        payload = {
            "schema": "nexus.graph.template",
            "schema_version": _TEMPLATE_SCHEMA_VERSION,
            "extension": TEMPLATE_FILE_EXTENSION,
            "id": template_id,
            "name": name,
            "description": str(description or ""),
            "category": str(category or "Templates"),
            "tool_type_id": self.tool_type_id,
            "plugin_id": self.plugin_id,
            "compatible_view_ids": [str(active_view_id)] if active_view_id else [],
            "node_types": node_types,
            "origin": [float(origin[0]), float(origin[1])],
            "snapshot": graph_json_safe(normalized_snapshot),
        }
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        return GraphTemplateSummary(template_id=template_id, name=name, description=description or "", category=category or "Templates", source="user", path=str(file_path))

    def load_template(self, template_id: str) -> dict:
        template_id = str(template_id or "").strip()
        for summary in self.list_templates(compatible_only=False):
            if summary.template_id == template_id:
                return self._read_template_file(Path(summary.path))
        raise KeyError(f"Template not found: {template_id}")

    def materialize_template(self, template_id: str, scene_pos: QtCore.QPointF) -> dict:
        payload = self.load_template(template_id)
        if not self.is_template_compatible(payload):
            raise ValueError("Template is not compatible with the active graph view")
        snapshot = copy.deepcopy(payload.get("snapshot") or {})
        target_x = float(scene_pos.x()) if hasattr(scene_pos, "x") else 0.0
        target_y = float(scene_pos.y()) if hasattr(scene_pos, "y") else 0.0
        return GraphIdRewriter.rewrite_snapshot(snapshot, dx=target_x, dy=target_y)

    @staticmethod
    def normalize_snapshot(snapshot: dict) -> Tuple[dict, Tuple[float, float]]:
        snapshot = graph_json_safe(copy.deepcopy(snapshot or {}))
        nodes = snapshot.get("nodes") or []
        if not nodes:
            return {"nodes": [], "connections": []}, (0.0, 0.0)
        xs = []
        ys = []
        for node_entry in nodes:
            node_data = node_entry.get("node_data", {}) if isinstance(node_entry, dict) else {}
            try:
                xs.append(float(node_data.get("x", 0.0)))
                ys.append(float(node_data.get("y", 0.0)))
            except Exception:
                continue
        origin_x = min(xs) if xs else 0.0
        origin_y = min(ys) if ys else 0.0
        for node_entry in nodes:
            node_data = node_entry.get("node_data", {}) if isinstance(node_entry, dict) else {}
            try:
                node_data["x"] = float(node_data.get("x", 0.0)) - origin_x
                node_data["y"] = float(node_data.get("y", 0.0)) - origin_y
            except Exception:
                pass
        for conn_entry in snapshot.get("connections") or []:
            if not isinstance(conn_entry, dict):
                continue
            points = []
            for point in conn_entry.get("route_points") or []:
                try:
                    if isinstance(point, (list, tuple)) and len(point) >= 2:
                        points.append([float(point[0]) - origin_x, float(point[1]) - origin_y])
                    elif hasattr(point, "x") and hasattr(point, "y"):
                        points.append([float(point.x()) - origin_x, float(point.y()) - origin_y])
                except Exception:
                    continue
            conn_entry["route_points"] = points
        return snapshot, (origin_x, origin_y)
