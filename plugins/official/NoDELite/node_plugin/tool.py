# Shared graph editor compatibility wrapper for NoDE-Lite.
from nexus_workspace.graph_editor.tool import NoDELiteTool as _SharedGraphTool


class NoDELiteTool(_SharedGraphTool):
    def __init__(self, parent=None, theme_name="Midnight", editor_title="Untitled Graph", plugin_context=None):
        super().__init__(
            parent=parent,
            theme_name=theme_name,
            editor_title=editor_title,
            plugin_context=plugin_context,
            tool_type_id="NoDELite",
            plugin_id="NoDELite",
            tool_label="NoDE Lite",
            view_label="NoDE View",
            default_node_view_id="default_view",
            allowed_node_view_ids=["default_view"],
        )
