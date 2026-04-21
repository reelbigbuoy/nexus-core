# ============================================================================
# Nexus
# File: plugin.py
# Description: 
# Part of: NoDE Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================
from nexus_workspace.core import build_plugin_manifest, build_tool_contribution
from nexus_workspace.plugins.base import ToolDescriptor, WorkspacePlugin
from .tool_host import NoDEViewBuilderToolHost


class NoDEViewBuilderPlugin(WorkspacePlugin):
    plugin_id = "NoDEViewBuilder"
    display_name = "NoDE View Builder"
    version = "1.0.0"
    description = "Creates NoDE / NoDE Lite views and custom node definitions."

    def manifest(self):
        return build_plugin_manifest(
            plugin_id=self.plugin_id,
            display_name=self.display_name,
            version=self.version,
            description=self.description,
            tools=[
                build_tool_contribution(
                    tool_type_id="NoDEViewBuilder",
                    display_name="NoDE View Builder",
                    description="Creates view manifests and node definition files for NoDE-family plugins.",
                    metadata={'surface': 'workspace', 'menu': 'tools'},
                )
            ],
            publishes=[], persists=['plugin.tool_state.v1'], consumes=[], handles_actions=[], commands=[], capabilities=[], metadata={'category': 'builder'}
        )

    def register(self, context):
        context.register_tool(
            ToolDescriptor(
                tool_type_id="NoDEViewBuilder",
                display_name="NoDE View Builder",
                create_instance=lambda **kwargs: NoDEViewBuilderToolHost(**kwargs),
                plugin_id=self.plugin_id,
                description="Creates view manifests and node definition files for NoDE-family plugins.",
                metadata={'surface': 'workspace', 'category': 'builder'},
            )
        )
