from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from nexus_workspace.framework.qt import QtCore, QtGui, QtWidgets


COMMON_DATA_TYPES = [
    'any', 'bool', 'int', 'float', 'double', 'string', 'char', 'bytes',
    'list', 'dict', 'set', 'tuple', 'object', 'enum', 'node',
]


class NodePreviewWidget(QtWidgets.QGraphicsView):
    def __init__(self, parent=None):
        scene = QtWidgets.QGraphicsScene()
        super().__init__(scene, parent)
        self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self.setMinimumHeight(170)
        self.setMaximumHeight(220)
        self.setSceneRect(0, 0, 320, 180)
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.refresh('Node', [], [])

    def refresh(self, title: str, inputs: List[dict], outputs: List[dict]):
        scene = self.scene()
        scene.clear()
        scene.setSceneRect(0, 0, 320, 180)

        width = 190
        port_gap = 24
        count = max(2, len(inputs), len(outputs))
        height = max(84, 42 + count * port_gap)
        x = 65
        y = max(16, (180 - height) / 2)

        rect = QtCore.QRectF(x, y, width, height)
        body_pen = QtGui.QPen(QtGui.QColor(120, 140, 175))
        body_pen.setWidth(2)
        body_brush = QtGui.QBrush(QtGui.QColor(42, 50, 67))
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        scene.addPath(path, body_pen, body_brush)

        header_rect = QtCore.QRectF(x, y, width, 34)
        path = QtGui.QPainterPath()
        path.addRoundedRect(header_rect, 14, 14)
        scene.addPath(path, QtGui.QPen(QtCore.Qt.NoPen), QtGui.QBrush(QtGui.QColor(64,90,132)))
        title_item = scene.addText(title or 'Node')
        title_item.setDefaultTextColor(QtGui.QColor('white'))
        font = title_item.font()
        font.setBold(True)
        font.setPointSize(max(font.pointSize(), 10))
        title_item.setFont(font)
        title_item.setPos(x + 12, y + 6)

        def draw_ports(port_list: List[dict], left_side: bool):
            for index, port in enumerate(port_list[:5]):
                py = y + 48 + index * port_gap
                px = x if left_side else x + width
                pin_kind = str(port.get('connection_kind') or ('data' if port.get('data_type') != 'exec' else 'exec')).lower()
                color = QtGui.QColor(243, 180, 77) if pin_kind == 'exec' else QtGui.QColor(86, 188, 255)
                scene.addEllipse(px - 5, py - 5, 10, 10, QtGui.QPen(QtCore.Qt.NoPen), QtGui.QBrush(color))
                label = str(port.get('name') or 'Port')
                text_item = scene.addText(label)
                text_item.setDefaultTextColor(QtGui.QColor(228, 232, 238))
                text_item.setScale(0.9)
                if left_side:
                    text_item.setPos(px + 10, py - 10)
                else:
                    br = text_item.boundingRect()
                    text_item.setPos(px - br.width() * 0.9 - 12, py - 10)

        draw_ports(inputs, True)
        draw_ports(outputs, False)
        self.fitInView(scene.sceneRect(), QtCore.Qt.KeepAspectRatio)


class PortTable(QtWidgets.QTableWidget):
    headers = ['Name', 'Direction', 'Pin Kind', 'Data Type', 'Multi', 'Required']

    def __init__(self, parent=None, data_type_options=None):
        super().__init__(0, len(self.headers), parent)
        self._data_type_options = list(data_type_options or COMMON_DATA_TYPES)
        self.setHorizontalHeaderLabels(self.headers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        for col in (1, 2, 3):
            self.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)

    def add_port_row(self, *, name='', direction='input', pin_kind='data', data_type='any', multi=False, required=False):
        row = self.rowCount()
        self.insertRow(row)
        self.setItem(row, 0, QtWidgets.QTableWidgetItem(name))

        direction_combo = QtWidgets.QComboBox(self)
        direction_combo.addItems(['input', 'output'])
        direction_combo.setCurrentText(direction)
        self.setCellWidget(row, 1, direction_combo)

        pin_combo = QtWidgets.QComboBox(self)
        pin_combo.addItems(['data', 'exec'])
        pin_combo.setCurrentText(pin_kind)
        self.setCellWidget(row, 2, pin_combo)

        data_type_combo = QtWidgets.QComboBox(self)
        data_type_combo.setEditable(True)
        data_type_combo.addItems(self._data_type_options)
        index = data_type_combo.findText(data_type)
        if index >= 0:
            data_type_combo.setCurrentIndex(index)
        else:
            data_type_combo.setEditText(data_type)
        self.setCellWidget(row, 3, data_type_combo)
        owner = self.parent()
        if owner is not None and hasattr(owner, '_update_node_preview'):
            direction_combo.currentTextChanged.connect(owner._update_node_preview)
            pin_combo.currentTextChanged.connect(owner._update_node_preview)
            data_type_combo.currentTextChanged.connect(owner._update_node_preview)

        multi_item = QtWidgets.QTableWidgetItem()
        multi_item.setFlags(multi_item.flags() | QtCore.Qt.ItemIsUserCheckable)
        multi_item.setCheckState(QtCore.Qt.Checked if multi else QtCore.Qt.Unchecked)
        self.setItem(row, 4, multi_item)

        req_item = QtWidgets.QTableWidgetItem()
        req_item.setFlags(req_item.flags() | QtCore.Qt.ItemIsUserCheckable)
        req_item.setCheckState(QtCore.Qt.Checked if required else QtCore.Qt.Unchecked)
        self.setItem(row, 5, req_item)

    def clear_ports(self):
        self.setRowCount(0)

    def port_entries(self) -> List[dict]:
        entries = []
        for row in range(self.rowCount()):
            name_item = self.item(row, 0)
            data_type_widget = self.cellWidget(row, 3)
            multi_item = self.item(row, 4)
            req_item = self.item(row, 5)
            name = (name_item.text().strip() if name_item else '')
            if not name:
                continue
            direction_widget = self.cellWidget(row, 1)
            kind_widget = self.cellWidget(row, 2)
            direction = direction_widget.currentText() if direction_widget else 'input'
            pin_kind = kind_widget.currentText() if kind_widget else 'data'
            data_type = (data_type_widget.currentText().strip() if data_type_widget and data_type_widget.currentText().strip() else ('exec' if pin_kind == 'exec' else 'any'))
            entries.append({
                'id': self._stable_id(name),
                'name': name,
                'direction': direction,
                'data_type': data_type,
                'connection_kind': pin_kind,
                'multi_connection': bool(multi_item and multi_item.checkState() == QtCore.Qt.Checked),
                'required': bool(req_item and req_item.checkState() == QtCore.Qt.Checked),
            })
        return entries

    @staticmethod
    def _stable_id(name: str) -> str:
        return re.sub(r'[^a-z0-9_]+', '_', name.strip().lower().replace(' ', '_')).strip('_') or 'port'


