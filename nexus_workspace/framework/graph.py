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
# File: graph.py
# Description: Implements generic graph editing models, widgets, and interaction helpers.
#============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from PyQt5 import QtCore, QtGui, QtWidgets


@dataclass
class GraphPortDefinition:
    port_id: str
    display_name: str
    direction: str = 'in'
    data_type: str = 'any'
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'port_id': self.port_id,
            'display_name': self.display_name,
            'direction': self.direction,
            'data_type': self.data_type,
            'metadata': dict(self.metadata or {}),
        }


@dataclass
class GraphNodeDefinition:
    node_type_id: str
    display_name: str
    category: str = 'general'
    ports: List[GraphPortDefinition] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'node_type_id': self.node_type_id,
            'display_name': self.display_name,
            'category': self.category,
            'ports': [port.to_dict() for port in self.ports],
            'metadata': dict(self.metadata or {}),
        }


@dataclass
class GraphDomainRegistration:
    domain_id: str
    display_name: str
    plugin_id: str
    description: str = ''
    document_type: str = ''
    file_extension: str = ''
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'domain_id': self.domain_id,
            'display_name': self.display_name,
            'plugin_id': self.plugin_id,
            'description': self.description,
            'document_type': self.document_type,
            'file_extension': self.file_extension,
            'metadata': dict(self.metadata or {}),
        }


@dataclass
class GraphNodeRecord:
    node_id: str
    node_type_id: str
    title: str = ''
    x: float = 0.0
    y: float = 0.0
    properties: Dict[str, object] = field(default_factory=dict)
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'node_id': self.node_id,
            'node_type_id': self.node_type_id,
            'title': self.title,
            'x': self.x,
            'y': self.y,
            'properties': dict(self.properties or {}),
            'metadata': dict(self.metadata or {}),
        }


@dataclass
class GraphEdgeRecord:
    edge_id: str
    source_node_id: str
    source_port_id: str
    target_node_id: str
    target_port_id: str
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'edge_id': self.edge_id,
            'source_node_id': self.source_node_id,
            'source_port_id': self.source_port_id,
            'target_node_id': self.target_node_id,
            'target_port_id': self.target_port_id,
            'metadata': dict(self.metadata or {}),
        }


