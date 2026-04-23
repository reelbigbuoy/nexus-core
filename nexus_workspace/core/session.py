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
# File: session.py
# Description: Manages session-scoped state and runtime data for the active application session.
#============================================================================

from nexus_workspace.framework.qt import QtWidgets


class SessionManager:
    """Coordinates multi-workspace lifecycle and application shutdown."""

    def __init__(self, workspace_manager=None, state_manager=None):
        self.workspace_manager = workspace_manager
        self.state_manager = state_manager
        self._is_shutting_down = False

    @property
    def is_shutting_down(self):
        return self._is_shutting_down

    def windows(self):
        if self.workspace_manager is None:
            return []
        return list(getattr(self.workspace_manager, '_windows', []))

    def primary_window(self):
        for window in self.windows():
            if getattr(window, 'is_primary', False):
                return window
        windows = self.windows()
        return windows[0] if windows else None

    def prepare_shutdown(self, anchor_window=None):
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        anchor = anchor_window or self.primary_window()
        if anchor is not None and self.state_manager is not None:
            try:
                self.state_manager.save_to_disk(anchor)
            except Exception:
                pass

    def shutdown_application(self, anchor_window=None):
        if self.workspace_manager is None:
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.quit()
            return
        self.prepare_shutdown(anchor_window=anchor_window)
        for window in list(self.windows()):
            try:
                window.close()
            except Exception:
                pass
        app = QtWidgets.QApplication.instance()
        if app is not None and not self.windows():
            app.quit()

    def should_allow_window_close(self, window):
        if self._is_shutting_down:
            return True
        if len(self.windows()) <= 1:
            self.prepare_shutdown(anchor_window=window)
        return True

    def on_window_closed(self, window):
        if self.workspace_manager is not None:
            self.workspace_manager.unregister_window(window)
        if self.workspace_manager is not None:
            self.workspace_manager.promote_primary_window()

        if not self._is_shutting_down:
            anchor = self.primary_window()
            if anchor is not None and self.state_manager is not None:
                try:
                    self.state_manager.save_to_disk(anchor)
                except Exception:
                    pass

        if self._is_shutting_down and not self.windows():
            app = QtWidgets.QApplication.instance()
            if app is not None:
                app.quit()