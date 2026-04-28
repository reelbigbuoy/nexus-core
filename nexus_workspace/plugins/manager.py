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
# File: manager.py
# Description: Manages plugin discovery, registration, loading, and runtime access.
#============================================================================

from typing import Dict, List
from .base import ToolDescriptor


class PluginManager:
    def __init__(self, context=None):
        self._plugins = []
        self._plugins_by_id = {}
        self._tool_descriptors: Dict[str, ToolDescriptor] = {}
        self._plugin_manifests: Dict[str, dict] = {}
        self._plugin_records: Dict[str, dict] = {}
        self._enabled_overrides: Dict[str, bool] = {}
        self.context = context

    def set_context(self, context):
        self.context = context

    def set_enabled_overrides(self, overrides=None):
        self._enabled_overrides = dict(overrides or {})

    def plugin_enabled(self, plugin_id: str) -> bool:
        if plugin_id in self._enabled_overrides:
            return bool(self._enabled_overrides.get(plugin_id))
        record = self._plugin_records.get(plugin_id) or {}
        return bool(record.get('enabled', True))

    def register_plugin(self, plugin, *, external_manifest=None, source_path='', source_kind='builtin'):
        self._plugins.append(plugin)
        plugin_id = getattr(plugin, 'plugin_id', '')
        if plugin_id:
            self._plugins_by_id[plugin_id] = plugin
        plugin.register(self.context or self)
        manifest = external_manifest
        if manifest is None and hasattr(plugin, 'manifest'):
            try:
                manifest = plugin.manifest()
            except Exception:
                manifest = None
        if manifest is not None and plugin_id:
            manifest_dict = manifest.to_dict() if hasattr(manifest, 'to_dict') else dict(manifest)
            tools = []
            for descriptor in self.tool_descriptors_for_plugin(plugin_id):
                tools.append({
                    'tool_type_id': descriptor.tool_type_id,
                    'display_name': descriptor.display_name,
                    'description': descriptor.description,
                    'widget_type': descriptor.widget_type,
                    'metadata': dict(descriptor.metadata or {}),
                })
            if tools:
                manifest_dict['tools'] = tools
            manifest_dict.setdefault('persists', [])
            provider = dict(manifest_dict.get('provider') or {})
            distribution = dict(manifest_dict.get('distribution') or {})
            ownership = dict(manifest_dict.get('ownership') or {})
            self._plugin_manifests[plugin_id] = manifest_dict
            self._plugin_records[plugin_id] = {
                'plugin_id': plugin_id,
                'display_name': manifest_dict.get('display_name') or getattr(plugin, 'display_name', plugin_id),
                'version': manifest_dict.get('version') or getattr(plugin, 'version', '1.0.0'),
                'plugin_type': manifest_dict.get('type', 'tool'),
                'source': source_kind,
                'location': source_path,
                'enabled': True,
                'status': 'loaded',
                'provider_name': provider.get('name', ''),
                'provider_id': provider.get('id', ''),
                'distribution_channel': distribution.get('channel', ''),
                'distribution_source': distribution.get('source', ''),
                'trust_level': distribution.get('trust', ''),
                'ownership_class': ownership.get('class', ''),
                'install_root': manifest_dict.get('install_root', ''),
                'display_category': manifest_dict.get('display_category', ''),
                'manifest': manifest_dict,
            }
            self._publish_registry_snapshot()

    def unregister_plugin(self, plugin_id: str):
        """Remove a plugin and its tool descriptors from the live registry."""
        plugin_id = str(plugin_id or '').strip()
        if not plugin_id:
            return
        self._plugins = [plugin for plugin in self._plugins if getattr(plugin, 'plugin_id', '') != plugin_id]
        self._plugins_by_id.pop(plugin_id, None)
        for tool_type_id, descriptor in list(self._tool_descriptors.items()):
            if getattr(descriptor, 'plugin_id', '') == plugin_id or tool_type_id == plugin_id:
                self._tool_descriptors.pop(tool_type_id, None)
        self._plugin_manifests.pop(plugin_id, None)
        self._plugin_records.pop(plugin_id, None)
        self._publish_registry_snapshot()

    def register_tool(self, descriptor: ToolDescriptor):
        if descriptor.plugin_id == '':
            descriptor.plugin_id = getattr(self._plugins[-1], 'plugin_id', '') if self._plugins else ''
        if descriptor.metadata is None:
            descriptor.metadata = {}
        self._tool_descriptors[descriptor.tool_type_id] = descriptor
        self._publish_registry_snapshot()

    def tool_descriptors(self) -> List[ToolDescriptor]:
        return list(self._tool_descriptors.values())

    def launchable_tool_descriptors(self) -> List[ToolDescriptor]:
        return [d for d in self._tool_descriptors.values() if (d.widget_type or 'tool') == 'tool' and self.plugin_enabled(d.plugin_id)]

    def view_tool_descriptors(self) -> List[ToolDescriptor]:
        return [d for d in self._tool_descriptors.values() if (d.widget_type or 'tool') == 'view' and self.plugin_enabled(d.plugin_id)]

    def tool_descriptors_for_plugin(self, plugin_id: str) -> List[ToolDescriptor]:
        return [descriptor for descriptor in self._tool_descriptors.values() if descriptor.plugin_id == plugin_id]

    def descriptor_for_tool(self, tool_type_id: str):
        return self._tool_descriptors.get(tool_type_id)

    def plugin(self, plugin_id: str):
        return self._plugins_by_id.get(plugin_id)

    def plugin_manifests(self) -> List[dict]:
        return [self._plugin_manifests[key] for key in sorted(self._plugin_manifests.keys())]

    def plugin_manifest(self, plugin_id: str):
        return self._plugin_manifests.get(plugin_id)

    def plugin_records(self) -> List[dict]:
        return [self._plugin_records[key] for key in sorted(self._plugin_records.keys())]

        manifests = self.plugin_manifests()
        tools = []
        for descriptor in self.tool_descriptors():
            plugin_manifest = self.plugin_manifest(descriptor.plugin_id) or {}
            provider = dict(plugin_manifest.get('provider') or {})
            distribution = dict(plugin_manifest.get('distribution') or {})
            ownership = dict(plugin_manifest.get('ownership') or {})
            tools.append({
                'tool_type_id': descriptor.tool_type_id,
                'display_name': descriptor.display_name,
                'plugin_id': descriptor.plugin_id,
                'description': descriptor.description,
                'widget_type': descriptor.widget_type,
                'metadata': dict(descriptor.metadata or {}),
                'provider_name': provider.get('name', ''),
                'distribution_channel': distribution.get('channel', ''),
                'trust_level': distribution.get('trust', ''),
                'ownership_class': ownership.get('class', ''),
            })
        return {
            'contract': 'platform.plugin_registry.v1',
            'plugins': manifests,
            'tools': sorted(tools, key=lambda item: (item.get('plugin_id') or '', item.get('display_name') or '')),
        }

    def _publish_registry_snapshot(self):
        if self.context is None:
            return
        data_store = getattr(self.context, 'data_store', None)
        if data_store is None:
            return
        try:
            data_store.set('platform.plugins', self.plugin_manifests())
            data_store.set('platform.plugin_records', self.plugin_records())
        except Exception:
            pass