@dataclass
class GraphDocumentModel:
    schema: str = 'platform.graph.document.v1'
    document_id: str = ''
    domain_id: str = ''
    display_name: str = ''
    nodes: List[GraphNodeRecord] = field(default_factory=list)
    edges: List[GraphEdgeRecord] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self):
        return {
            'schema': self.schema,
            'document_id': self.document_id,
            'domain_id': self.domain_id,
            'display_name': self.display_name,
            'nodes': [node.to_dict() for node in self.nodes],
            'edges': [edge.to_dict() for edge in self.edges],
            'metadata': dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(cls, payload: Optional[Dict[str, object]]):
        source = payload if isinstance(payload, dict) else {}
        nodes = []
        for entry in source.get('nodes', []) or []:
            if not isinstance(entry, dict):
                continue
            nodes.append(GraphNodeRecord(
                node_id=str(entry.get('node_id') or ''),
                node_type_id=str(entry.get('node_type_id') or 'node'),
                title=str(entry.get('title') or ''),
                x=float(entry.get('x') or 0.0),
                y=float(entry.get('y') or 0.0),
                properties=dict(entry.get('properties') or {}),
                metadata=dict(entry.get('metadata') or {}),
            ))
        edges = []
        for entry in source.get('edges', []) or []:
            if not isinstance(entry, dict):
                continue
            edges.append(GraphEdgeRecord(
                edge_id=str(entry.get('edge_id') or ''),
                source_node_id=str(entry.get('source_node_id') or ''),
                source_port_id=str(entry.get('source_port_id') or ''),
                target_node_id=str(entry.get('target_node_id') or ''),
                target_port_id=str(entry.get('target_port_id') or ''),
                metadata=dict(entry.get('metadata') or {}),
            ))
        return cls(
            schema=str(source.get('schema') or 'platform.graph.document.v1'),
            document_id=str(source.get('document_id') or ''),
            domain_id=str(source.get('domain_id') or ''),
            display_name=str(source.get('display_name') or ''),
            nodes=nodes,
            edges=edges,
            metadata=dict(source.get('metadata') or {}),
        )


class NexusGraphService:
    """Shared registry for graph-capable domains."""

    def __init__(self, data_store=None):
        self.data_store = data_store
        self._domains: Dict[str, GraphDomainRegistration] = {}
        self._node_definitions: Dict[str, List[GraphNodeDefinition]] = {}

    def register_domain(self, registration: GraphDomainRegistration):
        self._domains[registration.domain_id] = registration
        self._publish()
        return registration

    def register_node_definitions(self, domain_id: str, definitions: List[GraphNodeDefinition]):
        self._node_definitions[domain_id] = list(definitions or [])
        self._publish()

    def snapshot(self):
        return {
            'contract': 'platform.graph_registry.v1',
            'domains': [self._domains[key].to_dict() for key in sorted(self._domains.keys())],
            'node_definitions': {
                key: [definition.to_dict() for definition in self._node_definitions.get(key, [])]
                for key in sorted(self._node_definitions.keys())
            },
        }

    def _publish(self):
        if self.data_store is None:
            return
        try:
            snapshot = self.snapshot()
            self.data_store.set('platform.graph_registry', snapshot)
            self.data_store.set('platform.graph_domains', snapshot.get('domains', []))
        except Exception:
            pass


class _SimpleGraphNodeItem(QtWidgets.QGraphicsRectItem):
    WIDTH = 160.0
    HEIGHT = 58.0

    def __init__(self, record: GraphNodeRecord, moved_callback=None):
        super().__init__(0.0, 0.0, self.WIDTH, self.HEIGHT)
        self.record = record
        self.moved_callback = moved_callback
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setBrush(QtGui.QBrush(QtGui.QColor('#202734')))
        self.setPen(QtGui.QPen(QtGui.QColor('#53657d'), 1.4))
        self.title_item = QtWidgets.QGraphicsSimpleTextItem(self)
        self.title_item.setBrush(QtGui.QBrush(QtGui.QColor('#eaf0ff')))
        title_font = QtGui.QFont()
        title_font.setPointSize(9)
        title_font.setBold(True)
        self.title_item.setFont(title_font)
        self.subtitle_item = QtWidgets.QGraphicsSimpleTextItem(self)
        self.subtitle_item.setBrush(QtGui.QBrush(QtGui.QColor('#9db1cc')))
        subtitle_font = QtGui.QFont()
        subtitle_font.setPointSize(8)
        self.subtitle_item.setFont(subtitle_font)
        self.refresh_text()
        self.setPos(float(record.x or 0.0), float(record.y or 0.0))

    def refresh_text(self):
        self.title_item.setText(self.record.title or self.record.node_id or 'Node')
        self.subtitle_item.setText(self.record.node_type_id or 'node')
        self.title_item.setPos(10.0, 8.0)
        self.subtitle_item.setPos(10.0, 30.0)

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemPositionHasChanged:
            pos = value
            self.record.x = float(pos.x())
            self.record.y = float(pos.y())
            if callable(self.moved_callback):
                self.moved_callback(self)
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            selected = bool(value)
            self.setBrush(QtGui.QBrush(QtGui.QColor('#2a3950' if selected else '#202734')))
            self.setPen(QtGui.QPen(QtGui.QColor('#8fb7ff' if selected else '#53657d'), 1.8 if selected else 1.4))
        return super().itemChange(change, value)


class _SimpleGraphEdgeItem(QtWidgets.QGraphicsPathItem):
    def __init__(self, edge: GraphEdgeRecord, source_item: _SimpleGraphNodeItem, target_item: _SimpleGraphNodeItem):
        super().__init__()
        self.edge = edge
        self.source_item = source_item
        self.target_item = target_item
        self.setPen(QtGui.QPen(QtGui.QColor('#6b86a9'), 2.0))
        self.setZValue(-10.0)
        self.label_item = QtWidgets.QGraphicsSimpleTextItem(self)
        self.label_item.setBrush(QtGui.QBrush(QtGui.QColor('#a8bad6')))
        self.update_position()

    def update_position(self):
        if self.source_item is None or self.target_item is None:
            self.setPath(QtGui.QPainterPath())
            return
        src_rect = self.source_item.sceneBoundingRect()
        dst_rect = self.target_item.sceneBoundingRect()
        src = QtCore.QPointF(src_rect.right(), src_rect.center().y())
        dst = QtCore.QPointF(dst_rect.left(), dst_rect.center().y())
        dx = max(40.0, abs(dst.x() - src.x()) * 0.45)
        path = QtGui.QPainterPath(src)
        path.cubicTo(src.x() + dx, src.y(), dst.x() - dx, dst.y(), dst.x(), dst.y())
        self.setPath(path)
        label = str(self.edge.metadata.get('label') or self.edge.metadata.get('message_name') or '')
        self.label_item.setText(label)
        if label:
            mid = path.pointAtPercent(0.5)
            self.label_item.setPos(mid.x() + 6.0, mid.y() - 16.0)
        else:
            self.label_item.setPos(-10000.0, -10000.0)


class NexusSimpleGraphCanvas(QtWidgets.QWidget):
    nodeSelected = QtCore.pyqtSignal(str)
    nodeMoved = QtCore.pyqtSignal(str, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.scene = QtWidgets.QGraphicsScene(self)
        self.view = QtWidgets.QGraphicsView(self.scene, self)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.view.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        self.view.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self.view.setBackgroundBrush(QtGui.QBrush(QtGui.QColor('#151c26')))
        layout.addWidget(self.view, 1)
        self._graph_document = GraphDocumentModel()
        self._node_items: Dict[str, _SimpleGraphNodeItem] = {}
        self._edge_items: List[_SimpleGraphEdgeItem] = []
        self.scene.selectionChanged.connect(self._on_scene_selection_changed)

    def graph_document(self) -> GraphDocumentModel:
        return self._graph_document

    def set_graph_document(self, graph_document: Optional[Dict[str, object]] = None):
        if isinstance(graph_document, GraphDocumentModel):
            self._graph_document = graph_document
        else:
            self._graph_document = GraphDocumentModel.from_dict(graph_document)
        self._rebuild_scene()

    def refresh(self):
        self._rebuild_scene()

    def select_node(self, node_id: str):
        node = self._node_items.get(str(node_id or ''))
        if node is None:
            self.scene.clearSelection()
            return
        self.scene.blockSignals(True)
        self.scene.clearSelection()
        node.setSelected(True)
        self.scene.blockSignals(False)
        self.view.centerOn(node)

    def _rebuild_scene(self):
        self.scene.clear()
        self._node_items = {}
        self._edge_items = []
        for node in self._graph_document.nodes:
            item = _SimpleGraphNodeItem(node, moved_callback=self._on_node_item_moved)
            self.scene.addItem(item)
            self._node_items[node.node_id] = item
        for edge in self._graph_document.edges:
            source_item = self._node_items.get(edge.source_node_id)
            target_item = self._node_items.get(edge.target_node_id)
            if source_item is None or target_item is None:
                continue
            edge_item = _SimpleGraphEdgeItem(edge, source_item, target_item)
            self.scene.addItem(edge_item)
            self._edge_items.append(edge_item)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-120.0, -120.0, 120.0, 120.0))

    def _on_node_item_moved(self, _item):
        for edge_item in self._edge_items:
            edge_item.update_position()
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-120.0, -120.0, 120.0, 120.0))
        selected = self.selected_node_id()
        if selected:
            node = self._node_items.get(selected)
            if node is not None:
                self.nodeMoved.emit(selected, float(node.record.x), float(node.record.y))

    def _on_scene_selection_changed(self):
        self.nodeSelected.emit(self.selected_node_id())

    def selected_node_id(self) -> str:
        for item in self.scene.selectedItems():
            if isinstance(item, _SimpleGraphNodeItem):
                return str(item.record.node_id or '')
        return ''
