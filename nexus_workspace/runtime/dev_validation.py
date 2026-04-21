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
# File: dev_validation.py
# Description: Runs development-time validation checks for core modules and bundled plugins.
#============================================================================

from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class ValidationIssue:
    level: str
    message: str
    detail: str = ''


@dataclass
class ValidationReport:
    enabled: bool = False
    issues: List[ValidationIssue] = field(default_factory=list)

    def add(self, level: str, message: str, detail: str = ''):
        self.issues.append(ValidationIssue(level=level, message=message, detail=detail))

    @property
    def has_errors(self) -> bool:
        return any(issue.level == 'error' for issue in self.issues)

    def format_console(self) -> str:
        lines = ['[Nexus] Developer validation report']
        if not self.issues:
            lines.append('  OK - no issues detected.')
            return '\n'.join(lines)
        for issue in self.issues:
            lines.append(f"  {issue.level.upper()}: {issue.message}")
            if issue.detail:
                for detail_line in str(issue.detail).splitlines():
                    lines.append(f"    {detail_line}")
        return '\n'.join(lines)


def dev_validation_enabled() -> bool:
    value = str(os.environ.get('NEXUS_DEV_VALIDATE', '1')).strip().lower()
    return value not in {'0', 'false', 'off', 'no'}


def run_startup_validation(project_root: Path) -> ValidationReport:
    report = ValidationReport(enabled=dev_validation_enabled())
    if not report.enabled:
        return report

    expected_modules = [
        'nexus_workspace.framework.actions',
        'nexus_workspace.framework.forms',
        'nexus_workspace.framework.windowing',
        'nexus_workspace.framework.tools',
        'nexus_workspace.framework.controls',
        'nexus_workspace.shared_widgets.command_palette',
        'nexus_workspace.shared_widgets.plugin_manager_dialog',
        'nexus_workspace.shared_widgets.shortcut_preferences',
        'nexus_workspace.workspace.workspace_window',
        'nexus_workspace.workspace.main_window',
        'nexus_workspace.plugins.property_inspector.tool',
        'nexus_workspace.plugins.data_inspector.tool',
    ]
    for module_name in expected_modules:
        try:
            importlib.import_module(module_name)
        except Exception as exc:
            report.add('error', f'Import failed: {module_name}', ''.join(traceback.format_exception_only(type(exc), exc)).strip())

    plugins_root = project_root / 'plugins'
    command_ids = {}
    if plugins_root.exists():
        for manifest_path in sorted(plugins_root.rglob('plugin.json')):
            try:
                manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
                relative = manifest_path.relative_to(project_root)
                for key in ('schema', 'plugin_id', 'module', 'class'):
                    if not str(manifest.get(key) or '').strip():
                        report.add('warning', f'Manifest missing {key}: {relative}')
                module_name = str(manifest.get('module') or '').strip()
                class_name = str(manifest.get('class') or '').strip()
                if module_name and class_name:
                    try:
                        import_root = str(manifest.get('import_root') or '.').strip() or '.'
                        plugin_import_path = (manifest_path.parent / import_root).resolve()
                        added_path = None
                        if plugin_import_path.exists():
                            added_path = str(plugin_import_path)
                            if added_path not in sys.path:
                                sys.path.insert(0, added_path)
                        module = importlib.import_module(module_name)
                        plugin_cls = getattr(module, class_name, None)
                        if plugin_cls is None:
                            report.add('error', f'Plugin class not found: {relative}', f'{module_name}.{class_name}')
                        elif not inspect.isclass(plugin_cls):
                            report.add('error', f'Plugin target is not a class: {relative}', f'{module_name}.{class_name}')
                    except Exception as exc:
                        report.add('error', f'Plugin import failed: {relative}', ''.join(traceback.format_exception_only(type(exc), exc)).strip())
                    finally:
                        if added_path and added_path in sys.path:
                            try:
                                sys.path.remove(added_path)
                            except ValueError:
                                pass
                tools = manifest.get('tools') or []
                for index, tool in enumerate(tools):
                    if not str((tool or {}).get('tool_type_id') or '').strip():
                        report.add('warning', f'Tool contribution missing tool_type_id: {relative}', f'tools[{index}]')
                    if not str((tool or {}).get('display_name') or '').strip():
                        report.add('warning', f'Tool contribution missing display_name: {relative}', f'tools[{index}]')
                commands = manifest.get('commands') or []
                for index, command in enumerate(commands):
                    command_id = str((command or {}).get('command_id') or '').strip()
                    if not command_id:
                        report.add('warning', f'Command contribution missing command_id: {relative}', f'commands[{index}]')
                    else:
                        command_ids.setdefault(command_id, []).append(str(relative))
                    if not str((command or {}).get('title') or '').strip():
                        report.add('warning', f'Command contribution missing title: {relative}', f'commands[{index}]')
            except Exception as exc:
                report.add('error', f'Failed to parse manifest: {manifest_path.relative_to(project_root)}', str(exc))

    for command_id, owners in sorted(command_ids.items()):
        if len(owners) > 1:
            report.add('warning', f'Duplicate command contribution id: {command_id}', ', '.join(sorted(owners)))

    framework_roots = {'nexus_workspace/framework', 'nexus_workspace/workspace', 'nexus_workspace/core', 'nexus_workspace/runtime'}
    qt_import_count = 0
    for py_path in sorted(project_root.rglob('*.py')):
        relative = py_path.relative_to(project_root).as_posix()
        if relative.startswith('.git/'):
            continue
        try:
            source = py_path.read_text(encoding='utf-8')
        except Exception:
            continue
        if 'from PyQt5' in source or 'import PyQt5' in source:
            if not any(relative.startswith(prefix) for prefix in framework_roots):
                qt_import_count += 1
    report.add('info', 'Direct Qt import count outside framework/core/workspace/runtime', str(qt_import_count))

    return report
