# ============================================================================
# Nexus
# File: nexus_workspace/graph_editor/geometry.py
# Description: Shared geometry coercion helpers for Qt boundary calls.
# Part of: Nexus Core shared graph framework
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# ============================================================================

"""Geometry helpers for the shared graph framework.

Graph/layout math should remain float-friendly.  Newer PyQt/SIP builds are
strict about QWidget and integer-pixel overloads, so convert at Qt boundaries
instead of relying on implicit float-to-int casts.
"""

from nexus_workspace.framework.qt import QtCore


def px(value, default=0):
    """Return a rounded integer pixel value."""
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return int(default)


def qpoint(value_or_x=0, y=None):
    """Return a QPoint from QPoint, QPointF, point-like object, or x/y."""
    if y is None:
        value = value_or_x
        if isinstance(value, QtCore.QPoint):
            return QtCore.QPoint(value)
        if isinstance(value, QtCore.QPointF):
            return QtCore.QPoint(px(value.x()), px(value.y()))
        if hasattr(value, "x") and hasattr(value, "y"):
            return QtCore.QPoint(px(value.x()), px(value.y()))
        return QtCore.QPoint(px(value), 0)
    return QtCore.QPoint(px(value_or_x), px(y))


def qrect(value_or_x=0, y=None, w=None, h=None):
    """Return a QRect from QRect, QRectF, rect-like object, or x/y/w/h."""
    if y is None and w is None and h is None:
        value = value_or_x
        if isinstance(value, QtCore.QRect):
            return QtCore.QRect(value)
        if isinstance(value, QtCore.QRectF):
            return value.toAlignedRect()
        if hasattr(value, "toRect"):
            return QtCore.QRect(value.toRect())
        return QtCore.QRect()
    return QtCore.QRect(px(value_or_x), px(y), px(w), px(h))
