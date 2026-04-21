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
# Description: Package initializer for reusable Nexus Core framework components.
#============================================================================

from importlib import import_module

_EXPORTS = {
    'NexusAction': ('nexus_workspace.framework.actions', 'NexusAction'),
    'NexusCommand': ('nexus_workspace.framework.actions', 'NexusCommand'),
    'NexusCommandContribution': ('nexus_workspace.framework.actions', 'NexusCommandContribution'),
    'NexusCommandRegistry': ('nexus_workspace.framework.actions', 'NexusCommandRegistry'),
    'NexusCommandMenuBuilder': ('nexus_workspace.framework.actions', 'NexusCommandMenuBuilder'),
    'NexusCommandBar': ('nexus_workspace.framework.actions', 'NexusCommandBar'),
    'NexusCommandList': ('nexus_workspace.framework.actions', 'NexusCommandList'),
    'NexusToolbar': ('nexus_workspace.framework.actions', 'NexusToolbar'),
    'build_action_from_payload': ('nexus_workspace.framework.actions', 'build_action_from_payload'),
    'register_nexus_command': ('nexus_workspace.framework.actions', 'register_nexus_command'),
    'NexusListWidget': ('nexus_workspace.framework.controls', 'NexusListWidget'),
    'NexusSection': ('nexus_workspace.framework.controls', 'NexusSection'),
    'NexusSplitter': ('nexus_workspace.framework.controls', 'NexusSplitter'),
    'NexusTabWidget': ('nexus_workspace.framework.controls', 'NexusTabWidget'),
    'NexusTableWidget': ('nexus_workspace.framework.controls', 'NexusTableWidget'),
    'NexusTreeWidget': ('nexus_workspace.framework.controls', 'NexusTreeWidget'),
    'NexusDataModelForm': ('nexus_workspace.framework.forms', 'NexusDataModelForm'),
    'NexusFieldRow': ('nexus_workspace.framework.forms', 'NexusFieldRow'),
    'NexusForm': ('nexus_workspace.framework.forms', 'NexusForm'),
    'NexusInspectorSection': ('nexus_workspace.framework.forms', 'NexusInspectorSection'),
    'NexusSearchBar': ('nexus_workspace.framework.forms', 'NexusSearchBar'),
    'NexusPropertyGrid': ('nexus_workspace.framework.inspectors', 'NexusPropertyGrid'),
    'NexusPanel': ('nexus_workspace.framework.surfaces', 'NexusPanel'),
    'NexusSurface': ('nexus_workspace.framework.surfaces', 'NexusSurface'),
    'NexusToolHeader': ('nexus_workspace.framework.surfaces', 'NexusToolHeader'),
    'NexusToolbarRow': ('nexus_workspace.framework.surfaces', 'NexusToolbarRow'),
    'NexusToolBase': ('nexus_workspace.framework.tools', 'NexusToolBase'),
    'EcosystemShellTool': ('nexus_workspace.framework.ecosystem', 'EcosystemShellTool'),
    'NexusDocumentReference': ('nexus_workspace.framework.documents', 'NexusDocumentReference'),
    'NexusProjectManifest': ('nexus_workspace.framework.documents', 'NexusProjectManifest'),
    'NexusProjectSerializer': ('nexus_workspace.framework.documents', 'NexusProjectSerializer'),
    'NexusDocumentFactory': ('nexus_workspace.framework.documents', 'NexusDocumentFactory'),
    'DocumentTypeRegistration': ('nexus_workspace.framework.projects', 'DocumentTypeRegistration'),
    'NexusProjectService': ('nexus_workspace.framework.projects', 'NexusProjectService'),
    'GraphPortDefinition': ('nexus_workspace.framework.graph', 'GraphPortDefinition'),
    'GraphDomainRegistration': ('nexus_workspace.framework.graph', 'GraphDomainRegistration'),
    'GraphEdgeRecord': ('nexus_workspace.framework.graph', 'GraphEdgeRecord'),
    'GraphDocumentModel': ('nexus_workspace.framework.graph', 'GraphDocumentModel'),
    'NexusGraphService': ('nexus_workspace.framework.graph', 'NexusGraphService'),
    'NexusSimpleGraphCanvas': ('nexus_workspace.framework.graph', 'NexusSimpleGraphCanvas'),
    'ReviewableArtifactRegistration': ('nexus_workspace.framework.review', 'ReviewableArtifactRegistration'),
    'ReviewAnchor': ('nexus_workspace.framework.review', 'ReviewAnchor'),
    'NexusReviewService': ('nexus_workspace.framework.review', 'NexusReviewService'),
    'NexusReference': ('nexus_workspace.framework.references', 'NexusReference'),
    'NexusReferenceService': ('nexus_workspace.framework.references', 'NexusReferenceService'),
    'NexusDialogBase': ('nexus_workspace.framework.windowing', 'NexusDialogBase'),
    'NexusMessageDialog': ('nexus_workspace.framework.windowing', 'NexusMessageDialog'),
    'NexusTitleBar': ('nexus_workspace.framework.windowing', 'NexusTitleBar'),
    'NexusWindowBase': ('nexus_workspace.framework.windowing', 'NexusWindowBase'),
    'load_nexus_icon': ('nexus_workspace.framework.windowing', 'load_nexus_icon'),
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