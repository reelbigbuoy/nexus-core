# ============================================================================
# Nexus
# File: plugins/owner/NoDELite/node_plugin/tool_host.py
# Description: Nexus framework host wrapper for the NoDE Lite workbench.
# Part of: NoDE Lite Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE Lite repository root for license terms.
# ============================================================================

from __future__ import annotations

from nexus_workspace.framework.tools import NexusToolBase

from .tool import NoDELiteTool


class NoDELiteToolHost(NexusToolBase):
    tool_type_id = "NoDELite"
    display_name = "NoDE Lite"
    default_subtitle = "Node-based engineering graph editor"

    def __init__(self, parent=None, *, theme_name="Midnight", editor_title="Untitled Graph", plugin_context=None):
        super().__init__(parent=parent, theme_name=theme_name, editor_title=editor_title, plugin_context=plugin_context)
        self.ensure_header(title="NoDE Lite", subtitle=self.default_subtitle)
        self._workbench = NoDELiteTool(parent=self, theme_name=theme_name, editor_title=editor_title, plugin_context=plugin_context)
        self.content_layout().addWidget(self._workbench, 1)
        self._workbench.titleChanged.connect(self.set_tool_title)
        self._workbench.titleChanged.connect(self._sync_header_title)
        self._sync_header_title(self._workbench.windowTitle() or editor_title)

    def _sync_header_title(self, title):
        self.set_header_title(str(title or self.display_name))

    def workbench(self):
        return self._workbench

    def activate_tool(self):
        super().activate_tool()
        if self._workbench is not None:
            self._workbench.setFocus()

    def apply_theme(self, theme_name):
        super().apply_theme(theme_name)
        workbench = getattr(self, "_workbench", None)
        if workbench is not None and hasattr(workbench, "apply_theme"):
            workbench.apply_theme(theme_name)

    def save_state(self):
        state = super().save_state()
        workbench = getattr(self, "_workbench", None)
        if workbench is not None and hasattr(workbench, "save_state"):
            state["workbench_state"] = workbench.save_state()
        return state

    def load_state(self, state):
        super().load_state(state)
        workbench = getattr(self, "_workbench", None)
        if workbench is not None and hasattr(workbench, "load_state"):
            workbench.load_state((state or {}).get("workbench_state"))

    def __getattr__(self, name):
        workbench = self.__dict__.get("_workbench")
        if workbench is not None:
            return getattr(workbench, name)
        raise AttributeError(f"{self.__class__.__name__!s} has no attribute {name!r}")
