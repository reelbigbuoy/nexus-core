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
# File: plugin.py
# Description: Registers the bundled data inspector plugin with the Nexus Core plugin system.
#============================================================================

from ...core import (
    build_capability,
    build_command_contribution,
    build_plugin_manifest,
    build_tool_contribution,
)
from ...framework import NexusCommand, register_nexus_command
from ..base import ToolDescriptor, WorkspacePlugin
from .tool import DataInspectorTool


class DataInspectorPlugin(WorkspacePlugin):
    plugin_id = "data_inspector"
    display_name = "Platform Diagnostics"
    version = "1.1.0"
    description = "Runtime platform diagnostics for the DataStore, plugin registry, actions, events, and state taxonomy."

    def manifest(self):
        return build_plugin_manifest(
            plugin_id=self.plugin_id,
            display_name=self.display_name,
            version=self.version,
            description=self.description,
            tools=[
                build_tool_contribution(
                    tool_type_id="data_inspector",
                    display_name="Platform Diagnostics",
                    description="Inspects DataStore keys, plugin manifests, action routing, event activity, and persisted state boundaries.",
                    widget_type='view',
                    metadata={'surface': 'workspace', 'category': 'platform', 'menu': 'view'},
                )
            ],
            publishes=[],
            consumes=[
                'platform.plugin_registry.v1',
                'platform.state_taxonomy.v1',
                'platform.action_dispatcher.v1',
                'platform.command_registry.v1',
                'command.availability.v1',
                'platform.event_bus.v1',
            ],
            persists=['plugin.tool_state.v1'],
            handles_actions=[],
            commands=[
                build_command_contribution(command_id='platform.refresh_diagnostics', title='Refresh Diagnostics', description='Refresh the active platform diagnostics view.', category='Platform', tool_type_id='data_inspector', requires_active_tool=True),
            ],
            capabilities=[
                build_capability('platform.diagnostics', 'diagnostics', 'Provides a first-class platform diagnostics surface.'),
                build_capability('store.inspection', 'inspector', 'Inspects shared DataStore values and canonical runtime contracts.'),
                build_capability('action.observability', 'observability', 'Shows registered action handlers and recent routed actions.'),
                build_capability('event.observability', 'observability', 'Shows event bus subscriber counts and recent event activity.'),
            ],
            metadata={'category': 'platform', 'panel_role': 'diagnostics', 'type': 'view'},
        )

    def register(self, context):
        context.register_tool(
            ToolDescriptor(
                tool_type_id="data_inspector",
                display_name="Platform Diagnostics",
                create_instance=lambda **kwargs: DataInspectorTool(**kwargs),
                plugin_id=self.plugin_id,
                description="Platform diagnostics and runtime introspection tool.",
                widget_type='view',
                metadata={'surface': 'workspace', 'panel_role': 'diagnostics', 'category': 'platform', 'menu': 'view'},
            )
        )
        context.register_service(
            'diagnostics.platform',
            self,
            display_name='Platform Diagnostics Service',
            provider_plugin_id=self.plugin_id,
            description='Provides the platform diagnostics panel and runtime introspection service.',
            metadata={'panel_role': 'diagnostics'},
        )
        register_nexus_command(
            context,
            NexusCommand(
                command_id='platform.refresh_diagnostics',
                title='Refresh Diagnostics',
                description='Refresh the active platform diagnostics view.',
                plugin_id=self.plugin_id,
                tool_type_id='data_inspector',
                category='Platform',
                requires_active_tool=True,
                keywords=['refresh', 'diagnostics', 'platform'],
            ),
            lambda payload: self._invoke_tool_method(payload, 'refresh_view'),
        )

    def _invoke_tool_method(self, payload, method_name):
        tool = payload.get('active_tool_widget') if isinstance(payload, dict) else None
        if tool is None:
            return {'handled': False, 'status': 'unavailable', 'error': 'No active diagnostics tool.'}
        method = getattr(tool, method_name, None)
        if method is None:
            return {'handled': False, 'status': 'unavailable', 'error': f'Method {method_name} is unavailable.'}
        method()
        return {'handled': True, 'status': 'handled'}