class NoDEViewBuilderTool(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_plugin_root = self._discover_target_plugin_root()
        self._views_by_id: Dict[str, dict] = {}
        self._nodes_by_type: Dict[str, dict] = {}
        self._current_view_id: Optional[str] = None
        self._current_node_type_id: Optional[str] = None
        self._suspend_preview = False

        self._build_ui()
        self._load_from_disk(select_first=True)

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        target_group = QtWidgets.QGroupBox('Target')
        target_layout = QtWidgets.QVBoxLayout(target_group)
        self.targetLabel = QtWidgets.QLabel(self)
        self.targetLabel.setWordWrap(True)
        self.targetLabel.setText(self._target_label_text())
        target_layout.addWidget(self.targetLabel)
        root.addWidget(target_group)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        root.addWidget(splitter, 1)

        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        view_group = QtWidgets.QGroupBox('Views')
        view_layout = QtWidgets.QVBoxLayout(view_group)
        self.viewList = QtWidgets.QListWidget()
        self.viewList.currentItemChanged.connect(self._on_view_selected)
        view_layout.addWidget(self.viewList, 1)
        view_btns = QtWidgets.QHBoxLayout()
        self.btnNewView = QtWidgets.QPushButton('New View')
        self.btnDeleteView = QtWidgets.QPushButton('Delete View')
        self.btnNewView.clicked.connect(self._create_view)
        self.btnDeleteView.clicked.connect(self._delete_current_view)
        view_btns.addWidget(self.btnNewView)
        view_btns.addWidget(self.btnDeleteView)
        view_layout.addLayout(view_btns)
        left_layout.addWidget(view_group, 1)

        node_group = QtWidgets.QGroupBox('Nodes in View')
        node_layout = QtWidgets.QVBoxLayout(node_group)
        self.nodeList = QtWidgets.QListWidget()
        self.nodeList.currentItemChanged.connect(self._on_node_selected)
        node_layout.addWidget(self.nodeList, 1)
        node_btns = QtWidgets.QHBoxLayout()
        self.btnNewNode = QtWidgets.QPushButton('New Node')
        self.btnDeleteNode = QtWidgets.QPushButton('Delete Node')
        self.btnNewNode.clicked.connect(self._create_node)
        self.btnDeleteNode.clicked.connect(self._delete_current_node)
        node_btns.addWidget(self.btnNewNode)
        node_btns.addWidget(self.btnDeleteNode)
        node_layout.addLayout(node_btns)
        left_layout.addWidget(node_group, 1)

        splitter.addWidget(left_panel)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        view_detail_group = QtWidgets.QGroupBox('View Details')
        view_detail_layout = QtWidgets.QVBoxLayout(view_detail_group)
        view_form = QtWidgets.QFormLayout()
        self.viewNameEdit = QtWidgets.QLineEdit()
        self.viewDescEdit = QtWidgets.QLineEdit()
        self.viewDefaultCheck = QtWidgets.QCheckBox('Default view')
        view_form.addRow('Name', self.viewNameEdit)
        view_form.addRow('Description', self.viewDescEdit)
        view_form.addRow('', self.viewDefaultCheck)
        view_detail_layout.addLayout(view_form)

        category_label_row = QtWidgets.QHBoxLayout()
        category_label = QtWidgets.QLabel('Categories for this view')
        category_label_row.addWidget(category_label)
        category_label_row.addStretch(1)
        view_detail_layout.addLayout(category_label_row)

        self.categoryList = QtWidgets.QListWidget()
        self.categoryList.itemSelectionChanged.connect(self._sync_category_buttons)
        view_detail_layout.addWidget(self.categoryList, 1)
        category_btns = QtWidgets.QHBoxLayout()
        self.btnAddCategory = QtWidgets.QPushButton('Add')
        self.btnRenameCategory = QtWidgets.QPushButton('Rename')
        self.btnDeleteCategory = QtWidgets.QPushButton('Delete')
        self.btnAddCategory.clicked.connect(self._add_category)
        self.btnRenameCategory.clicked.connect(self._rename_category)
        self.btnDeleteCategory.clicked.connect(self._delete_category)
        category_btns.addWidget(self.btnAddCategory)
        category_btns.addWidget(self.btnRenameCategory)
        category_btns.addWidget(self.btnDeleteCategory)
        category_btns.addStretch(1)
        view_detail_layout.addLayout(category_btns)
        self.btnSaveView = QtWidgets.QPushButton('Save View')
        self.btnSaveView.clicked.connect(self._save_current_view)
        view_detail_layout.addWidget(self.btnSaveView, 0, QtCore.Qt.AlignLeft)
        right_layout.addWidget(view_detail_group, 1)

        node_detail_group = QtWidgets.QGroupBox('Node Details')
        node_detail_layout = QtWidgets.QVBoxLayout(node_detail_group)
        node_form = QtWidgets.QFormLayout()
        self.nodeNameEdit = QtWidgets.QLineEdit()
        self.categoryCombo = QtWidgets.QComboBox()
        self.nodeDescEdit = QtWidgets.QLineEdit()
        self.nodeKindCombo = QtWidgets.QComboBox()
        self.nodeKindCombo.addItems(['execution', 'data', 'graph'])
        self.nodeDataTypeEdit = QtWidgets.QComboBox()
        self.nodeDataTypeEdit.setEditable(True)
        self.nodeDataTypeEdit.addItems(COMMON_DATA_TYPES)
        self.nodeDataTypeEdit.setCurrentText('any')
        self.nodeGraphPathEdit = QtWidgets.QLineEdit()
        self.nodeGraphPathEdit.setReadOnly(True)
        self.nodeGraphPathEdit.setPlaceholderText('Auto-generated for graph nodes')
        node_form.addRow('Name', self.nodeNameEdit)
        node_form.addRow('Category', self.categoryCombo)
        node_form.addRow('Description', self.nodeDescEdit)
        node_form.addRow('Node Type', self.nodeKindCombo)
        node_form.addRow('Data Type', self.nodeDataTypeEdit)
        node_form.addRow('Owned Graph', self.nodeGraphPathEdit)
        node_detail_layout.addLayout(node_form)

        preview_label = QtWidgets.QLabel('Node Preview')
        node_detail_layout.addWidget(preview_label)
        self.nodePreview = NodePreviewWidget(self)
        node_detail_layout.addWidget(self.nodePreview)

        self.portTable = PortTable(self, data_type_options=COMMON_DATA_TYPES)
        self.portTable.itemChanged.connect(self._update_node_preview)
        self.portTable.model().rowsInserted.connect(lambda *_: self._update_node_preview())
        self.portTable.model().rowsRemoved.connect(lambda *_: self._update_node_preview())
        node_detail_layout.addWidget(self.portTable, 1)

        port_btns = QtWidgets.QHBoxLayout()
        self.btnAddInput = QtWidgets.QPushButton('Add Input')
        self.btnAddOutput = QtWidgets.QPushButton('Add Output')
        self.btnRemovePort = QtWidgets.QPushButton('Remove Port')
        self.btnAddInput.clicked.connect(lambda: self._add_port(direction='input'))
        self.btnAddOutput.clicked.connect(lambda: self._add_port(direction='output'))
        self.btnRemovePort.clicked.connect(self._remove_selected_port)
        port_btns.addWidget(self.btnAddInput)
        port_btns.addWidget(self.btnAddOutput)
        port_btns.addWidget(self.btnRemovePort)
        port_btns.addStretch(1)
        node_detail_layout.addLayout(port_btns)

        self.btnSaveNode = QtWidgets.QPushButton('Save Node')
        self.btnSaveNode.clicked.connect(self._save_current_node)
        node_detail_layout.addWidget(self.btnSaveNode, 0, QtCore.Qt.AlignLeft)
        right_layout.addWidget(node_detail_group, 2)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.logEdit = QtWidgets.QPlainTextEdit(self)
        self.logEdit.setReadOnly(True)
        self.logEdit.setMaximumBlockCount(300)
        root.addWidget(self.logEdit)

        self.viewNameEdit.textEdited.connect(self._refresh_view_list_labels)
        self.nodeNameEdit.textEdited.connect(self._refresh_node_list_labels)
        self.nodeNameEdit.textChanged.connect(self._update_node_preview)
        self.nodeDescEdit.textChanged.connect(self._update_node_preview)
        self.categoryCombo.currentTextChanged.connect(self._update_node_preview)
        self.nodeKindCombo.currentTextChanged.connect(self._on_node_kind_changed)
        self.nodeDataTypeEdit.currentTextChanged.connect(self._update_node_preview)
        self._sync_category_buttons()

    def _target_label_text(self) -> str:
        if self._target_plugin_root is None:
            return 'Target plugin not found automatically. Install this plugin alongside either NoDE or NoDE Lite.'
        return f'Connected directly to: {self._target_plugin_root}'

    def _discover_target_plugin_root(self) -> Optional[Path]:
        current = Path(__file__).resolve()
        plugin_root = current.parents[1]
        parent = plugin_root.parent
        for candidate_name in ('NoDELite', 'NoDE'):
            candidate = parent / candidate_name
            if (candidate / 'node_plugin').exists() and (candidate / 'plugin.json').exists():
                return candidate
        for candidate in parent.iterdir() if parent.exists() else []:
            if candidate.is_dir() and candidate.name != plugin_root.name and (candidate / 'node_plugin').exists() and (candidate / 'plugin.json').exists() and candidate.name.lower().startswith('node'):
                return candidate
        return None

    def _require_target_root(self) -> Path:
        if self._target_plugin_root is None:
            raise ValueError('Could not automatically locate NoDE or NoDE Lite beside this plugin.')
        return self._target_plugin_root

    def _views_dir(self) -> Path:
        return self._require_target_root() / 'node_plugin' / 'node_view_manifests'

    def _defs_dir(self) -> Path:
        return self._require_target_root() / 'node_plugin' / 'node_definitions'

    def _load_from_disk(self, *, select_first: bool = False):
        self._views_by_id.clear()
        self._nodes_by_type.clear()

        views_dir = self._views_dir()
        defs_dir = self._defs_dir()
        if views_dir.exists():
            for path in sorted(views_dir.glob('*.json')):
                data = json.loads(path.read_text(encoding='utf-8'))
                data['_source_path'] = str(path)
                self._views_by_id[data['view_id']] = data
        if defs_dir.exists():
            for path in sorted(defs_dir.rglob('*.json')):
                data = json.loads(path.read_text(encoding='utf-8'))
                data['_source_path'] = str(path)
                self._nodes_by_type[data['type_id']] = data

        self._rebuild_view_list()
        if select_first and self.viewList.count() > 0:
            self.viewList.setCurrentRow(0)
        elif self._current_view_id:
            self._select_view_by_id(self._current_view_id)
        elif self.viewList.count() > 0:
            self.viewList.setCurrentRow(0)
        else:
            self._populate_view_form(None)
            self._rebuild_node_list()
            self._populate_node_form(None)

    def _rebuild_view_list(self):
        current_id = self._current_view_id
        self.viewList.blockSignals(True)
        self.viewList.clear()
        for view in sorted(self._views_by_id.values(), key=lambda item: (0 if item.get('is_default') else 1, str(item.get('name', '')).lower())):
            label = str(view.get('name') or view['view_id'])
            if view.get('is_default'):
                label += ' [default]'
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, view['view_id'])
            self.viewList.addItem(item)
        self.viewList.blockSignals(False)
        if current_id:
            self._select_view_by_id(current_id)

    def _select_view_by_id(self, view_id: Optional[str]):
        if not view_id:
            return
        for row in range(self.viewList.count()):
            item = self.viewList.item(row)
            if item.data(QtCore.Qt.UserRole) == view_id:
                self.viewList.setCurrentRow(row)
                return

    def _rebuild_node_list(self):
        current_type = self._current_node_type_id
        self.nodeList.blockSignals(True)
        self.nodeList.clear()
        view = self._views_by_id.get(self._current_view_id) if self._current_view_id else None
        categories = set(view.get('include_categories', []) if view else [])
        type_ids = set(view.get('include_type_ids', []) if view else [])
        nodes = []
        for node in self._nodes_by_type.values():
            if not view:
                continue
            if node.get('type_id') in type_ids or node.get('category') in categories:
                nodes.append(node)
        for node in sorted(nodes, key=lambda item: (str(item.get('category', '')).lower(), str(item.get('name', '')).lower())):
            item = QtWidgets.QListWidgetItem(f"{node.get('name', node['type_id'])}  ({node.get('category', 'uncategorized')})")
            item.setData(QtCore.Qt.UserRole, node['type_id'])
            self.nodeList.addItem(item)
        self.nodeList.blockSignals(False)
        if current_type:
            self._select_node_by_type(current_type)
        elif self.nodeList.count() > 0:
            self.nodeList.setCurrentRow(0)
        else:
            self._populate_node_form(None)

    def _select_node_by_type(self, type_id: Optional[str]):
        if not type_id:
            return
        for row in range(self.nodeList.count()):
            item = self.nodeList.item(row)
            if item.data(QtCore.Qt.UserRole) == type_id:
                self.nodeList.setCurrentRow(row)
                return

    def _on_view_selected(self, current, previous):
        del previous
        self._current_view_id = current.data(QtCore.Qt.UserRole) if current else None
        self._populate_view_form(self._views_by_id.get(self._current_view_id) if self._current_view_id else None)
        self._rebuild_node_list()
        self._refresh_category_combo()

    def _on_node_selected(self, current, previous):
        del previous
        self._current_node_type_id = current.data(QtCore.Qt.UserRole) if current else None
        self._populate_node_form(self._nodes_by_type.get(self._current_node_type_id) if self._current_node_type_id else None)

    def _populate_view_form(self, view: Optional[dict]):
        self.viewNameEdit.blockSignals(True)
        self.viewDescEdit.blockSignals(True)
        self.viewDefaultCheck.blockSignals(True)
        self.categoryList.clear()
        if view:
            self.viewNameEdit.setText(str(view.get('name', '')))
            self.viewDescEdit.setText(str(view.get('description', '')))
            self.viewDefaultCheck.setChecked(bool(view.get('is_default')))
            for category in view.get('include_categories', []) or []:
                self.categoryList.addItem(str(category))
        else:
            self.viewNameEdit.clear()
            self.viewDescEdit.clear()
            self.viewDefaultCheck.setChecked(False)
        self.viewNameEdit.blockSignals(False)
        self.viewDescEdit.blockSignals(False)
        self.viewDefaultCheck.blockSignals(False)
        self._refresh_category_combo()
        self._sync_category_buttons()

    def _populate_node_form(self, node: Optional[dict]):
        self._suspend_preview = True
        self.nodeNameEdit.clear()
        self.nodeDescEdit.clear()
        self.nodeKindCombo.setCurrentText('execution')
        self.nodeDataTypeEdit.setCurrentText('any')
        self.nodeGraphPathEdit.clear()
        self.portTable.clear_ports()
        self._refresh_category_combo()
        if node:
            self.nodeNameEdit.setText(str(node.get('name', '')))
            self.nodeDescEdit.setText(str(node.get('description', '')))
            category = str(node.get('category', ''))
            metadata = dict(node.get('metadata', {}) or {})
            node_kind = str(metadata.get('node_kind', 'execution') or 'execution').strip().lower()
            if node_kind not in ('execution', 'data'):
                node_kind = 'execution'
            node_data_type = str(metadata.get('node_data_type', '') or '').strip()
            self.nodeKindCombo.setCurrentText(node_kind)
            self.nodeDataTypeEdit.setCurrentText(node_data_type or 'any')
            self.nodeGraphPathEdit.setText(str(metadata.get('owned_graph_path', '') or ''))
            index = self.categoryCombo.findText(category)
            if index >= 0:
                self.categoryCombo.setCurrentIndex(index)
            elif category:
                self.categoryCombo.addItem(category)
                self.categoryCombo.setCurrentText(category)
            for port in list(node.get('inputs', []) or []) + list(node.get('outputs', []) or []):
                self.portTable.add_port_row(
                    name=str(port.get('name', '')),
                    direction=str(port.get('direction', 'input')),
                    pin_kind=str(port.get('connection_kind') or ('exec' if port.get('data_type') == 'exec' else 'data')),
                    data_type=str(port.get('data_type', 'any')),
                    multi=bool(port.get('multi_connection', False)),
                    required=bool(port.get('required', False)),
                )
        else:
            self.categoryCombo.setCurrentIndex(0 if self.categoryCombo.count() > 0 else -1)
            self._apply_node_kind_defaults('execution', preserve_existing=False)
        self._suspend_preview = False
        self._update_node_preview()
        self._sync_node_kind_ui()

    def _sync_node_kind_ui(self):
        node_kind = self.nodeKindCombo.currentText().strip().lower()
        is_data = node_kind == 'data'
        is_graph = node_kind == 'graph'
        self.nodeDataTypeEdit.setEnabled(is_data)
        self.nodeGraphPathEdit.setEnabled(is_graph)
        if is_data and not self.nodeDataTypeEdit.currentText().strip():
            self.nodeDataTypeEdit.setCurrentText('any')
        if not is_data:
            self.nodeDataTypeEdit.setCurrentText('any')
        if not is_graph:
            self.nodeGraphPathEdit.clear()

    def _apply_node_kind_defaults(self, node_kind: str, preserve_existing: bool = True):
        node_kind = str(node_kind or 'execution').strip().lower()
        node_data_type = self.nodeDataTypeEdit.currentText().strip() or 'any'
        if node_kind == 'data':
            if not preserve_existing or self.portTable.rowCount() == 0:
                self.portTable.clear_ports()
                self.portTable.add_port_row(name='Value', direction='output', pin_kind='data', data_type=node_data_type)
                return
            for row in range(self.portTable.rowCount()):
                kind_widget = self.portTable.cellWidget(row, 2)
                data_type_item = self.portTable.item(row, 3)
                if kind_widget is not None and kind_widget.currentText().strip().lower() != 'data':
                    kind_widget.setCurrentText('data')
                if data_type_item is not None and not data_type_item.text().strip():
                    data_type_item.setText(node_data_type)
            return
        if node_kind == 'graph':
            if not preserve_existing or self.portTable.rowCount() == 0:
                self.portTable.clear_ports()
                self.portTable.add_port_row(name='In', direction='input', pin_kind='exec', data_type='exec')
                self.portTable.add_port_row(name='Out', direction='output', pin_kind='exec', data_type='exec')
            return
        if not preserve_existing or self.portTable.rowCount() == 0:
            self.portTable.clear_ports()
            self.portTable.add_port_row(name='In', direction='input', pin_kind='exec', data_type='exec')
            self.portTable.add_port_row(name='Out', direction='output', pin_kind='exec', data_type='exec')

    def _on_node_kind_changed(self, node_kind: str):
        self._sync_node_kind_ui()
        if self._suspend_preview:
            return
        self._apply_node_kind_defaults(node_kind, preserve_existing=False)
        self._update_node_preview()

    def _refresh_category_combo(self):
        current = self.categoryCombo.currentText()
        categories = [self.categoryList.item(i).text() for i in range(self.categoryList.count())]
        self.categoryCombo.blockSignals(True)
        self.categoryCombo.clear()
        self.categoryCombo.addItems(categories)
        if current:
            index = self.categoryCombo.findText(current)
            if index >= 0:
                self.categoryCombo.setCurrentIndex(index)
        self.categoryCombo.blockSignals(False)

    def _sync_category_buttons(self):
        has_selection = bool(self.categoryList.selectedItems())
        self.btnRenameCategory.setEnabled(has_selection)
        self.btnDeleteCategory.setEnabled(has_selection)

    def _refresh_view_list_labels(self):
        item = self.viewList.currentItem()
        if item is None:
            return
        label = self.viewNameEdit.text().strip() or 'Untitled View'
        if self.viewDefaultCheck.isChecked():
            label += ' [default]'
        item.setText(label)

    def _refresh_node_list_labels(self):
        item = self.nodeList.currentItem()
        if item is None:
            return
        label = self.nodeNameEdit.text().strip() or 'Untitled Node'
        category = self.categoryCombo.currentText().strip() or 'uncategorized'
        item.setText(f'{label}  ({category})')

    def _prompt_text(self, title: str, label: str, text: str = '') -> Optional[str]:
        value, ok = QtWidgets.QInputDialog.getText(self, title, label, text=text)
        value = value.strip() if ok else ''
        return value if ok and value else None

    def _create_view(self):
        name = self._prompt_text('New View', 'View name')
        if not name:
            return
        view_id = self._unique_id(name, self._views_by_id.keys(), suffix='view')
        payload = {
            'view_id': view_id,
            'name': name,
            'description': '',
            'include_categories': [],
            'include_type_ids': [],
            'exclude_categories': [],
            'exclude_type_ids': [],
            'include_source_subdirs': [],
            'is_default': False,
            'rules': {
                'allow_cycles': True,
                'allow_self_connections': False,
                'enforce_data_type_compatibility': False,
                'cycle_checked_connection_kinds': ['exec'],
            },
            'connection_styles': {
                'data': {'color_role': 'connection_data', 'width': 2.0, 'pen_style': 'solid'},
                'exec': {'color_role': 'connection_exec', 'width': 2.5, 'pen_style': 'solid'},
            },
        }
        path = self._views_dir() / f'{view_id}.view.json'
        payload['_source_path'] = str(path)
        self._write_json(path, payload)
        self._views_by_id[view_id] = payload
        self._rebuild_view_list()
        self._select_view_by_id(view_id)

    def _delete_current_view(self):
        view = self._views_by_id.get(self._current_view_id) if self._current_view_id else None
        if not view:
            return
        answer = QtWidgets.QMessageBox.question(self, 'Delete View', f"Delete view '{view.get('name', view['view_id'])}'?")
        if answer != QtWidgets.QMessageBox.Yes:
            return
        source = Path(view.get('_source_path', self._views_dir() / f"{view['view_id']}.view.json"))
        if source.exists():
            source.unlink()
            self._log(f'Deleted {source}')
        self._views_by_id.pop(view['view_id'], None)
        self._current_view_id = None
        self._rebuild_view_list()
        if self.viewList.count() > 0:
            self.viewList.setCurrentRow(0)
        else:
            self._populate_view_form(None)
            self._rebuild_node_list()

    def _add_category(self):
        name = self._prompt_text('Add Category', 'Category name')
        if not name:
            return
        existing = {self.categoryList.item(i).text().lower() for i in range(self.categoryList.count())}
        if name.lower() in existing:
            QtWidgets.QMessageBox.warning(self, 'Category Exists', f"'{name}' already exists in this view.")
            return
        self.categoryList.addItem(name)
        self._refresh_category_combo()

    def _rename_category(self):
        items = self.categoryList.selectedItems()
        if not items:
            return
        item = items[0]
        old = item.text()
        new = self._prompt_text('Rename Category', 'Category name', text=old)
        if not new or new == old:
            return
        item.setText(new)
        for node in self._nodes_by_type.values():
            if node.get('category') == old and node.get('type_id') in set(self._views_by_id.get(self._current_view_id, {}).get('include_type_ids', [])):
                node['category'] = new
        if self.categoryCombo.currentText() == old:
            self.categoryCombo.setCurrentText(new)
        self._refresh_category_combo()
        self._rebuild_node_list()

    def _delete_category(self):
        items = self.categoryList.selectedItems()
        if not items:
            return
        category = items[0].text()
        answer = QtWidgets.QMessageBox.question(self, 'Delete Category', f"Delete category '{category}' from this view? Nodes in that category will remain on disk until you move or delete them.")
        if answer != QtWidgets.QMessageBox.Yes:
            return
        row = self.categoryList.row(items[0])
        self.categoryList.takeItem(row)
        self._refresh_category_combo()
        self._rebuild_node_list()

    def _create_node(self):
        if not self._current_view_id:
            QtWidgets.QMessageBox.warning(self, 'No View Selected', 'Create or select a view first.')
            return
        if self.categoryList.count() == 0:
            QtWidgets.QMessageBox.warning(self, 'No Categories', 'Add at least one category to the view first.')
            return
        draft_id = self._next_draft_node_id()
        self._current_node_type_id = draft_id
        self.nodeList.blockSignals(True)
        self.nodeList.clearSelection()
        draft_item = QtWidgets.QListWidgetItem('Untitled Node  (uncategorized)')
        draft_item.setData(QtCore.Qt.UserRole, draft_id)
        self.nodeList.addItem(draft_item)
        self.nodeList.setCurrentItem(draft_item)
        self.nodeList.blockSignals(False)
        self._populate_node_form(None)
        self._current_node_type_id = draft_id

    def _delete_current_node(self):
        if self._current_node_type_id and str(self._current_node_type_id).startswith('__draft_node__'):
            row = self.nodeList.currentRow()
            if row >= 0:
                self.nodeList.takeItem(row)
            self._current_node_type_id = None
            self._populate_node_form(None)
            return
        node = self._nodes_by_type.get(self._current_node_type_id) if self._current_node_type_id else None
        if not node:
            return
        answer = QtWidgets.QMessageBox.question(self, 'Delete Node', f"Delete node '{node.get('name', node['type_id'])}'?")
        if answer != QtWidgets.QMessageBox.Yes:
            return
        source = Path(node.get('_source_path', self._defs_dir()))
        if source.exists():
            source.unlink()
            self._log(f'Deleted {source}')
        view = self._views_by_id.get(self._current_view_id)
        if view:
            include_type_ids = [item for item in view.get('include_type_ids', []) if item != node['type_id']]
            view['include_type_ids'] = include_type_ids
            self._write_json(Path(view.get('_source_path', self._views_dir() / f"{view['view_id']}.view.json")), view)
        self._nodes_by_type.pop(node['type_id'], None)
        self._current_node_type_id = None
        self._rebuild_node_list()

    def _add_port(self, *, direction: str):
        self.portTable.add_port_row(direction=direction, pin_kind='data', data_type='any')
        self._update_node_preview()

    def _remove_selected_port(self):
        row = self.portTable.currentRow()
        if row >= 0:
            self.portTable.removeRow(row)
            self._update_node_preview()

    def _save_current_view(self):
        view = self._views_by_id.get(self._current_view_id) if self._current_view_id else None
        if view is None:
            QtWidgets.QMessageBox.warning(self, 'No View Selected', 'Select or create a view first.')
            return
        name = self.viewNameEdit.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, 'Missing Name', 'View name is required.')
            return
        categories = [self.categoryList.item(i).text().strip() for i in range(self.categoryList.count()) if self.categoryList.item(i).text().strip()]
        view['name'] = name
        view['description'] = self.viewDescEdit.text().strip()
        view['include_categories'] = categories
        if self.viewDefaultCheck.isChecked():
            for other in self._views_by_id.values():
                other['is_default'] = False
                self._write_json(Path(other.get('_source_path', self._views_dir() / f"{other['view_id']}.view.json")), other)
        view['is_default'] = bool(self.viewDefaultCheck.isChecked())
        path = Path(view.get('_source_path', self._views_dir() / f"{view['view_id']}.view.json"))
        self._write_json(path, view)
        self._views_by_id[view['view_id']] = view
        self._rebuild_view_list()
        self._select_view_by_id(view['view_id'])
        self._refresh_category_combo()
        self._rebuild_node_list()

    def _save_current_node(self):
        view = self._views_by_id.get(self._current_view_id) if self._current_view_id else None
        if view is None:
            QtWidgets.QMessageBox.warning(self, 'No View Selected', 'Select or create a view first.')
            return
        name = self.nodeNameEdit.text().strip()
        category = self.categoryCombo.currentText().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, 'Missing Name', 'Node name is required.')
            return
        if not category:
            QtWidgets.QMessageBox.warning(self, 'Missing Category', 'Choose a category for the node.')
            return
        ports = self.portTable.port_entries()
        node_kind = self.nodeKindCombo.currentText().strip().lower() or 'execution'
        node_data_type = self.nodeDataTypeEdit.currentText().strip() or 'any'
        if node_kind == 'data':
            for port in ports:
                if str(port.get('connection_kind', 'data')).strip().lower() != 'exec':
                    port['connection_kind'] = 'data'
                    port['data_type'] = node_data_type
        inputs = [p for p in ports if p['direction'] == 'input']
        outputs = [p for p in ports if p['direction'] == 'output']
        is_new = (self._current_node_type_id is None) or str(self._current_node_type_id).startswith('__draft_node__')
        type_id = self._unique_id(name, self._nodes_by_type.keys(), suffix='node') if is_new else self._current_node_type_id
        previous = self._nodes_by_type.get(type_id, {})
        payload = {
            'type_id': type_id,
            'name': name,
            'category': category,
            'description': self.nodeDescEdit.text().strip(),
            'inputs': inputs,
            'outputs': outputs,
            'properties': list(previous.get('properties', [])),
            'defaults': dict(previous.get('defaults', {})),
            'metadata': dict(previous.get('metadata', {'generated_by': 'NoDEViewBuilder'})),
            'visual': dict(previous.get('visual', {'compact': False})),
        }
        payload['metadata']['generated_by'] = 'NoDEViewBuilder'
        payload['metadata']['node_kind'] = node_kind
        payload['metadata']['node_data_type'] = node_data_type if node_kind == 'data' else ''
        owned_graph_path = ''
        if node_kind == 'graph':
            owned_graph_path = str(self._owned_graphs_dir() / f'{type_id}.nexnode')
            payload['metadata']['owns_graph'] = True
            payload['metadata']['execution_model'] = 'subgraph_call'
            payload['metadata']['owned_graph_id'] = f'{type_id}.graph'
            payload['metadata']['owned_graph_path'] = owned_graph_path
        else:
            payload['metadata'].pop('owns_graph', None)
            payload['metadata'].pop('execution_model', None)
            payload['metadata'].pop('owned_graph_id', None)
            payload['metadata'].pop('owned_graph_path', None)
        category_slug = self._stable_slug(category)
        new_path = self._defs_dir() / category_slug / f'{type_id}.json'
        old_path = Path(previous.get('_source_path', new_path)) if previous else new_path
        payload['_source_path'] = str(new_path)
        self._write_json(new_path, payload)
        if owned_graph_path:
            self._ensure_owned_graph_file(Path(owned_graph_path), payload, view)
            self.nodeGraphPathEdit.setText(owned_graph_path)
        if old_path != new_path and old_path.exists():
            old_path.unlink()
            self._log(f'Deleted moved file {old_path}')
        self._nodes_by_type[type_id] = payload
        include_type_ids = list(view.get('include_type_ids', []) or [])
        if type_id not in include_type_ids:
            include_type_ids.append(type_id)
            view['include_type_ids'] = include_type_ids
            self._write_json(Path(view.get('_source_path', self._views_dir() / f"{view['view_id']}.view.json")), view)
        self._current_node_type_id = type_id
        self._rebuild_node_list()
        self._select_node_by_type(type_id)

    def _update_node_preview(self):
        if self._suspend_preview:
            return
        ports = self.portTable.port_entries()
        node_kind = self.nodeKindCombo.currentText().strip().lower() or 'execution'
        node_data_type = self.nodeDataTypeEdit.currentText().strip() or 'any'
        if node_kind == 'data':
            for port in ports:
                if str(port.get('connection_kind', 'data')).strip().lower() != 'exec':
                    port['connection_kind'] = 'data'
                    port['data_type'] = node_data_type
        inputs = [p for p in ports if p['direction'] == 'input']
        outputs = [p for p in ports if p['direction'] == 'output']
        title = self.nodeNameEdit.text().strip() or ('Data Node' if node_kind == 'data' else 'Node')
        self.nodePreview.refresh(title, inputs, outputs)
        self._refresh_node_list_labels()


    def _next_draft_node_id(self) -> str:
        existing = {self.nodeList.item(i).data(QtCore.Qt.UserRole) for i in range(self.nodeList.count())}
        counter = 1
        while True:
            draft_id = f'__draft_node__{counter}'
            if draft_id not in existing:
                return draft_id
            counter += 1

    def _owned_graphs_dir(self) -> Path:
        return self._target_plugin_root / 'node_graphs'

    def _ensure_owned_graph_file(self, path: Path, node_payload: dict, view_payload: Optional[dict]):
        if path.exists():
            return
        graph_payload = {
            'metadata': {
                'generated_by': 'NoDEViewBuilder',
                'owner_node_type_id': node_payload.get('type_id'),
                'owner_node_name': node_payload.get('name'),
                'active_node_view_id': view_payload.get('view_id') if isinstance(view_payload, dict) else None,
                'graph_role': 'owned_subgraph',
            },
            'nodes': [],
            'connections': [],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(graph_payload, indent=2), encoding='utf-8')
        self._log(f'Created owned graph {path}')

    def _write_json(self, path: Path, payload: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        serializable = {k: v for k, v in payload.items() if not str(k).startswith('_')}
        path.write_text(json.dumps(serializable, indent=2), encoding='utf-8')
        payload['_source_path'] = str(path)
        self._log(f'Wrote {path}')

    def _log(self, message: str):
        self.logEdit.appendPlainText(message)

    @staticmethod
    def _stable_slug(value: str) -> str:
        slug = re.sub(r'[^a-z0-9]+', '_', value.strip().lower())
        return slug.strip('_') or 'item'

    def _unique_id(self, name: str, existing_ids, *, suffix: str) -> str:
        base = self._stable_slug(name)
        if not base.endswith(f'_{suffix}'):
            base = f'{base}_{suffix}'
        candidate = base
        counter = 2
        existing = set(existing_ids)
        while candidate in existing:
            candidate = f'{base}_{counter}'
            counter += 1
        return candidate
