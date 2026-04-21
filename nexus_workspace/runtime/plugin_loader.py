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
# File: plugin_loader.py
# Description: Discovers plugin manifests, classifies plugin sources, and loads plugin modules.
#============================================================================

from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .app_metadata import APP_VERSION, PLUGIN_MANIFEST_SCHEMA

PLUGIN_SOURCE_ROOTS = {
    'builtin': {'channel': 'builtin', 'source': 'bundled', 'trust': 'platform', 'ownership': 'platform'},
    'owner': {'channel': 'manual', 'source': 'owner', 'trust': 'owner', 'ownership': 'personal'},
    'official': {'channel': 'official', 'source': 'official', 'trust': 'first_party', 'ownership': 'first_party'},
    'organization': {'channel': 'organization', 'source': 'private', 'trust': 'organization', 'ownership': 'organization'},
    'marketplace': {'channel': 'marketplace', 'source': 'signed', 'trust': 'verified', 'ownership': 'third_party'},
    'third_party': {'channel': 'manual', 'source': 'external', 'trust': 'unverified', 'ownership': 'third_party'},
    'legacy_external': {'channel': 'manual', 'source': 'external', 'trust': 'unverified', 'ownership': 'third_party'},
    'user': {'channel': 'manual', 'source': 'user', 'trust': 'local', 'ownership': 'unknown'},
}


@dataclass
class PluginLoadRecord:
    plugin_id: str
    display_name: str
    version: str
    plugin_type: str
    source: str
    location: str
    enabled: bool
    module: str = ''
    class_name: str = ''
    status: str = 'discovered'
    error: str = ''
    provider_name: str = ''
    provider_id: str = ''
    ownership_class: str = ''
    distribution_channel: str = ''
    distribution_source: str = ''
    trust_level: str = ''
    install_root: str = ''
    manifest: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'plugin_id': self.plugin_id,
            'display_name': self.display_name,
            'version': self.version,
            'plugin_type': self.plugin_type,
            'source': self.source,
            'location': self.location,
            'enabled': self.enabled,
            'module': self.module,
            'class_name': self.class_name,
            'status': self.status,
            'error': self.error,
            'provider_name': self.provider_name,
            'provider_id': self.provider_id,
            'ownership_class': self.ownership_class,
            'distribution_channel': self.distribution_channel,
            'distribution_source': self.distribution_source,
            'trust_level': self.trust_level,
            'install_root': self.install_root,
            'manifest': dict(self.manifest or {}),
        }


