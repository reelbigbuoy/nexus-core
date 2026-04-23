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
# File: base.py
# Description: Defines the base plugin classes and interfaces used by the plugin system.
#============================================================================

from dataclasses import dataclass
from typing import Callable
from nexus_workspace.framework.qt import QtCore, QtWidgets

from ..core.plugin_contract import build_plugin_manifest


@dataclass
class ToolDescriptor:
    tool_type_id: str
    display_name: str
    create_instance: Callable[..., QtWidgets.QWidget]
    plugin_id: str = ''
    description: str = ''
    widget_type: str = 'tool'
    metadata: dict = None


class WorkspacePlugin:
    plugin_id = ''
    display_name = ''
    version = '1.0.0'
    description = ''

    def register(self, context):
        raise NotImplementedError

    def manifest(self):
        return build_plugin_manifest(
            plugin_id=self.plugin_id,
            display_name=self.display_name or self.plugin_id,
            version=getattr(self, 'version', '1.0.0'),
            description=getattr(self, 'description', ''),
        )


def reset_tool_theme(tool, theme_name):
    if tool is None or not hasattr(tool, 'apply_theme'):
        return
    try:
        tool.apply_theme(theme_name)
    except Exception:
        return

    def _deferred():
        try:
            tool.apply_theme(theme_name)
        except Exception:
            pass

    QtCore.QTimer.singleShot(0, _deferred)