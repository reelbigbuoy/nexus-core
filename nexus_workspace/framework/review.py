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
# File: review.py
# Description: Defines reusable review-oriented UI components and supporting workflow helpers.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ReviewableArtifactRegistration:
    artifact_type: str
    display_name: str
    plugin_id: str
    supports_text_diff: bool = False
    supports_graph_diff: bool = False
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'artifact_type': self.artifact_type,
            'display_name': self.display_name,
            'plugin_id': self.plugin_id,
            'supports_text_diff': self.supports_text_diff,
            'supports_graph_diff': self.supports_graph_diff,
            'metadata': dict(self.metadata or {}),
        }


@dataclass
class ReviewAnchor:
    document_type: str
    document_id: str
    element_id: str = ''
    element_kind: str = ''
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'document_type': self.document_type,
            'document_id': self.document_id,
            'element_id': self.element_id,
            'element_kind': self.element_kind,
            'metadata': dict(self.metadata or {}),
        }


class NexusReviewService:
    def __init__(self, data_store=None):
        self.data_store = data_store
        self._artifacts: Dict[str, ReviewableArtifactRegistration] = {}

    def register_artifact(self, registration: ReviewableArtifactRegistration):
        self._artifacts[registration.artifact_type] = registration
        self._publish()
        return registration

    def snapshot(self):
        return {
            'contract': 'platform.review_registry.v1',
            'artifacts': [self._artifacts[key].to_dict() for key in sorted(self._artifacts.keys())],
            'anchor_contract': 'platform.review.anchor.v1',
        }

    def _publish(self):
        if self.data_store is None:
            return
        try:
            snapshot = self.snapshot()
            self.data_store.set('platform.review_registry', snapshot)
            self.data_store.set('platform.review_artifacts', snapshot.get('artifacts', []))
        except Exception:
            pass