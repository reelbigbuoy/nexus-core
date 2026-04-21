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
# File: services.py
# Description: Defines shared service keys and convenience accessors for core application services.
#============================================================================

from .action_contract import normalize_action_request
from dataclasses import dataclass, field

from .service_registry import ServiceRegistry


@dataclass
class PluginContext:
    plugin_manager: object = None
    workspace_manager: object = None
    event_bus: object = None
    state_manager: object = None
    session_manager: object = None
    data_store: object = None
    action_dispatcher: object = None
    context_resolver: object = None
    command_service: object = None
    service_registry: object = field(default_factory=ServiceRegistry)

    def register_tool(self, descriptor):
        return self.plugin_manager.register_tool(descriptor)

    def descriptor_for_tool(self, tool_type_id: str):
        return self.plugin_manager.descriptor_for_tool(tool_type_id)

    def tool_descriptors(self):
        return self.plugin_manager.tool_descriptors()

    def plugin_manifest(self, plugin_id: str):
        return self.plugin_manager.plugin_manifest(plugin_id)

    def plugin_manifests(self):
        return self.plugin_manager.plugin_manifests()

    def plugin_registry(self):
        return self.plugin_manager.capabilities_snapshot()

    def publish_action_request(self, payload):
        if self.event_bus is not None:
            self.event_bus.publish('action.requested', normalize_action_request(payload))

    def create_action_handler_scope(self):
        if self.action_dispatcher is None:
            return None
        return self.action_dispatcher.create_handler_scope()

    def register_action_handler(self, *, action_type, callback, plugin_id=None, source_plugin_id=None, target_kind=None, target_contract=None, name=None):
        if self.action_dispatcher is None:
            return None
        return self.action_dispatcher.register_handler(
            action_type=action_type,
            callback=callback,
            plugin_id=plugin_id,
            source_plugin_id=source_plugin_id,
            target_kind=target_kind,
            target_contract=target_contract,
            name=name,
        )

    def unregister_action_handler(self, registration):
        if self.action_dispatcher is not None:
            self.action_dispatcher.unregister_handler(registration)
    def publish_active_tool_context(self, tool, window=None):
        if self.context_resolver is not None:
            return self.context_resolver.publish_active_tool(tool, window=window)
        return None

    def current_context(self, key: str, default=None):
        if self.data_store is None:
            return default
        return self.data_store.get(key, default)


    def register_service(self, service_id: str, instance, *, display_name: str = '', provider_plugin_id: str = '', description: str = '', metadata=None):
        descriptor = self.service_registry.register_service(
            service_id,
            instance,
            display_name=display_name,
            provider_plugin_id=provider_plugin_id,
            description=description,
            metadata=metadata,
        )
        self._publish_service_registry_snapshot()
        return descriptor

    def service(self, service_id: str, default=None):
        return self.service_registry.service(service_id, default)

    def service_descriptor(self, service_id: str):
        return self.service_registry.descriptor(service_id)

    def available_services(self):
        return self.service_registry.descriptors()

    def service_registry_snapshot(self):
        return self.service_registry.snapshot()

    def _publish_service_registry_snapshot(self):
        if self.data_store is None:
            return
        try:
            snapshot = self.service_registry_snapshot()
            self.data_store.set('platform.service_registry', snapshot)
            self.data_store.set('platform.services', snapshot.get('services', []))
        except Exception:
            pass

    def register_command(self, **kwargs):
        if self.command_service is None:
            return None
        return self.command_service.register_command(**kwargs)

    def execute_command(self, command_id: str):
        if self.command_service is None:
            return {'handled': False, 'status': 'unavailable', 'error': 'Command service is unavailable.'}
        return self.command_service.execute(command_id)

    def available_commands(self):
        if self.command_service is None:
            return []
        return self.command_service.available_commands()

    def search_available_commands(self, query: str = ''):
        if self.command_service is None:
            return []
        return self.command_service.search_available_commands(query)

    def command_registry(self):
        if self.command_service is None:
            return {'contract': 'platform.command_registry.v1', 'commands': [], 'categories': []}
        return self.command_service.command_registry_snapshot()

    def shortcut_registry(self):
        if self.command_service is None:
            return {'contract': 'platform.shortcut_registry.v1', 'entries': []}
        return self.command_service.shortcut_registry_snapshot()

    def shortcut_bindings(self):
        if self.command_service is None:
            return {}
        return self.command_service.shortcut_bindings()

    def set_shortcut_override(self, command_id: str, shortcut: str):
        if self.command_service is None:
            return None
        return self.command_service.set_shortcut_override(command_id, shortcut)

    def clear_shortcut_override(self, command_id: str):
        if self.command_service is None:
            return None
        return self.command_service.clear_shortcut_override(command_id)

    def set_shortcut_bindings(self, bindings=None):
        if self.command_service is None:
            return None
        return self.command_service.set_shortcut_bindings(bindings)
