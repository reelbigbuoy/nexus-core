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
# File: nexus.py
# Description: Application entry point that launches the Nexus Core workspace.
#============================================================================

import sys
from pathlib import Path
from PyQt5 import QtGui, QtWidgets
from nexus_workspace.runtime.dev_validation import run_startup_validation


def main():
    project_root = Path(__file__).resolve().parent
    report = run_startup_validation(project_root)
    if report.enabled:
        print(report.format_console())
    from nexus_workspace.workspace.main_window import WorkspaceMainWindow

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Nexus")
    icon_path = Path(__file__).resolve().parent / "nexus_workspace" / "assets" / "icons" / "nexus_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QtGui.QIcon(str(icon_path)))
    window = WorkspaceMainWindow()
    window.refresh_window_title()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
