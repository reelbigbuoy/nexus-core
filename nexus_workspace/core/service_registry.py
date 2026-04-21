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
# File: service_registry.py
# Description: Implements the registry used to register and resolve shared services.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ServiceDescriptor:
    service_id: str
    display_name: str = ''
    provider_plugin_id: str = ''
    description: str = ''
    metadata: Dict[str, Any] = field(default_factory=dict)
    instance: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'service_id': self.service_id,
            'display_name': self.display_name or self.service_id,
            'provider_plugin_id': self.provider_plugin_id,
            'description': self.description,
            'metadata': dict(self.metadata or {}),
        }


class ServiceRegistry:
    def __init__(self):
        self._services: Dict[str, ServiceDescriptor] = {}

    def register_service(self, service_id: str, instance: Any, *, display_name: str = '', provider_plugin_id: str = '', description: str = '', metadata: Optional[Dict[str, Any]] = None) -> ServiceDescriptor:
        descriptor = ServiceDescriptor(
            service_id=service_id,
            display_name=display_name or service_id,
            provider_plugin_id=provider_plugin_id,
            description=description,
            metadata=dict(metadata or {}),
            instance=instance,
        )
        self._services[service_id] = descriptor
        return descriptor

    def service(self, service_id: str, default: Any = None) -> Any:
        descriptor = self._services.get(service_id)
        if descriptor is None:
            return default
        return descriptor.instance

    def descriptor(self, service_id: str) -> Optional[ServiceDescriptor]:
        return self._services.get(service_id)

    def descriptors(self) -> List[ServiceDescriptor]:
        return [self._services[key] for key in sorted(self._services.keys())]

    def snapshot(self) -> Dict[str, Any]:
        return {
            'contract': 'platform.service_registry.v1',
            'services': [descriptor.to_dict() for descriptor in self.descriptors()],
        }