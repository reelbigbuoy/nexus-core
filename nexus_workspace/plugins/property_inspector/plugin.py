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
# Description: Registers the bundled property inspector plugin with the Nexus Core plugin system.
#============================================================================

from ...core import (
    build_capability,
    build_plugin_manifest,
    build_tool_contribution,
)
from ..base import ToolDescriptor, WorkspacePlugin
from .tool import PropertyInspectorTool


class PropertyInspectorPlugin(WorkspacePlugin):
    plugin_id = "property_inspector"
    display_name = "Property Inspector"
    version = "1.0.0"
    description = "Shared inspection surface for selected objects and contract-backed properties."

    def manifest(self):
        return build_plugin_manifest(
            plugin_id=self.plugin_id,
            display_name=self.display_name,
            version=self.version,
            description=self.description,
            tools=[
                build_tool_contribution(
                    tool_type_id="property_inspector",
                    display_name="Property Inspector",
                    description="Renders inspectable selections and requests edits through the action pipeline.",
                    widget_type='view',
                    metadata={'surface': 'workspace', 'menu': 'view'},
                )
            ],
            publishes=['action.request.v1'],
            consumes=['selection.current.v1', 'inspectable.object.v1', 'context.inspectable_target.v1', 'platform.command_registry.v1'],
            persists=['plugin.tool_state.v1'],
            handles_actions=[],
            capabilities=[
                build_capability('selection.inspection', 'inspector', 'Displays canonical selection state.'),
                build_capability('property.editing', 'requester', 'Requests property mutations through ActionDispatcher.'),
                build_capability('shared.widget.host', 'ui', 'Hosts the reusable PropertyGridWidget.'),
            ],
            metadata={'category': 'platform', 'panel_role': 'inspector', 'type': 'view'},
        )

    def register(self, context):
        context.register_tool(
            ToolDescriptor(
                tool_type_id="property_inspector",
                display_name="Property Inspector",
                create_instance=lambda **kwargs: PropertyInspectorTool(**kwargs),
                plugin_id=self.plugin_id,
                description="Selection and property inspection tool.",
                widget_type='view',
                metadata={'surface': 'workspace', 'panel_role': 'inspector', 'menu': 'view'},
            )
        )
        context.register_service(
            'inspection.properties',
            self,
            display_name='Property Inspection Service',
            provider_plugin_id=self.plugin_id,
            description='Provides the shared property inspection surface.',
            metadata={'panel_role': 'inspector'},
        )
