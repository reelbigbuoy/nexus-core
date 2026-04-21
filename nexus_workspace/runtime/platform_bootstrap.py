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
# File: platform_bootstrap.py
# Description: Bootstraps application services, plugins, themes, and workspace startup behavior.
#============================================================================

from __future__ import annotations

from nexus_workspace.framework.graph import NexusGraphService
from nexus_workspace.framework.projects import NexusProjectService
from nexus_workspace.framework.references import NexusReferenceService
from nexus_workspace.framework.review import NexusReviewService


def bootstrap_platform_services(plugin_context):
    if plugin_context is None:
        return {}

    services = {
        'platform.projects': plugin_context.service('platform.projects'),
        'platform.graph': plugin_context.service('platform.graph'),
        'platform.review': plugin_context.service('platform.review'),
        'platform.references': plugin_context.service('platform.references'),
    }

    if services['platform.projects'] is None:
        services['platform.projects'] = NexusProjectService(data_store=plugin_context.data_store)
        plugin_context.register_service(
            'platform.projects',
            services['platform.projects'],
            display_name='Project Registry Service',
            provider_plugin_id='platform',
            description='Tracks Nexus project file conventions and registered document types.',
            metadata={'layer': 'platform', 'role': 'project_registry'},
        )
    if services['platform.graph'] is None:
        services['platform.graph'] = NexusGraphService(data_store=plugin_context.data_store)
        plugin_context.register_service(
            'platform.graph',
            services['platform.graph'],
            display_name='Graph Registry Service',
            provider_plugin_id='platform',
            metadata={'layer': 'platform', 'role': 'graph_registry'},
        )
    if services['platform.references'] is None:
        services['platform.references'] = NexusReferenceService(data_store=plugin_context.data_store)
        plugin_context.register_service(
            'platform.references',
            services['platform.references'],
            display_name='Reference Resolver Service',
            provider_plugin_id='platform',
            metadata={'layer': 'platform', 'role': 'reference_registry'},
        )
    if services['platform.review'] is None:
        services['platform.review'] = NexusReviewService(data_store=plugin_context.data_store)
        plugin_context.register_service(
            'platform.review',
            services['platform.review'],
            display_name='Review Registry Service',
            provider_plugin_id='platform',
            metadata={'layer': 'platform', 'role': 'review_registry'},
        )

    for service in services.values():
        publish = getattr(service, '_publish', None)
        if callable(publish):
            try:
                publish()
            except Exception:
                pass
    return services