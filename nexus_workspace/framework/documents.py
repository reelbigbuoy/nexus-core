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
# File: documents.py
# Description: Provides document-oriented framework components for editor and file-based workflows.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import json


@dataclass
class NexusDocumentReference:
    document_id: str
    document_type: str
    path: str
    display_name: str = ''
    plugin_id: str = ''
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'document_id': self.document_id,
            'document_type': self.document_type,
            'path': self.path,
            'display_name': self.display_name,
            'plugin_id': self.plugin_id,
            'metadata': dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        return cls(
            document_id=str(payload.get('document_id') or ''),
            document_type=str(payload.get('document_type') or ''),
            path=str(payload.get('path') or ''),
            display_name=str(payload.get('display_name') or ''),
            plugin_id=str(payload.get('plugin_id') or ''),
            metadata=dict(payload.get('metadata') or {}),
        )


@dataclass
class NexusProjectManifest:
    schema: str = 'nexus.project.v1'
    name: str = 'Untitled Project'
    project_id: str = 'project'
    project_root: str = '.'
    documents: List[NexusDocumentReference] = field(default_factory=list)
    settings: Dict[str, object] = field(default_factory=dict)
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'schema': self.schema,
            'name': self.name,
            'project_id': self.project_id,
            'project_root': self.project_root,
            'documents': [document.to_dict() for document in self.documents],
            'settings': dict(self.settings or {}),
            'metadata': dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, payload):
        payload = dict(payload or {})
        return cls(
            schema=str(payload.get('schema') or 'nexus.project.v1'),
            name=str(payload.get('name') or 'Untitled Project'),
            project_id=str(payload.get('project_id') or 'project'),
            project_root=str(payload.get('project_root') or '.'),
            documents=[NexusDocumentReference.from_dict(item) for item in (payload.get('documents') or [])],
            settings=dict(payload.get('settings') or {}),
            metadata=dict(payload.get('metadata') or {}),
        )

    def add_document(self, document: NexusDocumentReference):
        self.documents = [existing for existing in self.documents if existing.document_id != document.document_id]
        self.documents.append(document)


class NexusProjectSerializer:
    @staticmethod
    def save(path, manifest: NexusProjectManifest):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True), encoding='utf-8')
        return target

    @staticmethod
    def load(path):
        source = Path(path)
        payload = json.loads(source.read_text(encoding='utf-8'))
        return NexusProjectManifest.from_dict(payload)


class NexusDocumentFactory:
    """Lightweight helper for creating deterministic document stubs."""

    def __init__(self, project_service):
        self.project_service = project_service

    def create_stub(self, document_type: str, *, document_id: str, display_name: str = '', metadata=None):
        registration = None
        if self.project_service is not None:
            registration = self.project_service.document_type_registration(document_type)
        registration_metadata = dict(getattr(registration, 'metadata', {}) or {}) if registration is not None else {}
        stub = {
            'schema': document_type,
            'document_id': document_id,
            'display_name': display_name or document_id,
            'plugin_id': getattr(registration, 'plugin_id', ''),
            'metadata': {**registration_metadata, **dict(metadata or {})},
        }
        return stub

    def create_project_manifest(self, *, name: str, project_id: str = 'project', project_root: str = '.', documents: Optional[Iterable[NexusDocumentReference]] = None, metadata=None):
        return NexusProjectManifest(
            name=name,
            project_id=project_id,
            project_root=project_root,
            documents=list(documents or []),
            metadata=dict(metadata or {}),
        )