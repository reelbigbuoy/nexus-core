# ============================================================================
# Nexus
# File: tool_host.py
# Description: 
# Part of: NoDE Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================
from nexus_workspace.framework.tools import NexusToolBase
from .tool import NoDEViewBuilderTool


class NoDEViewBuilderToolHost(NexusToolBase):
    tool_type_id = "NoDEViewBuilder"
    display_name = "NoDE View Builder"
    default_subtitle = "Create custom views and node types"

    def __init__(self, parent=None, *, theme_name="Midnight", editor_title="NoDE View Builder", plugin_context=None):
        super().__init__(parent=parent, theme_name=theme_name, editor_title=editor_title, plugin_context=plugin_context)
        self.ensure_header(title="NoDE View Builder", subtitle=self.default_subtitle)
        self._workbench = NoDEViewBuilderTool(parent=self)
        self.content_layout().addWidget(self._workbench, 1)

    def __getattr__(self, name):
        workbench = self.__dict__.get("_workbench")
        if workbench is not None:
            return getattr(workbench, name)
        raise AttributeError(name)