class PluginLoader:
    def __init__(self, plugin_manager, data_store=None, enabled_overrides=None, app_version: str = APP_VERSION):
        self.plugin_manager = plugin_manager
        self.data_store = data_store
        self.enabled_overrides = dict(enabled_overrides or {})
        self.app_version = app_version
        self.records: List[PluginLoadRecord] = []
        self.errors: List[str] = []

    def discover_and_load(self, search_paths: Optional[List[Path]] = None):
        self.records = []
        self.errors = []
        for manifest_path in self._discover_manifest_paths(search_paths=search_paths):
            record = self._load_manifest_path(manifest_path)
            if record is not None:
                self.records.append(record)
        self._publish_state()
        return self.records

    def default_search_paths(self) -> List[Path]:
        base_dir = Path(__file__).resolve().parents[2]
        search_paths = [
            base_dir / 'plugins',
            base_dir / 'plugins_external',
            Path.home() / '.nexus' / 'plugins',
        ]
        extra = os.environ.get('NEXUS_PLUGIN_PATH', '').strip()
        if extra:
            for part in extra.split(os.pathsep):
                candidate = Path(part).expanduser()
                if str(candidate):
                    search_paths.append(candidate)
        deduped = []
        seen = set()
        for path in search_paths:
            key = str(path.resolve()) if path.exists() else str(path)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(path)
        return deduped

    def _discover_manifest_paths(self, search_paths: Optional[List[Path]] = None) -> List[Path]:
        manifests: List[Path] = []
        for root in search_paths or self.default_search_paths():
            if not root.exists() or not root.is_dir():
                continue
            manifests.extend(self._discover_manifest_paths_under_root(root))
        return manifests

    def _discover_manifest_paths_under_root(self, root: Path) -> List[Path]:
        manifests: List[Path] = []
        if root.name == 'plugins':
            for source_dir in sorted(root.iterdir()):
                if not source_dir.is_dir():
                    continue
                for child in sorted(source_dir.iterdir()):
                    manifest_path = child / 'plugin.json'
                    if child.is_dir() and manifest_path.exists():
                        manifests.append(manifest_path)
            return manifests
        for child in sorted(root.iterdir()):
            manifest_path = child / 'plugin.json'
            if child.is_dir() and manifest_path.exists():
                manifests.append(manifest_path)
        return manifests

    def _is_enabled(self, plugin_id: str, manifest: Dict[str, object]) -> bool:
        if plugin_id in self.enabled_overrides:
            return bool(self.enabled_overrides.get(plugin_id))
        return bool(manifest.get('enabled', True))

    def _load_manifest_path(self, manifest_path: Path) -> Optional[PluginLoadRecord]:
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except Exception as exc:
            self.errors.append(f'Failed to read {manifest_path}: {exc}')
            return None

        plugin_id = str(manifest.get('plugin_id') or '').strip()
        display_name = str(manifest.get('display_name') or plugin_id or manifest_path.parent.name)
        source_category = self._source_name_for_path(manifest_path.parent)
        merged_manifest = self._normalized_manifest(manifest, manifest_path.parent)
        provider = merged_manifest.get('provider') or {}
        distribution = merged_manifest.get('distribution') or {}
        ownership = merged_manifest.get('ownership') or {}
        record = PluginLoadRecord(
            plugin_id=plugin_id or manifest_path.parent.name,
            display_name=display_name,
            version=str(merged_manifest.get('version') or '1.0.0'),
            plugin_type=str(merged_manifest.get('type') or 'tool'),
            source=source_category,
            location=str(manifest_path.parent),
            enabled=False,
            module=str(merged_manifest.get('module') or ''),
            class_name=str(merged_manifest.get('class') or ''),
            provider_name=str(provider.get('name') or ''),
            provider_id=str(provider.get('id') or ''),
            ownership_class=str(ownership.get('class') or ''),
            distribution_channel=str(distribution.get('channel') or ''),
            distribution_source=str(distribution.get('source') or ''),
            trust_level=str(distribution.get('trust') or ''),
            install_root=self._install_root_name(manifest_path.parent),
            manifest=merged_manifest,
        )
        try:
            self._validate_manifest(merged_manifest, manifest_path)
            record.enabled = self._is_enabled(record.plugin_id, merged_manifest)
            if not record.enabled:
                record.status = 'disabled'
                return record
            if not self._is_compatible(merged_manifest):
                record.status = 'incompatible'
                record.error = 'Plugin is not compatible with this Nexus version.'
                return record
            plugin = self._instantiate_plugin(merged_manifest, manifest_path.parent)
            self.plugin_manager.register_plugin(plugin, external_manifest=merged_manifest, source_path=str(manifest_path.parent), source_kind=record.source)
            record.status = 'loaded'
            return record
        except Exception as exc:
            record.status = 'error'
            record.error = str(exc)
            self.errors.append(f'{record.plugin_id}: {exc}')
            return record

    def _normalized_manifest(self, manifest: Dict[str, object], plugin_root: Path) -> Dict[str, object]:
        normalized = dict(manifest or {})
        source_category = self._source_name_for_path(plugin_root)
        defaults = PLUGIN_SOURCE_ROOTS.get(source_category, {})
        provider = dict(normalized.get('provider') or {})
        if not provider.get('name'):
            provider['name'] = str(normalized.get('author') or normalized.get('display_name') or normalized.get('plugin_id') or plugin_root.name)
        if not provider.get('id'):
            provider['id'] = str(normalized.get('plugin_id') or plugin_root.name)
        normalized['provider'] = provider
        distribution = dict(normalized.get('distribution') or {})
        distribution.setdefault('channel', defaults.get('channel', 'manual'))
        distribution.setdefault('source', defaults.get('source', source_category))
        distribution.setdefault('trust', defaults.get('trust', 'unknown'))
        normalized['distribution'] = distribution
        ownership = dict(normalized.get('ownership') or {})
        ownership.setdefault('class', defaults.get('ownership', 'unknown'))
        normalized['ownership'] = ownership
        normalized.setdefault('source', source_category)
        normalized.setdefault('display_category', source_category.replace('_', ' ').title())
        normalized.setdefault('install_root', self._install_root_name(plugin_root))
        return normalized

    def _validate_manifest(self, manifest: Dict[str, object], manifest_path: Path):
        schema = str(manifest.get('schema') or '').strip()
        if schema != PLUGIN_MANIFEST_SCHEMA:
            raise ValueError(f'Unsupported plugin schema in {manifest_path.name}: {schema or "<missing>"}')
        for key in ('plugin_id', 'module', 'class'):
            if not str(manifest.get(key) or '').strip():
                raise ValueError(f'Manifest {manifest_path} is missing required field: {key}')
        for key in ('provider', 'distribution', 'ownership'):
            value = manifest.get(key)
            if not isinstance(value, dict):
                raise ValueError(f'Manifest {manifest_path} must define object field: {key}')

    def _is_compatible(self, manifest: Dict[str, object]) -> bool:
        min_version = str(manifest.get('min_nexus_version') or '').strip()
        max_version = str(manifest.get('max_nexus_version') or '').strip()
        current = self._version_tuple(self.app_version)
        if min_version and current < self._version_tuple(min_version):
            return False
        if max_version and current > self._version_tuple(max_version):
            return False
        return True

    def _instantiate_plugin(self, manifest: Dict[str, object], plugin_root: Path):
        import_root = str(manifest.get('import_root') or '.').strip()
        module_name = str(manifest.get('module') or '').strip()
        class_name = str(manifest.get('class') or '').strip()
        search_root = (plugin_root / import_root).resolve() if import_root != '.' else plugin_root.resolve()
        if str(search_root) not in sys.path:
            sys.path.insert(0, str(search_root))
        module = importlib.import_module(module_name)
        plugin_class = getattr(module, class_name, None)
        if plugin_class is None:
            raise ValueError(f'Plugin class not found: {module_name}.{class_name}')
        return plugin_class()

    def _source_name_for_path(self, plugin_root: Path) -> str:
        parent = plugin_root.parent
        if parent.name in PLUGIN_SOURCE_ROOTS:
            return parent.name
        if parent.name == 'plugins_external':
            return 'legacy_external'
        if parent == (Path.home() / '.nexus' / 'plugins'):
            return 'user'
        if parent.parent.name == 'plugins' and parent.name in PLUGIN_SOURCE_ROOTS:
            return parent.name
        return 'third_party'

    def _install_root_name(self, plugin_root: Path) -> str:
        parent = plugin_root.parent
        if parent.parent.name == 'plugins':
            return str(parent.name)
        if parent.name == 'plugins':
            return 'plugins'
        if parent.name == 'plugins_external':
            return 'plugins_external'
        if parent == (Path.home() / '.nexus' / 'plugins'):
            return 'user'
        return parent.name

    def _version_tuple(self, version: str):
        parts = []
        for piece in str(version).split('.'):
            try:
                parts.append(int(piece))
            except ValueError:
                digits = ''.join(ch for ch in piece if ch.isdigit())
                parts.append(int(digits) if digits else 0)
        return tuple(parts)

    def snapshot(self):
        return {
            'contract': 'platform.plugin_loader.v1',
            'records': [record.to_dict() for record in self.records],
            'errors': list(self.errors),
            'enabled_overrides': dict(self.enabled_overrides or {}),
            'search_paths': [str(path) for path in self.default_search_paths()],
            'source_roots': dict(PLUGIN_SOURCE_ROOTS),
        }

    def _publish_state(self):
        if self.data_store is None:
            return
        try:
            self.data_store.set('platform.plugin_loader', self.snapshot())
        except Exception:
            pass