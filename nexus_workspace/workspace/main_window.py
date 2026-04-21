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
# File: main_window.py
# Description: Implements the main application window and top-level workspace integration.
#============================================================================

from pathlib import Path

from PyQt5 import QtCore, QtWidgets

from ..core import ActionDispatcher, CommandService, ContextResolver, DataStore, EventBus, PluginContext, SessionManager, StateManager, build_state_taxonomy
from ..plugins.manager import PluginManager
from ..runtime.plugin_loader import PluginLoader
from ..runtime.platform_bootstrap import bootstrap_platform_services
from .manager_workspace import WorkspaceManager
from .workspace_window import WorkspaceWindow


class WorkspaceMainWindow(WorkspaceWindow):
    def __init__(self):
        workspace_manager = WorkspaceManager()
        self.event_bus = EventBus()
        self.action_dispatcher = ActionDispatcher(event_bus=self.event_bus)
        self.data_store = DataStore(event_bus=self.event_bus)
        self.context_resolver = ContextResolver(data_store=self.data_store, event_bus=self.event_bus)
        self.command_service = CommandService(data_store=self.data_store, plugin_manager=None, workspace_manager=workspace_manager)
        self.event_bus.set_data_store(self.data_store)
        self.action_dispatcher.set_data_store(self.data_store)
        self.state_manager = StateManager()
        self.session_manager = SessionManager(workspace_manager=workspace_manager, state_manager=self.state_manager)
        workspace_manager.session_manager = self.session_manager
        plugin_manager = PluginManager()
        self.command_service.plugin_manager = plugin_manager
        plugin_context = PluginContext(
            plugin_manager=plugin_manager,
            workspace_manager=workspace_manager,
            event_bus=self.event_bus,
            state_manager=self.state_manager,
            session_manager=self.session_manager,
            data_store=self.data_store,
            action_dispatcher=self.action_dispatcher,
            context_resolver=self.context_resolver,
            command_service=self.command_service,
        )
        plugin_manager.set_context(plugin_context)
        self.platform_services = bootstrap_platform_services(plugin_context)

        loaded_state = self.state_manager.load_from_disk() or {}
        plugin_overrides = (((loaded_state.get('platform') or {}).get('preferences') or {}).get('plugins') or {}).get('enabled', {}) if isinstance(loaded_state, dict) else {}
        self._plugin_enablement_overrides = dict(plugin_overrides or {})

        plugin_manager.set_enabled_overrides(self._plugin_enablement_overrides)

        self.plugin_loader = PluginLoader(
            plugin_manager=plugin_manager,
            data_store=self.data_store,
            enabled_overrides=self._plugin_enablement_overrides,
        )
        self.plugin_loader.discover_and_load()

        self._publish_platform_state_taxonomy()
        super().__init__(workspace_manager, plugin_manager=plugin_manager, session_manager=self.session_manager, is_primary=True)
        self.plugin_context = plugin_context
        self.setObjectName('WorkspaceMainWindow')
        self.apply_theme(self.current_theme_name)
        self.statusbar.showMessage('Nexus Core ready', 2000)
        self.resize(1400, 900)
        self.setMinimumSize(1000, 700)
        restored = self.restore_persisted_state(preloaded_state=loaded_state)
        if not restored:
            self._center_on_screen()
        QtCore.QTimer.singleShot(0, self._refresh_restored_theme)
        self.refresh_window_title()

    def plugin_records(self):
        if self.plugin_loader is None:
            return []
        return [record.to_dict() for record in self.plugin_loader.records]

    def set_plugin_enablement_overrides(self, overrides=None):
        self._plugin_enablement_overrides = dict(overrides or {})
        if self.plugin_manager is not None:
            self.plugin_manager.set_enabled_overrides(self._plugin_enablement_overrides)
        if self.plugin_loader is not None:
            self.plugin_loader.enabled_overrides = dict(self._plugin_enablement_overrides)
            self.plugin_loader._publish_state()

    def _publish_platform_state_taxonomy(self):
        try:
            self.data_store.set('platform.state_taxonomy', build_state_taxonomy())
        except Exception:
            pass

    def _refresh_restored_theme(self):
        self.apply_theme(self.current_theme_name)
        for window in list(self.workspace_manager._windows):
            if window is self:
                continue
            try:
                window.apply_theme(getattr(window, 'current_theme_name', self.current_theme_name))
            except Exception:
                pass

    def _center_on_screen(self):
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is None:
            return
        available = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(available.center())
        self.move(frame.topLeft())

    def create_detached_workspace_window(self):
        return self.workspace_manager.create_workspace_window(
            plugin_manager=self.plugin_manager,
            theme_name=self.current_theme_name,
            is_primary=False,
        )

    def restore_persisted_state(self, preloaded_state=None):
        state = preloaded_state if preloaded_state is not None else self.state_manager.load_from_disk()
        if not state:
            return False
        preferences = ((state.get('platform') or {}).get('preferences') or {}) if isinstance(state, dict) else {}
        shortcut_bindings = (((preferences.get('shortcuts') or {}).get('bindings') or {}) if isinstance(preferences, dict) else {})
        recent_entries = (((preferences.get('recent') or {}).get('entries') or []) if isinstance(preferences, dict) else [])
        plugin_overrides = (((preferences.get('plugins') or {}).get('enabled') or {}) if isinstance(preferences, dict) else {})
        try:
            self.plugin_context.set_shortcut_bindings(shortcut_bindings)
        except Exception:
            pass
        self._recent_entries = list(recent_entries or [])
        self._plugin_enablement_overrides = dict(plugin_overrides or self._plugin_enablement_overrides)
        restored = self.state_manager.restore_workspace_state(self, state)
        if restored:
            self.refresh_command_bindings()
            self.statusbar.showMessage('Restored previous workspace', 3000)
        return restored