from nexus_workspace.core import build_plugin_manifest, build_tool_contribution
from nexus_workspace.plugins.base import ToolDescriptor, WorkspacePlugin
from .tool_host import PluginBuilderToolHost


class PluginBuilderPlugin(WorkspacePlugin):
    plugin_id = "PluginBuilder"
    display_name = "Plugin Builder"
    version = "1.7.9"
    description = "Visual builder for creating Nexus plugins and exporting them into the plugin sandbox."

    def manifest(self):
        return build_plugin_manifest(
            plugin_id=self.plugin_id,
            display_name=self.display_name,
            version=self.version,
            description=self.description,
            tools=[
                build_tool_contribution(
                    tool_type_id="PluginBuilder",
                    display_name="Plugin Builder",
                    description="Design plugin UI scaffolds and export them into plugins/plugin-sandbox.",
                    metadata={"surface": "workspace", "menu": "tools"},
                )
            ],
            publishes=[],
            persists=['plugin.tool_state.v1'],
            consumes=[],
            handles_actions=[],
            commands=[],
            capabilities=[],
            metadata={'category': 'builder'}
        )

    def register(self, context):
        context.register_tool(
            ToolDescriptor(
                tool_type_id="PluginBuilder",
                display_name="Plugin Builder",
                create_instance=lambda **kwargs: PluginBuilderToolHost(**kwargs),
                plugin_id=self.plugin_id,
                description="Visual builder for Nexus plugin scaffolds.",
                metadata={'surface': 'workspace', 'category': 'builder'},
            )
        )
