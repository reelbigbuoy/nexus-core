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
# File: projects.py
# Description: Defines project-oriented framework models and helpers for project-backed workflows.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from .documents import NexusDocumentFactory, NexusProjectManifest, NexusProjectSerializer


@dataclass
class DocumentTypeRegistration:
    document_type: str
    display_name: str
    plugin_id: str
    file_extension: str
    description: str = ''
    role: str = 'artifact'
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'document_type': self.document_type,
            'display_name': self.display_name,
            'plugin_id': self.plugin_id,
            'file_extension': self.file_extension,
            'description': self.description,
            'role': self.role,
            'metadata': dict(self.metadata or {}),
        }


class NexusProjectService:
    """Shared project/document registry service.

    The service is intentionally lightweight for now: it establishes a stable
    place for plugins to declare owned file types and the top-level Nexus
    project extension before full save/load behavior is implemented.
    """

    def __init__(self, data_store=None):
        self.data_store = data_store
        self.project_extension = '.nexusproj'
        self.user_state_extension = '.nexususer'
        self._document_types: Dict[str, DocumentTypeRegistration] = {}
        self.document_factory = NexusDocumentFactory(self)
        self.last_project_path = ''
        self.last_project_manifest: Optional[NexusProjectManifest] = None

    def upsert_document_reference(self, document_reference):
        manifest = self.last_project_manifest
        if manifest is None:
            project_root = str(Path(document_reference.path).resolve().parent) if getattr(document_reference, 'path', '') else '.'
            manifest = self.create_project_manifest(name='Nexus Project', project_root=project_root)
        manifest.add_document(document_reference)
        self.last_project_manifest = manifest
        self._publish()
        return manifest

    def save_last_project_manifest(self, path=None):
        manifest = self.last_project_manifest
        if manifest is None:
            return None
        target = path or self.last_project_path or str(Path(manifest.project_root) / f"{manifest.project_id or 'project'}{self.project_extension}")
        return self.save_project_manifest(target, manifest)

    def register_document_type(self, registration: DocumentTypeRegistration):
        self._document_types[registration.document_type] = registration
        self._publish()
        return registration

    def document_type_registration(self, document_type: str):
        return self._document_types.get(document_type)

    def document_type_for_extension(self, file_extension: str):
        needle = str(file_extension or '').lower()
        for registration in self._document_types.values():
            if str(registration.file_extension or '').lower() == needle:
                return registration
        return None

    def create_project_manifest(self, *, name: str, project_id: str = 'project', project_root: str = '.', documents=None, metadata=None):
        return self.document_factory.create_project_manifest(
            name=name,
            project_id=project_id,
            project_root=project_root,
            documents=documents,
            metadata=metadata,
        )

    def save_project_manifest(self, path, manifest: NexusProjectManifest):
        saved = NexusProjectSerializer.save(path, manifest)
        self.last_project_path = str(saved)
        self.last_project_manifest = manifest
        self._publish()
        return saved

    def load_project_manifest(self, path):
        manifest = NexusProjectSerializer.load(path)
        self.last_project_path = str(Path(path))
        self.last_project_manifest = manifest
        self._publish()
        return manifest

    def snapshot(self):
        return {
            'contract': 'platform.project_registry.v1',
            'project_extension': self.project_extension,
            'user_state_extension': self.user_state_extension,
            'document_types': [self._document_types[key].to_dict() for key in sorted(self._document_types.keys())],
            'last_project_path': self.last_project_path,
            'last_project_manifest': self.last_project_manifest.to_dict() if self.last_project_manifest is not None else None,
        }

    def _publish(self):
        if self.data_store is None:
            return
        try:
            snapshot = self.snapshot()
            self.data_store.set('platform.project_registry', snapshot)
            self.data_store.set('platform.document_types', snapshot.get('document_types', []))
        except Exception:
            pass