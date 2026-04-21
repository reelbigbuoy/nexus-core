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
# File: references.py
# Description: Provides reference and linking helpers for cross-object navigation within the workspace.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class NexusReference:
    object_type: str
    object_id: str
    document_id: str = ''
    document_type: str = ''
    display_name: str = ''
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'object_type': self.object_type,
            'object_id': self.object_id,
            'document_id': self.document_id,
            'document_type': self.document_type,
            'display_name': self.display_name,
            'metadata': dict(self.metadata or {}),
        }


class NexusReferenceService:
    CAP_KEY = 'ecosystem.nexcap.documents'
    REQ_KEY = 'ecosystem.nexreq.documents'
    TEST_KEY = 'ecosystem.nextest.documents'

    def __init__(self, data_store=None):
        self.data_store = data_store

    def capabilities(self) -> List[Dict[str, object]]:
        payload = self._payload(self.CAP_KEY)
        rows = []
        for document in payload.get('documents', []) or []:
            document_id = str(document.get('document_id') or '')
            document_path = str(document.get('document_path') or '')
            for capability in document.get('capabilities', []) or []:
                item = dict(capability or {})
                item.setdefault('_document_id', document_id)
                item.setdefault('_document_path', document_path)
                rows.append(item)
        rows.sort(key=lambda item: (str(item.get('name') or '').lower(), str(item.get('id') or '').lower()))
        return rows

    def capability_by_id(self, capability_id: str) -> Optional[Dict[str, object]]:
        needle = str(capability_id or '')
        for capability in self.capabilities():
            if str(capability.get('id') or '') == needle:
                return capability
        return None

    def capability_name(self, capability_id: str) -> str:
        capability = self.capability_by_id(capability_id)
        if capability is None:
            return ''
        return str(capability.get('name') or capability.get('id') or '')

    def requirements(self) -> List[Dict[str, object]]:
        payload = self._payload(self.REQ_KEY)
        rows = []
        for document in payload.get('documents', []) or []:
            document_id = str(document.get('document_id') or '')
            document_path = str(document.get('document_path') or '')
            for requirement in document.get('requirements', []) or []:
                item = dict(requirement or {})
                item.setdefault('_document_id', document_id)
                item.setdefault('_document_path', document_path)
                rows.append(item)
        rows.sort(key=lambda item: (str(item.get('id') or '').lower(), str(item.get('title') or '').lower()))
        return rows

    def requirement_by_id(self, requirement_id: str) -> Optional[Dict[str, object]]:
        needle = str(requirement_id or '')
        for requirement in self.requirements():
            if str(requirement.get('id') or '') == needle:
                return requirement
        return None

    def requirement_elements(self, requirement_id: str) -> List[Dict[str, object]]:
        requirement = self.requirement_by_id(requirement_id)
        if requirement is None:
            return []
        rows = []
        for entry in requirement.get('preconditions', []) or []:
            rows.append(dict(entry or {}))
        trigger = requirement.get('trigger') or {}
        if isinstance(trigger, dict) and trigger:
            rows.append(dict(trigger))
        for entry in requirement.get('outputs', []) or []:
            rows.append(dict(entry or {}))
        return rows

    def requirements_for_capability(self, capability_id: str) -> List[Dict[str, object]]:
        needle = str(capability_id or '')
        return [req for req in self.requirements() if str(req.get('linked_capability_id') or '') == needle]

    def tests(self) -> List[Dict[str, object]]:
        payload = self._payload(self.TEST_KEY)
        rows = []
        for document in payload.get('documents', []) or []:
            document_id = str(document.get('document_id') or '')
            document_path = str(document.get('document_path') or '')
            for test_case in document.get('tests', []) or []:
                item = dict(test_case or {})
                item.setdefault('_document_id', document_id)
                item.setdefault('_document_path', document_path)
                rows.append(item)
        rows.sort(key=lambda item: (str(item.get('id') or '').lower(), str(item.get('name') or '').lower()))
        return rows

    def tests_for_requirement(self, requirement_id: str) -> List[Dict[str, object]]:
        needle = str(requirement_id or '')
        matches = []
        for test_case in self.tests():
            for step in test_case.get('steps', []) or []:
                if str(step.get('linked_requirement_id') or '') == needle:
                    matches.append(test_case)
                    break
        return matches

    def tests_for_requirement_element(self, requirement_id: str, element_id: str) -> List[Dict[str, object]]:
        req_needle = str(requirement_id or '')
        elem_needle = str(element_id or '')
        matches = []
        for test_case in self.tests():
            for step in test_case.get('steps', []) or []:
                if str(step.get('linked_requirement_id') or '') == req_needle and str(step.get('linked_element_id') or '') == elem_needle:
                    matches.append(test_case)
                    break
        return matches

    def coverage_rows(self) -> List[Dict[str, object]]:
        rows = []
        for requirement in self.requirements():
            req_id = str(requirement.get('id') or '')
            capability_id = str(requirement.get('linked_capability_id') or '')
            tests = self.tests_for_requirement(req_id)
            rows.append({
                'capability_id': capability_id,
                'capability_name': self.capability_name(capability_id) or 'Unlinked',
                'requirement_id': req_id,
                'requirement_title': str(requirement.get('title') or req_id or 'Requirement'),
                'test_count': len(tests),
                'covered': bool(tests),
                'test_names': [str(test.get('name') or test.get('id') or 'Test') for test in tests],
                'validation_issues': self.requirement_validation(requirement),
            })
        return rows

    def capability_validation(self, capability_id: str) -> List[str]:
        capability = self.capability_by_id(capability_id)
        if capability is None:
            return []
        issues = []
        if not self.requirements_for_capability(capability_id):
            issues.append('Capability is not linked to any requirements yet.')
        return issues

    def requirement_validation(self, requirement: Dict[str, object]) -> List[str]:
        issues = []
        trigger = requirement.get('trigger') or {}
        if not str((trigger or {}).get('text') or '').strip():
            issues.append('Requirement is missing a trigger.')
        outputs = requirement.get('outputs', []) or []
        if not outputs:
            issues.append('Requirement has no expected outputs.')
        if not str(requirement.get('linked_capability_id') or '').strip():
            issues.append('Requirement is not linked to a capability.')
        return issues

    def snapshot(self):
        capabilities = self.capabilities()
        requirements = self.requirements()
        tests = self.tests()
        return {
            'contract': 'platform.references.v1',
            'counts': {
                'capabilities': len(capabilities),
                'requirements': len(requirements),
                'tests': len(tests),
            },
            'coverage_rows': self.coverage_rows(),
        }

    def _payload(self, key: str) -> Dict[str, object]:
        if self.data_store is None:
            return {}
        payload = self.data_store.get(key) or {}
        return payload if isinstance(payload, dict) else {}

    def _publish(self):
        if self.data_store is None:
            return
        try:
            self.data_store.set('platform.references', self.snapshot())
        except Exception:
            pass
