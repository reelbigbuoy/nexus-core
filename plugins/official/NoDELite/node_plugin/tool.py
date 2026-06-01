# Shared graph editor compatibility wrapper for NoDE-Lite.
from pathlib import Path

from nexus_workspace.graph_editor.definitions import register_node_definition_dir, load_external_node_definitions
from nexus_workspace.graph_editor.node_views import register_node_view_manifest_dir, load_node_views
from nexus_workspace.graph_editor.tool import NoDELiteTool as _SharedGraphTool


def _register_local_graph_assets():
    """Register NoDE Lite-owned node definitions and view manifests.

    The shared graph editor also ships a generic default_view manifest.  NoDE
    Lite's default_view must come from the plugin folder so edits made under
    plugins/official/NoDELite/node_plugin/node_view_manifests are reflected in
    the active tool and in zone-scoped right-click palettes.
    """
    root = Path(__file__).resolve().parent
    register_node_definition_dir(root / "node_definitions")
    register_node_view_manifest_dir(root / "node_view_manifests")
    load_external_node_definitions(clear_existing=True)
    load_node_views(clear_existing=True)


class NoDELiteTool(_SharedGraphTool):
    def __init__(self, parent=None, theme_name="Midnight", editor_title="Untitled Graph", plugin_context=None):
        _register_local_graph_assets()
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
