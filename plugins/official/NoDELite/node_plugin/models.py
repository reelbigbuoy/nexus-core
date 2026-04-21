# ============================================================================
# Nexus
# File: plugins/owner/NoDE/node_plugin/models.py
# Description: Source module for node plugin functionality.
# Part of: NoDE Plugin
# Copyright (c) 2026 Reel Big Buoy Company
# All rights reserved.
# Proprietary and confidential.
# See the LICENSE file in the NoDE repository root for license terms.
# ============================================================================

from PyQt5.QtCore import QPointF


class GraphConnectionData:
    def __init__(self, source_node_id, source_port_name, target_node_id, target_port_name, route_points=None, connection_kind=None):
        self.source_node_id = source_node_id
        self.source_port_name = source_port_name
        self.target_node_id = target_node_id
        self.target_port_name = target_port_name
        self.route_points = [QPointF(p) for p in (route_points or [])]
        self.connection_kind = connection_kind

    def copy(self):
        return GraphConnectionData(
            self.source_node_id,
            self.source_port_name,
            self.target_node_id,
            self.target_port_name,
            [QPointF(p) for p in self.route_points],
            self.connection_kind,
        )

    def to_dict(self):
        return {
            "source_node_id": self.source_node_id,
            "source_port_name": self.source_port_name,
            "target_node_id": self.target_node_id,
            "target_port_name": self.target_port_name,
            "route_points": [(p.x(), p.y()) for p in self.route_points],
            "connection_kind": self.connection_kind,
        }

    @classmethod
    def from_dict(cls, data):
        if isinstance(data, cls):
            return data.copy()
        return cls(
            data["source_node_id"],
            data.get("source_port_name", data.get("source_port")),
            data["target_node_id"],
            data.get("target_port_name", data.get("target_port")),
            [QPointF(x, y) for x, y in data.get("route_points", [])],
            data.get("connection_kind"),
        )
