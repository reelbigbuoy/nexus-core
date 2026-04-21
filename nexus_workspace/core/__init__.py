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
# File: __init__.py
# Description: Package initializer for core contracts, services, and state modules.
#============================================================================

from importlib import import_module

_EXPORTS = {
    "DataStore": ("nexus_workspace.core.data_store", "DataStore"),
    "EventBus": ("nexus_workspace.core.events", "EventBus"),
    "NexusSerializable": ("nexus_workspace.core.serialization", "NexusSerializable"),
    "PluginContext": ("nexus_workspace.core.services", "PluginContext"),
    "StateManager": ("nexus_workspace.core.state", "StateManager"),
    "SessionManager": ("nexus_workspace.core.session", "SessionManager"),
    "ActionDispatcher": ("nexus_workspace.core.action_dispatcher", "ActionDispatcher"),
    "ActionHandlerScope": ("nexus_workspace.core.action_dispatcher", "ActionHandlerScope"),
    "ACTION_HANDLED_EVENT": ("nexus_workspace.core.action_dispatcher", "ACTION_HANDLED_EVENT"),
    "ACTION_UNHANDLED_EVENT": ("nexus_workspace.core.action_dispatcher", "ACTION_UNHANDLED_EVENT"),
    "ACTION_FAILED_EVENT": ("nexus_workspace.core.action_dispatcher", "ACTION_FAILED_EVENT"),
    "ACTION_REQUEST_CONTRACT": ("nexus_workspace.core.action_contract", "ACTION_REQUEST_CONTRACT"),
    "ACTION_RESULT_CONTRACT": ("nexus_workspace.core.action_contract", "ACTION_RESULT_CONTRACT"),
    "ACTION_STATUS_FAILED": ("nexus_workspace.core.action_contract", "ACTION_STATUS_FAILED"),
    "ACTION_STATUS_HANDLED": ("nexus_workspace.core.action_contract", "ACTION_STATUS_HANDLED"),
    "ACTION_STATUS_UNHANDLED": ("nexus_workspace.core.action_contract", "ACTION_STATUS_UNHANDLED"),
    "PROPERTY_EDIT_REQUEST": ("nexus_workspace.core.action_contract", "PROPERTY_EDIT_REQUEST"),
    "ActionHandlerSpec": ("nexus_workspace.core.action_contract", "ActionHandlerSpec"),
    "build_action_request": ("nexus_workspace.core.action_contract", "build_action_request"),
    "build_action_result": ("nexus_workspace.core.action_contract", "build_action_result"),
    "normalize_action_request": ("nexus_workspace.core.action_contract", "normalize_action_request"),
    "normalize_action_result": ("nexus_workspace.core.action_contract", "normalize_action_result"),
    "ACTION_REQUEST_EVENT": ("nexus_workspace.core.action_requests", "ACTION_REQUEST_EVENT"),
    "ActionRequestPublisher": ("nexus_workspace.core.action_requests", "ActionRequestPublisher"),
    "DATA_MODEL_CONTRACT": ("nexus_workspace.core.data_model", "DATA_MODEL_CONTRACT"),
    "build_data_field": ("nexus_workspace.core.data_model", "build_data_field"),
    "build_data_section": ("nexus_workspace.core.data_model", "build_data_section"),
    "build_data_model": ("nexus_workspace.core.data_model", "build_data_model"),
    "normalize_data_field": ("nexus_workspace.core.data_model", "normalize_data_field"),
    "normalize_data_section": ("nexus_workspace.core.data_model", "normalize_data_section"),
    "normalize_data_model": ("nexus_workspace.core.data_model", "normalize_data_model"),
    "data_model_to_inspectable": ("nexus_workspace.core.data_model", "data_model_to_inspectable"),
    "INSPECTABLE_OBJECT_CONTRACT": ("nexus_workspace.core.inspectable_contract", "INSPECTABLE_OBJECT_CONTRACT"),
    "build_field_descriptor": ("nexus_workspace.core.inspectable_contract", "build_field_descriptor"),
    "build_section": ("nexus_workspace.core.inspectable_contract", "build_section"),
    "build_inspectable_object": ("nexus_workspace.core.inspectable_contract", "build_inspectable_object"),
    "normalize_inspectable_object": ("nexus_workspace.core.inspectable_contract", "normalize_inspectable_object"),
    "PLUGIN_MANIFEST_CONTRACT": ("nexus_workspace.core.plugin_contract", "PLUGIN_MANIFEST_CONTRACT"),
    "CapabilityDescriptor": ("nexus_workspace.core.plugin_contract", "CapabilityDescriptor"),
    "PluginManifest": ("nexus_workspace.core.plugin_contract", "PluginManifest"),
    "ToolContribution": ("nexus_workspace.core.plugin_contract", "ToolContribution"),
    "build_capability": ("nexus_workspace.core.plugin_contract", "build_capability"),
    "build_plugin_manifest": ("nexus_workspace.core.plugin_contract", "build_plugin_manifest"),
    "build_tool_contribution": ("nexus_workspace.core.plugin_contract", "build_tool_contribution"),
    "PERSISTED_STATE_CONTRACT": ("nexus_workspace.core.state_contract", "PERSISTED_STATE_CONTRACT"),
    "PLUGIN_TOOL_STATE_CONTRACT": ("nexus_workspace.core.state_contract", "PLUGIN_TOOL_STATE_CONTRACT"),
    "STATE_TAXONOMY_CONTRACT": ("nexus_workspace.core.state_contract", "STATE_TAXONOMY_CONTRACT"),
    "WORKSPACE_WINDOW_STATE_CONTRACT": ("nexus_workspace.core.state_contract", "WORKSPACE_WINDOW_STATE_CONTRACT"),
    "PluginToolStateEnvelope": ("nexus_workspace.core.state_contract", "PluginToolStateEnvelope"),
    "WorkspaceWindowStateEnvelope": ("nexus_workspace.core.state_contract", "WorkspaceWindowStateEnvelope"),
    "build_plugin_tool_state": ("nexus_workspace.core.state_contract", "build_plugin_tool_state"),
    "build_state_taxonomy": ("nexus_workspace.core.state_contract", "build_state_taxonomy"),
    "build_workspace_window_state": ("nexus_workspace.core.state_contract", "build_workspace_window_state"),
    "normalize_persisted_state": ("nexus_workspace.core.state_contract", "normalize_persisted_state"),
    "CONTEXT_ACTIVE_TOOL_CONTRACT": ("nexus_workspace.core.context_contract", "CONTEXT_ACTIVE_TOOL_CONTRACT"),
    "CONTEXT_ACTIVE_TOOL_KEY": ("nexus_workspace.core.context_contract", "CONTEXT_ACTIVE_TOOL_KEY"),
    "CONTEXT_INSPECTABLE_TARGET_CONTRACT": ("nexus_workspace.core.context_contract", "CONTEXT_INSPECTABLE_TARGET_CONTRACT"),
    "CONTEXT_INSPECTABLE_TARGET_KEY": ("nexus_workspace.core.context_contract", "CONTEXT_INSPECTABLE_TARGET_KEY"),
    "CONTEXT_REGISTRY_CONTRACT": ("nexus_workspace.core.context_contract", "CONTEXT_REGISTRY_CONTRACT"),
    "CONTEXT_REGISTRY_KEY": ("nexus_workspace.core.context_contract", "CONTEXT_REGISTRY_KEY"),
    "build_active_tool_context": ("nexus_workspace.core.context_contract", "build_active_tool_context"),
    "build_context_registry": ("nexus_workspace.core.context_contract", "build_context_registry"),
    "build_inspectable_target_context": ("nexus_workspace.core.context_contract", "build_inspectable_target_context"),
    "normalize_active_tool_context": ("nexus_workspace.core.context_contract", "normalize_active_tool_context"),
    "ContextResolver": ("nexus_workspace.core.context_service", "ContextResolver"),
    "COMMAND_AVAILABLE_CONTRACT": ("nexus_workspace.core.command_contract", "COMMAND_AVAILABLE_CONTRACT"),
    "COMMAND_AVAILABLE_KEY": ("nexus_workspace.core.command_contract", "COMMAND_AVAILABLE_KEY"),
    "COMMAND_DESCRIPTOR_CONTRACT": ("nexus_workspace.core.command_contract", "COMMAND_DESCRIPTOR_CONTRACT"),
    "COMMAND_EXECUTION_RESULT_CONTRACT": ("nexus_workspace.core.command_contract", "COMMAND_EXECUTION_RESULT_CONTRACT"),
    "COMMAND_RECENT_KEY": ("nexus_workspace.core.command_contract", "COMMAND_RECENT_KEY"),
    "COMMAND_REGISTRY_CONTRACT": ("nexus_workspace.core.command_contract", "COMMAND_REGISTRY_CONTRACT"),
    "COMMAND_REGISTRY_KEY": ("nexus_workspace.core.command_contract", "COMMAND_REGISTRY_KEY"),
    "SHORTCUT_REGISTRY_CONTRACT": ("nexus_workspace.core.command_contract", "SHORTCUT_REGISTRY_CONTRACT"),
    "SHORTCUT_REGISTRY_KEY": ("nexus_workspace.core.command_contract", "SHORTCUT_REGISTRY_KEY"),
    "CommandContribution": ("nexus_workspace.core.command_contract", "CommandContribution"),
    "CommandDescriptor": ("nexus_workspace.core.command_contract", "CommandDescriptor"),
    "build_command_availability": ("nexus_workspace.core.command_contract", "build_command_availability"),
    "build_command_contribution": ("nexus_workspace.core.command_contract", "build_command_contribution"),
    "build_command_descriptor": ("nexus_workspace.core.command_contract", "build_command_descriptor"),
    "build_command_execution_result": ("nexus_workspace.core.command_contract", "build_command_execution_result"),
    "build_command_registry": ("nexus_workspace.core.command_contract", "build_command_registry"),
    "build_shortcut_registry": ("nexus_workspace.core.command_contract", "build_shortcut_registry"),
    "CommandService": ("nexus_workspace.core.command_service", "CommandService"),
    "ServiceRegistry": ("nexus_workspace.core.service_registry", "ServiceRegistry"),
    "ServiceDescriptor": ("nexus_workspace.core.service_registry", "ServiceDescriptor"),
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
