from nexus_workspace.framework.tools import NexusToolBase
from .tool import PluginBuilderWorkbench


class PluginBuilderToolHost(NexusToolBase):
    tool_type_id = "PluginBuilder"
    display_name = "Plugin Builder"
    default_subtitle = "Build responsive Nexus plugin layouts and export them into the plugin sandbox"

    def __init__(self, parent=None, *, theme_name="Midnight", editor_title="Plugin Builder", plugin_context=None):
        super().__init__(parent=parent, theme_name=theme_name, editor_title=editor_title, plugin_context=plugin_context)
        self.ensure_header(title="Plugin Builder", subtitle=self.default_subtitle)
        self._workbench = PluginBuilderWorkbench(parent=self)
        self.content_layout().addWidget(self._workbench, 1)

    def save_state(self):
        state = super().save_state()
        if hasattr(self._workbench, 'save_state'):
            state['workbench'] = self._workbench.save_state()
        return state

    def load_state(self, state):
        super().load_state(state)
        if isinstance(state, dict) and hasattr(self._workbench, 'load_state'):
            self._workbench.load_state(state.get('workbench') or {})

    def __getattr__(self, name):
        workbench = self.__dict__.get("_workbench")
        if workbench is not None:
            return getattr(workbench, name)
        raise AttributeError(name)
