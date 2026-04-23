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
# File: qt.py
# Description: Central Qt compatibility bridge for code outside the framework wrappers.
#============================================================================

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

try:
    from PyQt5 import QtChart as QtChart
except Exception:  # pragma: no cover
    try:
        from PyQt5 import QtCharts as QtChart
    except Exception:  # pragma: no cover
        QtChart = None

Signal = QtCore.pyqtSignal
Slot = QtCore.pyqtSlot
Property = QtCore.pyqtProperty

__all__ = [
    'QtCore',
    'QtGui',
    'QtWidgets',
    'QtChart',
    'Signal',
    'Slot',
    'Property',
]
