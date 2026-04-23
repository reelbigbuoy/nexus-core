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
# File: charts.py
# Description: Defines Nexus chart wrappers with graceful fallback when Qt chart modules are unavailable.
#============================================================================

from __future__ import annotations

from typing import Iterable, Sequence, Tuple

from PyQt5 import QtCore, QtWidgets

try:
    from PyQt5 import QtChart as _QtChartModule
except Exception:
    try:
        from PyQt5 import QtCharts as _QtChartModule
    except Exception:
        _QtChartModule = None


class _ChartFallback(QtWidgets.QFrame):
    def __init__(self, parent=None, *, object_name='NexusChartFallback'):
        super().__init__(parent)
        self.setObjectName(object_name)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self._label = QtWidgets.QLabel('Qt chart support is not available in this runtime.', self)
        self._label.setWordWrap(True)
        layout.addWidget(self._label)
        layout.addStretch(1)

    def set_message(self, message: str):
        self._label.setText(str(message or ''))


if _QtChartModule is not None:
    _ChartViewBase = _QtChartModule.QChartView
    _Chart = _QtChartModule.QChart
    _BarSeries = _QtChartModule.QBarSeries
    _BarSet = _QtChartModule.QBarSet
    _PieSeries = _QtChartModule.QPieSeries
    _LineSeries = _QtChartModule.QLineSeries
    _ValueAxis = _QtChartModule.QValueAxis
    _BarCategoryAxis = _QtChartModule.QBarCategoryAxis
else:
    _ChartViewBase = _ChartFallback
    _Chart = None
    _BarSeries = None
    _BarSet = None
    _PieSeries = None
    _LineSeries = None
    _ValueAxis = None
    _BarCategoryAxis = None


class NexusChartView(_ChartViewBase):
    """Base chart view wrapper for Nexus chart surfaces."""

    def __init__(self, parent=None, *, object_name='NexusChartView', title=''):
        if _QtChartModule is None:
            super().__init__(parent, object_name=object_name)
            self.set_message('Qt chart support is not available in this runtime.')
            return
        chart = _Chart()
        chart.setTitle(str(title or ''))
        super().__init__(chart, parent)
        self.setObjectName(object_name)
        from PyQt5 import QtGui
        self.setRenderHint(QtGui.QPainter.Antialiasing)

    def chart_object(self):
        if _QtChartModule is None:
            return None
        return self.chart()

    def set_chart_title(self, title: str):
        chart = self.chart_object()
        if chart is not None:
            chart.setTitle(str(title or ''))


class NexusBarChartView(NexusChartView):
    def __init__(self, parent=None, *, object_name='NexusBarChartView', title=''):
        super().__init__(parent, object_name=object_name, title=title)

    def set_series_data(self, categories: Sequence[str], values: Iterable[float], *, series_name='Series'):
        chart = self.chart_object()
        if chart is None:
            self.set_message('Bar chart requested, but Qt chart support is not available in this runtime.')
            return
        chart.removeAllSeries()
        series = _BarSeries()
        bar_set = _BarSet(str(series_name or 'Series'))
        for value in values or []:
            bar_set.append(float(value))
        series.append(bar_set)
        chart.addSeries(series)
        axis_x = _BarCategoryAxis()
        axis_x.append([str(item) for item in categories or []])
        axis_y = _ValueAxis()
        chart.createDefaultAxes()
        chart.setAxisX(axis_x, series)
        chart.setAxisY(axis_y, series)


class NexusPieChartView(NexusChartView):
    def __init__(self, parent=None, *, object_name='NexusPieChartView', title=''):
        super().__init__(parent, object_name=object_name, title=title)

    def set_series_data(self, slices: Iterable[Tuple[str, float]]):
        chart = self.chart_object()
        if chart is None:
            self.set_message('Pie chart requested, but Qt chart support is not available in this runtime.')
            return
        chart.removeAllSeries()
        series = _PieSeries()
        for label, value in slices or []:
            series.append(str(label), float(value))
        chart.addSeries(series)


class NexusLineChartView(NexusChartView):
    def __init__(self, parent=None, *, object_name='NexusLineChartView', title=''):
        super().__init__(parent, object_name=object_name, title=title)

    def set_series_data(self, points: Iterable[Tuple[float, float]], *, series_name='Series'):
        chart = self.chart_object()
        if chart is None:
            self.set_message('Line chart requested, but Qt chart support is not available in this runtime.')
            return
        chart.removeAllSeries()
        series = _LineSeries()
        series.setName(str(series_name or 'Series'))
        for x_value, y_value in points or []:
            series.append(float(x_value), float(y_value))
        chart.addSeries(series)
        chart.createDefaultAxes()


__all__ = [
    'NexusBarChartView',
    'NexusChartView',
    'NexusLineChartView',
    'NexusPieChartView',
]
