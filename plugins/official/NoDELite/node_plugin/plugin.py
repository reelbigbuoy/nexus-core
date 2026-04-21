# ============================================================================
# Nexus
# File: plugins/owner/NoDELite/node_plugin/plugin.py
# Description: Plugin registration and host integration for NoDE Lite Plugin.
# Part of: NoDE Lite Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE Lite repository root for license terms.
# ============================================================================

from nexus_workspace.core import (
    build_capability,
    build_command_contribution,
    build_plugin_manifest,
    build_tool_contribution,
)
from nexus_workspace.plugins.base import ToolDescriptor, WorkspacePlugin
from .tool_host import NoDELiteToolHost


class NoDELitePlugin(WorkspacePlugin):
    plugin_id = "NoDELite"
    display_name = "NoDE Lite"
    version = "1.0.0"
    description = "Node-based graph editor plugin for Nexus Core without runtime/debug tooling."

    def manifest(self):
        return build_plugin_manifest(
            plugin_id=self.plugin_id,
            display_name=self.display_name,
            version=self.version,
            description=self.description,
            tools=[
                build_tool_contribution(
                    tool_type_id="NoDELite",
                    display_name="NoDE Lite",
                    description="Interactive node graph editor.",
                    metadata={'surface': 'workspace', 'menu': 'tools'},
                )
            ],
            publishes=['selection.current.v1', 'inspectable.object.v1'],
            persists=['plugin.tool_state.v1'],
            consumes=['action.request.v1'],
            handles_actions=['property.edit.requested'],
            commands=[
                build_command_contribution(command_id='nodelite.delete_selection', title='Delete Selected', description='Delete the current NoDE Lite selection.', category='Edit', shortcut='Delete', tool_type_id='NoDELite', requires_active_tool=True, required_capabilities=['graph.editing']),
                build_command_contribution(command_id='nodelite.undo', title='Undo', description='Undo the last NoDE Lite change.', category='Edit', shortcut='Ctrl+Z', tool_type_id='NoDELite', requires_active_tool=True),
                build_command_contribution(command_id='nodelite.redo', title='Redo', description='Redo the last NoDE Lite change.', category='Edit', shortcut='Ctrl+Y', tool_type_id='NoDELite', requires_active_tool=True),
                build_command_contribution(command_id='nodelite.save', title='Save Graph', description='Save the active NoDE Lite graph.', category='File', shortcut='Ctrl+S', tool_type_id='NoDELite', requires_active_tool=True),
                build_command_contribution(command_id='nodelite.save_as', title='Save Graph As', description='Save the active NoDE Lite graph to a new file.', category='File', tool_type_id='NoDELite', requires_active_tool=True),
                build_command_contribution(command_id='nodelite.view.switch', title='Switch NoDE Lite View…', description='Choose the active NoDE Lite node view for this graph.', category='View', tool_type_id='NoDELite', requires_active_tool=True),
                build_command_contribution(command_id='nodelite.view.next', title='Next NoDE Lite View', description='Cycle to the next available NoDE Lite view.', category='View', tool_type_id='NoDELite', requires_active_tool=True),
                build_command_contribution(command_id='nodelite.view.previous', title='Previous NoDE Lite View', description='Cycle to the previous available NoDE Lite view.', category='View', tool_type_id='NoDELite', requires_active_tool=True),
            ],
            capabilities=[
                build_capability('graph.editing', 'editor', 'Provides interactive node graph editing.'),
                build_capability('selection.publisher', 'contract', 'Publishes canonical selection state.'),
                build_capability('inspectable.publisher', 'contract', 'Publishes inspectable object metadata for selected nodes.'),
            ],
            metadata={'category': 'graph', 'primary_surface': 'graph'},
        )

    def register(self, context):
        context.register_tool(
            ToolDescriptor(
                tool_type_id="NoDELite",
                display_name="NoDE Lite",
                create_instance=lambda **kwargs: NoDELiteToolHost(**kwargs),
                plugin_id=self.plugin_id,
                description="Node-based graph editor.",
                metadata={'surface': 'workspace', 'category': 'graph', 'file_extensions': ['.nexnode', '.json'], 'file_open_filter': 'Nexus Graph (*.nexnode);;Graph JSON (*.json)'},
            )
        )
        context.register_command(command_id='nodelite.delete_selection', title='Delete Selected', description='Delete the current NoDE Lite selection.', plugin_id=self.plugin_id, tool_type_id='NoDELite', category='Edit', shortcut='Delete', requires_active_tool=True, required_capabilities=['graph.editing'], callback=lambda payload: self._invoke_tool_method(payload, 'delete_selected_items'))
        context.register_command(command_id='nodelite.undo', title='Undo', description='Undo the last NoDE Lite change.', plugin_id=self.plugin_id, tool_type_id='NoDELite', category='Edit', shortcut='Ctrl+Z', requires_active_tool=True, callback=lambda payload: self._invoke_tool_method(payload, 'undo_stack.undo'))
        context.register_command(command_id='nodelite.redo', title='Redo', description='Redo the last NoDE Lite change.', plugin_id=self.plugin_id, tool_type_id='NoDELite', category='Edit', shortcut='Ctrl+Y', requires_active_tool=True, callback=lambda payload: self._invoke_tool_method(payload, 'undo_stack.redo'))
        context.register_command(command_id='nodelite.save', title='Save Graph', description='Save the active NoDE Lite graph.', plugin_id=self.plugin_id, tool_type_id='NoDELite', category='File', shortcut='Ctrl+S', requires_active_tool=True, callback=lambda payload: self._invoke_tool_method(payload, 'save'))
        context.register_command(command_id='nodelite.save_as', title='Save Graph As', description='Save the active NoDE Lite graph to a new file.', plugin_id=self.plugin_id, tool_type_id='NoDELite', category='File', requires_active_tool=True, callback=lambda payload: self._invoke_tool_method(payload, 'save_graph_to_file_as'))
        context.register_command(command_id='nodelite.view.switch', title='Switch NoDE Lite View…', description='Choose the active NoDE Lite node view for this graph.', plugin_id=self.plugin_id, tool_type_id='NoDELite', category='View', requires_active_tool=True, callback=lambda payload: self._invoke_tool_method(payload, 'prompt_select_node_view'))
        context.register_command(command_id='nodelite.view.next', title='Next NoDE Lite View', description='Cycle to the next available NoDE Lite view.', plugin_id=self.plugin_id, tool_type_id='NoDELite', category='View', requires_active_tool=True, callback=lambda payload: self._invoke_tool_method_with_args(payload, 'cycle_node_view', 1))
        context.register_command(command_id='nodelite.view.previous', title='Previous NoDE Lite View', description='Cycle to the previous available NoDE Lite view.', plugin_id=self.plugin_id, tool_type_id='NoDELite', category='View', requires_active_tool=True, callback=lambda payload: self._invoke_tool_method_with_args(payload, 'cycle_node_view', -1))

    def _resolve_tool(self, payload):
        tool = (payload or {}).get('tool')
        if tool is None and isinstance(payload, dict):
            tool = payload.get('active_tool')
        return tool

    def _invoke_tool_method(self, payload, method_path):
        tool = self._resolve_tool(payload)
        if tool is None:
            return False
        target = tool
        for part in method_path.split('.'):
            target = getattr(target, part, None)
            if target is None:
                return False
        return target() if callable(target) else False

    def _invoke_tool_method_with_args(self, payload, method_name, *args):
        tool = self._resolve_tool(payload)
        if tool is None:
            return False
        method = getattr(tool, method_name, None)
        if method is None:
            return False
        return method(*args)
