# ============================================================================
# Nexus Core
# File: nexus_workspace/graph_editor/validation.py
# Description: Shared graph validation primitives and engine.
# ============================================================================

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ValidationIssue:
    severity: str
    message: str
    nodes: List[object] = field(default_factory=list)
    connections: List[object] = field(default_factory=list)
    code: Optional[str] = None

    @property
    def state(self):
        value = str(self.severity or '').strip().lower()
        return 'error' if value == 'error' else 'warning'


class GraphValidationPolicy:
    def validate(self, editor, scene):
        return []


class GraphValidationEngine:
    def run(self, editor, scene, policy=None):
        if policy is None:
            return []
        validator = getattr(policy, 'validate', None)
        if not callable(validator):
            return []
        issues = validator(editor, scene) or []
        return [issue for issue in issues if issue is not None]
