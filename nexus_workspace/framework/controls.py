# ============================================================================
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
# File: controls.py
# Description: Defines reusable Nexus UI controls that extend common Qt widgets.
#============================================================================

from __future__ import annotations

from typing import Iterable, Optional

from PyQt5 import QtCore, QtGui, QtWidgets


class NexusWidgetMixin:
    """Nexus metadata/capability layer for Qt-derived widgets.

    Every first-class Nexus control subclasses the native Qt widget directly. That
    preserves Qt methods, properties, signals, delegates, models, drag/drop, and
    event behavior while adding Nexus identity, theme roles, variants, metadata,
    and property schemas for the Plugin Builder.
    """

    NEXUS_TYPE_ID = "nexus.widget"
    QT_BASE_CLASS = "QWidget"
    NEXUS_PROPERTY_SCHEMA = {"enabled": "bool", "visible": "bool", "tool_tip": "str", "object_name": "str"}
    NEXUS_SIGNALS = ()

    def _init_nexus(self, *, object_name=None, nexus_id=None, metadata=None, theme_role=None, variant=None):
        if object_name:
            self.setObjectName(str(object_name))
        self._nexus_id = str(nexus_id or "")
        self._nexus_metadata = dict(metadata or {})
        if self._nexus_id:
            self.setProperty("nexusId", self._nexus_id)
        if theme_role:
            self.setProperty("nexusThemeRole", str(theme_role))
        if variant is not None:
            self.setProperty("nexusVariant", str(variant or "default"))
        self._repolish_nexus_style()

    @property
    def nexus_id(self):
        return getattr(self, "_nexus_id", "")

    def set_nexus_id(self, nexus_id):
        self._nexus_id = str(nexus_id or "")
        self.setProperty("nexusId", self._nexus_id)
        return self

    def nexus_metadata(self):
        return dict(getattr(self, "_nexus_metadata", {}))

    def set_nexus_metadata(self, metadata):
        self._nexus_metadata = dict(metadata or {})
        return self

    def set_nexus_meta(self, key, value):
        if not hasattr(self, "_nexus_metadata"):
            self._nexus_metadata = {}
        self._nexus_metadata[str(key)] = value
        return self

    def nexus_meta(self, key, default=None):
        return getattr(self, "_nexus_metadata", {}).get(str(key), default)

    def set_nexus_theme_role(self, role):
        self.setProperty("nexusThemeRole", str(role or ""))
        return self._repolish_nexus_style()

    def set_nexus_variant(self, variant="default"):
        self.setProperty("nexusVariant", str(variant or "default"))
        return self._repolish_nexus_style()

    def set_nexus_corner_style(self, corner_style="rounded"):
        """Set a semantic corner style used by the Nexus design system."""
        value = str(corner_style or "rounded").lower()
        if value not in {"rounded", "square"}:
            value = "rounded"
        self.setProperty("nexusCorner", value)
        return self._repolish_nexus_style()

    def set_nexus_border_style(self, border_style="default"):
        """Set a semantic border style used by the Nexus design system."""
        value = str(border_style or "default").lower()
        if value not in {"default", "none", "subtle", "strong"}:
            value = "default"
        self.setProperty("nexusBorder", value)
        return self._repolish_nexus_style()

    def set_nexus_background_style(self, background_style="default"):
        """Set a semantic background style used by the Nexus design system."""
        value = str(background_style or "default").lower()
        if value not in {"default", "panel", "surface", "transparent"}:
            value = "default"
        self.setProperty("nexusBackground", value)
        return self._repolish_nexus_style()

    def apply_nexus_style_properties(self, *, corner_style=None, border_style=None, background_style=None):
        if corner_style is not None:
            self.set_nexus_corner_style(corner_style)
        if border_style is not None:
            self.set_nexus_border_style(border_style)
        if background_style is not None:
            self.set_nexus_background_style(background_style)
        return self._repolish_nexus_style()

    def _repolish_nexus_style(self):
        style = self.style() if hasattr(self, "style") else None
        if style is not None:
            style.unpolish(self)
            style.polish(self)
        self.update()
        return self

    @classmethod
    def nexus_capabilities(cls):
        return {
            "type_id": getattr(cls, "NEXUS_TYPE_ID", cls.__name__),
            "qt_base": getattr(cls, "QT_BASE_CLASS", ""),
            "properties": dict(getattr(cls, "NEXUS_PROPERTY_SCHEMA", {})),
            "signals": list(getattr(cls, "NEXUS_SIGNALS", ())),
        }


def _apply_common_widget_options(widget, **kwargs):
    setters = {
        "tool_tip": widget.setToolTip,
        "tooltip": widget.setToolTip,
        "status_tip": widget.setStatusTip,
        "whats_this": widget.setWhatsThis,
        "accessible_name": widget.setAccessibleName,
        "accessible_description": widget.setAccessibleDescription,
        "enabled": widget.setEnabled,
        "visible": widget.setVisible,
        "minimum_width": widget.setMinimumWidth,
        "minimum_height": widget.setMinimumHeight,
        "maximum_width": widget.setMaximumWidth,
        "maximum_height": widget.setMaximumHeight,
        "fixed_width": widget.setFixedWidth,
        "fixed_height": widget.setFixedHeight,
        "size_policy": widget.setSizePolicy,
        "focus_policy": widget.setFocusPolicy,
        "context_menu_policy": widget.setContextMenuPolicy,
        "accept_drops": widget.setAcceptDrops,
        "style_sheet": widget.setStyleSheet,
        "font": widget.setFont,
        "cursor": widget.setCursor,
    }
    for key, value in kwargs.items():
        if value is None:
            continue
        setter = setters.get(key)
        if setter is None:
            raise TypeError(f"Unsupported Nexus widget option: {key}")
        setter(value)
    return widget


class NexusFrame(QtWidgets.QFrame, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.frame"
    QT_BASE_CLASS = "QFrame"

    def __init__(self, parent=None, *, object_name="NexusFrame", frame_shape=QtWidgets.QFrame.NoFrame, frame_shadow=None, line_width=None, mid_line_width=None, nexus_id=None, metadata=None, theme_role="surface", corner_style="rounded", border_style="default", background_style="default", **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, nexus_id=nexus_id, metadata=metadata, theme_role=theme_role)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setProperty("nexusControl", "frame")
        self.setProperty("nexusFrameStyle", "borderless" if frame_shape == QtWidgets.QFrame.NoFrame else "bordered")
        self.apply_nexus_style_properties(corner_style=corner_style, border_style=border_style, background_style=background_style)
        self.setFrameShape(frame_shape)
        if frame_shadow is not None:
            self.setFrameShadow(frame_shadow)
        if line_width is not None:
            self.setLineWidth(int(line_width))
        if mid_line_width is not None:
            self.setMidLineWidth(int(mid_line_width))
        _apply_common_widget_options(self, **kwargs)


class NexusSection(NexusFrame):
    NEXUS_TYPE_ID = "nexus.section"

    def __init__(self, title="", parent=None, *, object_name="NexusSection", margins=(12, 12, 12, 12), spacing=8, title_selectable=False, **kwargs):
        super().__init__(parent, object_name=object_name, frame_shape=QtWidgets.QFrame.NoFrame, theme_role="section", **kwargs)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(*margins)
        root.setSpacing(spacing)
        self._title_label = None
        if title:
            self._title_label = NexusLabel(str(title), self, object_name="NexusSectionTitle", selectable=title_selectable)
            font = self._title_label.font()
            font.setBold(True)
            self._title_label.setFont(font)
            root.addWidget(self._title_label, 0)
        self._body = QtWidgets.QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(spacing)
        root.addLayout(self._body, 1)

    def body_layout(self):
        return self._body

    def title(self):
        return self._title_label.text() if self._title_label else ""

    def set_title(self, title):
        if self._title_label is None:
            self._title_label = NexusLabel("", self, object_name="NexusSectionTitle")
            font = self._title_label.font()
            font.setBold(True)
            self._title_label.setFont(font)
            self.layout().insertWidget(0, self._title_label, 0)
        self._title_label.setText(str(title or ""))
        return self


class NexusSubWindow(QtWidgets.QMdiSubWindow, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.sub_window"
    QT_BASE_CLASS = "QMdiSubWindow"

    def __init__(self, parent=None, *, object_name="NexusSubWindow", delete_on_close=False, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, bool(delete_on_close))
        _apply_common_widget_options(self, **kwargs)


class NexusMenuBar(QtWidgets.QMenuBar, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.menu_bar"
    QT_BASE_CLASS = "QMenuBar"

    def __init__(self, parent=None, *, object_name="NexusMenuBar", native_menu_bar=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name)
        if native_menu_bar is not None:
            self.setNativeMenuBar(bool(native_menu_bar))
        _apply_common_widget_options(self, **kwargs)

    def add_nexus_menu(self, title: str):
        menu = NexusMenu(title, self)
        self.addMenu(menu)
        return menu


class NexusMenu(QtWidgets.QMenu, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.menu"
    QT_BASE_CLASS = "QMenu"

    def __init__(self, title="", parent=None, *, object_name="NexusMenu", tear_off_enabled=None, **kwargs):
        super().__init__(str(title or ""), parent)
        self._init_nexus(object_name=object_name)
        if tear_off_enabled is not None:
            self.setTearOffEnabled(bool(tear_off_enabled))
        _apply_common_widget_options(self, **kwargs)

    def add_nexus_menu(self, title: str):
        submenu = NexusMenu(title, self)
        self.addMenu(submenu)
        return submenu

    def add_action(self, text: str, callback=None, *, checkable: bool = False, checked: bool = False, enabled: bool = True, shortcut: Optional[str] = None, tooltip: str = "", icon=None, data=None):
        action = QtWidgets.QAction(str(text or ""), self)
        if icon is not None:
            action.setIcon(icon if isinstance(icon, QtGui.QIcon) else QtGui.QIcon(str(icon)))
        action.setCheckable(bool(checkable))
        if checkable:
            action.setChecked(bool(checked))
        action.setEnabled(bool(enabled))
        if shortcut:
            action.setShortcut(QtGui.QKeySequence(str(shortcut)))
        if tooltip:
            action.setToolTip(str(tooltip))
            action.setStatusTip(str(tooltip))
        if data is not None:
            action.setData(data)
        if callback is not None:
            action.triggered.connect(callback)
        self.addAction(action)
        return action


class NexusLabel(QtWidgets.QLabel, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.label"
    QT_BASE_CLASS = "QLabel"
    NEXUS_PROPERTY_SCHEMA = {"text": "str", "pixmap": "QPixmap", "word_wrap": "bool", "alignment": "Qt.Alignment", "selectable": "bool", "open_external_links": "bool"}

    def __init__(self, text="", parent=None, *, object_name="NexusLabel", word_wrap=False, alignment=None, text_format=None, pixmap=None, scaled_contents=None, open_external_links=None, selectable=False, buddy=None, **kwargs):
        super().__init__(str(text or ""), parent)
        self._init_nexus(object_name=object_name, theme_role="text")
        self.setWordWrap(bool(word_wrap))
        if alignment is not None:
            self.setAlignment(alignment)
        if text_format is not None:
            self.setTextFormat(text_format)
        if pixmap is not None:
            self.setPixmap(pixmap)
        if scaled_contents is not None:
            self.setScaledContents(bool(scaled_contents))
        if open_external_links is not None:
            self.setOpenExternalLinks(bool(open_external_links))
        if selectable:
            self.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse | QtCore.Qt.TextSelectableByKeyboard)
        if buddy is not None:
            self.setBuddy(buddy)
        _apply_common_widget_options(self, **kwargs)


class NexusTextInput(QtWidgets.QLineEdit, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.text_input"
    QT_BASE_CLASS = "QLineEdit"
    NEXUS_PROPERTY_SCHEMA = {"text": "str", "placeholder": "str", "read_only": "bool", "clear_button_enabled": "bool", "echo_mode": "QLineEdit.EchoMode", "max_length": "int", "input_mask": "str", "validator": "QValidator", "completer": "QCompleter"}
    NEXUS_SIGNALS = ("textChanged", "textEdited", "returnPressed", "editingFinished", "selectionChanged")

    def __init__(self, text="", parent=None, *, object_name="NexusTextInput", placeholder="", clear_button=True, read_only=False, echo_mode=None, max_length=None, input_mask=None, validator=None, completer=None, alignment=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="input")
        self.setText(str(text or ""))
        self.setPlaceholderText(str(placeholder or ""))
        self.setClearButtonEnabled(bool(clear_button))
        self.setReadOnly(bool(read_only))
        if echo_mode is not None:
            self.setEchoMode(echo_mode)
        if max_length is not None:
            self.setMaxLength(int(max_length))
        if input_mask:
            self.setInputMask(str(input_mask))
        if validator is not None:
            self.setValidator(validator)
        if completer is not None:
            self.setCompleter(completer)
        if alignment is not None:
            self.setAlignment(alignment)
        _apply_common_widget_options(self, **kwargs)


class NexusButton(QtWidgets.QPushButton, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.button"
    QT_BASE_CLASS = "QPushButton"
    NEXUS_PROPERTY_SCHEMA = {"text": "str", "icon": "QIcon", "checkable": "bool", "checked": "bool", "default": "bool", "auto_default": "bool", "flat": "bool", "menu": "QMenu", "shortcut": "QKeySequence", "variant": "enum"}
    NEXUS_SIGNALS = ("clicked", "pressed", "released", "toggled")

    def __init__(self, text="", parent=None, *, object_name="NexusButton", tooltip="", variant="secondary", icon=None, checkable=False, checked=False, default=False, auto_default=None, flat=False, menu=None, shortcut=None, **kwargs):
        super().__init__(str(text or ""), parent)
        self._init_nexus(object_name=object_name, theme_role="button", variant=variant)
        if icon is not None:
            self.setIcon(icon if isinstance(icon, QtGui.QIcon) else QtGui.QIcon(str(icon)))
        self.setCheckable(bool(checkable))
        if checkable or checked:
            self.setChecked(bool(checked))
        self.setDefault(bool(default))
        if auto_default is not None:
            self.setAutoDefault(bool(auto_default))
        self.setFlat(bool(flat))
        if menu is not None:
            self.setMenu(menu)
        if shortcut:
            self.setShortcut(QtGui.QKeySequence(str(shortcut)))
        if tooltip:
            self.setToolTip(str(tooltip))
        _apply_common_widget_options(self, **kwargs)


class NexusCheckBox(QtWidgets.QCheckBox, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.checkbox"
    QT_BASE_CLASS = "QCheckBox"
    NEXUS_PROPERTY_SCHEMA = {"text": "str", "checked": "bool", "tristate": "bool", "check_state": "Qt.CheckState"}
    NEXUS_SIGNALS = ("stateChanged", "toggled", "clicked")

    def __init__(self, text="", parent=None, *, object_name="NexusCheckBox", checked=False, tristate=False, check_state=None, **kwargs):
        super().__init__(str(text or ""), parent)
        self._init_nexus(object_name=object_name, theme_role="check")
        self.setTristate(bool(tristate))
        if check_state is not None:
            self.setCheckState(check_state)
        else:
            self.setChecked(bool(checked))
        _apply_common_widget_options(self, **kwargs)


class NexusRadioButton(QtWidgets.QRadioButton, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.radio_button"
    QT_BASE_CLASS = "QRadioButton"
    NEXUS_PROPERTY_SCHEMA = {"text": "str", "checked": "bool", "auto_exclusive": "bool"}
    NEXUS_SIGNALS = ("toggled", "clicked")

    def __init__(self, text="", parent=None, *, object_name="NexusRadioButton", checked=False, auto_exclusive=None, **kwargs):
        super().__init__(str(text or ""), parent)
        self._init_nexus(object_name=object_name, theme_role="radio")
        self.setChecked(bool(checked))
        if auto_exclusive is not None:
            self.setAutoExclusive(bool(auto_exclusive))
        _apply_common_widget_options(self, **kwargs)


class NexusSlider(QtWidgets.QSlider, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.slider"
    QT_BASE_CLASS = "QSlider"
    NEXUS_SIGNALS = ("valueChanged", "sliderMoved", "sliderPressed", "sliderReleased", "rangeChanged")

    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None, *, object_name="NexusSlider", minimum=None, maximum=None, value=None, single_step=None, page_step=None, tick_position=None, tick_interval=None, tracking=None, **kwargs):
        super().__init__(orientation, parent)
        self._init_nexus(object_name=object_name, theme_role="slider")
        if minimum is not None: self.setMinimum(int(minimum))
        if maximum is not None: self.setMaximum(int(maximum))
        if single_step is not None: self.setSingleStep(int(single_step))
        if page_step is not None: self.setPageStep(int(page_step))
        if tick_position is not None: self.setTickPosition(tick_position)
        if tick_interval is not None: self.setTickInterval(int(tick_interval))
        if tracking is not None: self.setTracking(bool(tracking))
        if value is not None: self.setValue(int(value))
        _apply_common_widget_options(self, **kwargs)


class NexusComboBox(QtWidgets.QComboBox, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.combo_box"
    QT_BASE_CLASS = "QComboBox"
    NEXUS_PROPERTY_SCHEMA = {"items": "list", "editable": "bool", "current_index": "int", "current_text": "str", "insert_policy": "QComboBox.InsertPolicy", "duplicates_enabled": "bool"}
    NEXUS_SIGNALS = ("currentIndexChanged", "currentTextChanged", "activated", "editTextChanged")

    def __init__(self, parent=None, *, object_name="NexusComboBox", editable=False, items=None, current_index=None, current_text=None, insert_policy=None, duplicates_enabled=None, max_visible_items=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="input")
        self.setEditable(bool(editable))
        if items: self.set_items(items)
        if insert_policy is not None: self.setInsertPolicy(insert_policy)
        if duplicates_enabled is not None: self.setDuplicatesEnabled(bool(duplicates_enabled))
        if max_visible_items is not None: self.setMaxVisibleItems(int(max_visible_items))
        if current_index is not None: self.setCurrentIndex(int(current_index))
        if current_text is not None: self.setCurrentText(str(current_text))
        _apply_common_widget_options(self, **kwargs)

    def set_items(self, items: Iterable):
        self.clear()
        for item in items or []:
            if isinstance(item, dict):
                self.addItem(str(item.get("label", item.get("text", item.get("value", "")))), item.get("value"))
            elif isinstance(item, tuple) and len(item) >= 2:
                self.addItem(str(item[0]), item[1])
            else:
                self.addItem(str(item))
        return self

    def items(self):
        return [self.itemText(i) for i in range(self.count())]


class NexusSpinBox(QtWidgets.QSpinBox, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.spin_box"
    QT_BASE_CLASS = "QSpinBox"
    NEXUS_SIGNALS = ("valueChanged", "textChanged", "editingFinished")

    def __init__(self, parent=None, *, object_name="NexusSpinBox", minimum=None, maximum=None, value=None, single_step=None, prefix="", suffix="", wrapping=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="input")
        if minimum is not None: self.setMinimum(int(minimum))
        if maximum is not None: self.setMaximum(int(maximum))
        if single_step is not None: self.setSingleStep(int(single_step))
        if prefix: self.setPrefix(str(prefix))
        if suffix: self.setSuffix(str(suffix))
        if wrapping is not None: self.setWrapping(bool(wrapping))
        if value is not None: self.setValue(int(value))
        _apply_common_widget_options(self, **kwargs)


class NexusDoubleSpinBox(QtWidgets.QDoubleSpinBox, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.double_spin_box"
    QT_BASE_CLASS = "QDoubleSpinBox"
    NEXUS_SIGNALS = ("valueChanged", "textChanged", "editingFinished")

    def __init__(self, parent=None, *, object_name="NexusDoubleSpinBox", minimum=None, maximum=None, value=None, single_step=None, decimals=None, prefix="", suffix="", wrapping=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="input")
        if decimals is not None: self.setDecimals(int(decimals))
        if minimum is not None: self.setMinimum(float(minimum))
        if maximum is not None: self.setMaximum(float(maximum))
        if single_step is not None: self.setSingleStep(float(single_step))
        if prefix: self.setPrefix(str(prefix))
        if suffix: self.setSuffix(str(suffix))
        if wrapping is not None: self.setWrapping(bool(wrapping))
        if value is not None: self.setValue(float(value))
        _apply_common_widget_options(self, **kwargs)


class NexusTabWidget(QtWidgets.QTabWidget, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.tab_widget"
    QT_BASE_CLASS = "QTabWidget"
    NEXUS_SIGNALS = ("currentChanged", "tabCloseRequested", "tabBarClicked", "tabBarDoubleClicked")

    def __init__(self, parent=None, *, object_name="NexusTabWidget", document_mode=True, tabs_closable=None, movable=None, tab_position=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="tabs")
        self.setDocumentMode(bool(document_mode))
        if tabs_closable is not None: self.setTabsClosable(bool(tabs_closable))
        if movable is not None: self.setMovable(bool(movable))
        if tab_position is not None: self.setTabPosition(tab_position)
        _apply_common_widget_options(self, **kwargs)

    def add_nexus_tab(self, widget, title, icon=None):
        return self.addTab(widget, icon, str(title or "")) if icon is not None else self.addTab(widget, str(title or ""))


class NexusListWidget(QtWidgets.QListWidget, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.list_widget"
    QT_BASE_CLASS = "QListWidget"

    def __init__(self, parent=None, *, object_name="NexusListWidget", items=None, alternating_row_colors=True, uniform_item_sizes=True, selection_mode=None, drag_drop_mode=None, sorting_enabled=None, edit_triggers=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="list")
        self.setAlternatingRowColors(bool(alternating_row_colors))
        self.setUniformItemSizes(bool(uniform_item_sizes))
        if selection_mode is not None: self.setSelectionMode(selection_mode)
        if drag_drop_mode is not None: self.setDragDropMode(drag_drop_mode)
        if sorting_enabled is not None: self.setSortingEnabled(bool(sorting_enabled))
        if edit_triggers is not None: self.setEditTriggers(edit_triggers)
        if items: self.set_items(items)
        _apply_common_widget_options(self, **kwargs)

    def set_items(self, items):
        self.clear()
        for item in items or []:
            self.addItem(item if isinstance(item, QtWidgets.QListWidgetItem) else str(item))
        return self

    def items(self):
        return [self.item(i).text() for i in range(self.count())]


class NexusTreeWidget(QtWidgets.QTreeWidget, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.tree_widget"
    QT_BASE_CLASS = "QTreeWidget"

    def __init__(self, parent=None, *, object_name="NexusTreeWidget", header_labels=None, column_count=None, alternating_row_colors=True, uniform_row_heights=True, root_is_decorated=None, selection_mode=None, drag_drop_mode=None, sorting_enabled=None, edit_triggers=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="tree")
        self.setAlternatingRowColors(bool(alternating_row_colors))
        self.setUniformRowHeights(bool(uniform_row_heights))
        if column_count is not None: self.setColumnCount(int(column_count))
        if header_labels is not None: self.setHeaderLabels([str(x) for x in header_labels])
        if root_is_decorated is not None: self.setRootIsDecorated(bool(root_is_decorated))
        if selection_mode is not None: self.setSelectionMode(selection_mode)
        if drag_drop_mode is not None: self.setDragDropMode(drag_drop_mode)
        if sorting_enabled is not None: self.setSortingEnabled(bool(sorting_enabled))
        if edit_triggers is not None: self.setEditTriggers(edit_triggers)
        _apply_common_widget_options(self, **kwargs)


class NexusHierarchyView(NexusTreeWidget):
    NEXUS_TYPE_ID = "nexus.hierarchy_view"

    def __init__(self, parent=None, *, object_name="NexusHierarchyView", **kwargs):
        super().__init__(parent, object_name=object_name, **kwargs)


class NexusTableWidget(QtWidgets.QTableWidget, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.table_widget"
    QT_BASE_CLASS = "QTableWidget"

    tableDataChanged = QtCore.pyqtSignal()
    structureChanged = QtCore.pyqtSignal()
    columnRenamed = QtCore.pyqtSignal(int, str, str)

    def __init__(self, rows=0, columns=0, parent=None, *, object_name="NexusTableWidget", horizontal_headers=None, vertical_headers=None, alternating_row_colors=True, selection_behavior=QtWidgets.QAbstractItemView.SelectRows, selection_mode=None, edit_triggers=None, hide_vertical_header=True, sorting_enabled=None, stretch_last_section=None, enable_context_menu=True, enable_clipboard=True, allow_structure_edit=False, multi_select=True, editable_cells=False, spreadsheet_mode=False, enable_sorting=True, enable_filtering=True, allow_column_rename=True, **kwargs):
        # Preserve the common Qt overloads while keeping Nexus convenience arguments.
        # QTableWidget(parent) is a valid Qt pattern, so NexusTableEditor(parent)
        # must not treat the QWidget as a row count.
        if isinstance(rows, QtWidgets.QWidget) and parent is None and columns == 0:
            parent = rows
            rows = 0
            columns = 0
        rows = 0 if rows is None else int(rows)
        columns = 0 if columns is None else int(columns)
        super().__init__(rows, columns, parent)
        self._init_nexus(object_name=object_name, theme_role="table")
        self._nexus_table_capabilities = {}
        self._table_undo_stack = []
        self._table_redo_stack = []
        self._restoring_table_snapshot = False
        self._bulk_table_mutation = False
        self._last_table_snapshot = None
        self._hidden_rows_by_filter = set()
        self._drag_fill_active = False
        self._drag_fill_source_bounds = None
        self._drag_fill_target = None
        self._drag_fill_hover_handle = False
        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)
        self.setAlternatingRowColors(bool(alternating_row_colors))
        if selection_behavior is not None:
            self.setSelectionBehavior(selection_behavior)
        if selection_mode is not None:
            self.setSelectionMode(selection_mode)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers if edit_triggers is None else edit_triggers)
        self.setTabKeyNavigation(True)
        self.verticalHeader().setVisible(not bool(hide_vertical_header))
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setSectionsClickable(True)
        if horizontal_headers is not None:
            self.setHorizontalHeaderLabels([str(x) for x in horizontal_headers])
        if vertical_headers is not None:
            self.setVerticalHeaderLabels([str(x) for x in vertical_headers])
        if sorting_enabled is not None:
            self.setSortingEnabled(bool(sorting_enabled))
        if stretch_last_section is not None:
            self.horizontalHeader().setStretchLastSection(bool(stretch_last_section))
        self.set_table_capabilities(
            context_menu=enable_context_menu,
            clipboard=enable_clipboard,
            structure_edit=allow_structure_edit,
            multi_select=multi_select,
            editable=editable_cells,
            spreadsheet=spreadsheet_mode,
            sorting=enable_sorting if sorting_enabled is None else bool(sorting_enabled),
            filtering=enable_filtering,
            column_rename=allow_column_rename,
        )
        self.itemChanged.connect(self._on_table_item_changed)
        self.horizontalHeader().sectionDoubleClicked.connect(self.rename_column_at_index)
        self._connect_table_selection_repaint_hooks()
        self._install_table_keyboard_shortcuts()
        self._install_table_application_shortcut_filter()
        self._last_table_snapshot = self._table_snapshot()
        _apply_common_widget_options(self, **kwargs)

    def set_table_capabilities(self, *, context_menu=None, clipboard=None, structure_edit=None, multi_select=None, editable=None, spreadsheet=None, sorting=None, filtering=None, column_rename=None):
        caps = getattr(self, "_nexus_table_capabilities", {}) or {}
        if context_menu is not None: caps["context_menu"] = bool(context_menu)
        if clipboard is not None: caps["clipboard"] = bool(clipboard)
        if structure_edit is not None: caps["structure_edit"] = bool(structure_edit)
        if multi_select is not None: caps["multi_select"] = bool(multi_select)
        if editable is not None: caps["editable"] = bool(editable)
        if spreadsheet is not None: caps["spreadsheet"] = bool(spreadsheet)
        if sorting is not None: caps["sorting"] = bool(sorting)
        if filtering is not None: caps["filtering"] = bool(filtering)
        if column_rename is not None: caps["column_rename"] = bool(column_rename)
        self._nexus_table_capabilities = caps
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection if caps.get("multi_select", True) else QtWidgets.QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems if caps.get("spreadsheet", False) else self.selectionBehavior())
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed
            if caps.get("editable", False) else QtWidgets.QAbstractItemView.NoEditTriggers
        )
        if caps.get("spreadsheet", False):
            self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
            self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection if caps.get("multi_select", True) else QtWidgets.QAbstractItemView.SingleSelection)
            self.setDragDropMode(QtWidgets.QAbstractItemView.NoDragDrop)
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu if caps.get("context_menu", True) else QtCore.Qt.NoContextMenu)
        if not caps.get("sorting", True):
            self.setSortingEnabled(False)
        return self

    def _table_snapshot(self):
        return {
            "headers": [self.horizontalHeaderItem(c).text() if self.horizontalHeaderItem(c) else f"Column {c + 1}" for c in range(self.columnCount())],
            "rows": [[self.item(r, c).text() if self.item(r, c) else "" for c in range(self.columnCount())] for r in range(self.rowCount())],
        }

    def _restore_table_snapshot(self, snapshot):
        if isinstance(snapshot, list):
            snapshot = {"headers": [f"Column {i + 1}" for i in range(max((len(row) for row in snapshot), default=0))], "rows": snapshot}
        headers = list((snapshot or {}).get("headers") or [])
        rows = list((snapshot or {}).get("rows") or [])
        self._restoring_table_snapshot = True
        self._bulk_table_mutation = True
        try:
            column_count = max(len(headers), max((len(row) for row in rows), default=0), self.columnCount())
            self.setColumnCount(column_count)
            self.setRowCount(len(rows))
            if headers:
                self.setHorizontalHeaderLabels([str(x) for x in headers])
            for r, row in enumerate(rows):
                for c, value in enumerate(row):
                    self.setItem(r, c, QtWidgets.QTableWidgetItem(str(value)))
            self.clear_filters()
        finally:
            self._bulk_table_mutation = False
            self._restoring_table_snapshot = False
            self._last_table_snapshot = self._table_snapshot()
        self.tableDataChanged.emit()
        self.structureChanged.emit()

    def _push_table_undo(self, snapshot=None):
        if getattr(self, "_restoring_table_snapshot", False):
            return
        self._table_undo_stack.append(snapshot if snapshot is not None else self._table_snapshot())
        if len(self._table_undo_stack) > 50:
            self._table_undo_stack.pop(0)
        self._table_redo_stack.clear()

    def _on_table_item_changed(self, _item):
        if getattr(self, "_restoring_table_snapshot", False) or getattr(self, "_bulk_table_mutation", False):
            return
        previous = getattr(self, "_last_table_snapshot", None)
        if previous is not None:
            self._push_table_undo(previous)
        self._last_table_snapshot = self._table_snapshot()
        self.tableDataChanged.emit()

    def undo_table(self):
        if not self._table_undo_stack:
            return
        self._table_redo_stack.append(self._table_snapshot())
        self._restore_table_snapshot(self._table_undo_stack.pop())

    def redo_table(self):
        if not self._table_redo_stack:
            return
        self._table_undo_stack.append(self._table_snapshot())
        self._restore_table_snapshot(self._table_redo_stack.pop())

    def _selected_bounds(self):
        ranges = self.selectedRanges()
        if not ranges:
            row = self.currentRow()
            col = self.currentColumn()
            if row < 0 or col < 0:
                return None
            return row, row, col, col
        return (
            min(r.topRow() for r in ranges),
            max(r.bottomRow() for r in ranges),
            min(r.leftColumn() for r in ranges),
            max(r.rightColumn() for r in ranges),
        )

    def _connect_table_selection_repaint_hooks(self):
        try:
            model = self.selectionModel()
            if model is not None:
                model.selectionChanged.connect(lambda *_: self.viewport().update())
                model.currentChanged.connect(lambda *_: self.viewport().update())
        except Exception:
            # Selection model setup is best-effort because Qt may replace the model
            # when the view is reconfigured by a plugin builder or host tool.
            pass

    def _install_table_keyboard_shortcuts(self):
        # QTableWidget only receives keyPressEvent while the view itself owns focus.
        # In spreadsheet use, focus often belongs to the viewport or a transient cell
        # editor, so install widget-with-children shortcuts to keep Excel-style
        # actions reliable from anywhere inside the table.
        self._nexus_table_shortcuts = []

        def add_shortcut(sequence, callback):
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(sequence), self)
            shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
            self._nexus_table_shortcuts.append(shortcut)

        add_shortcut(QtGui.QKeySequence.Copy, self._shortcut_copy_selection)
        add_shortcut(QtGui.QKeySequence.Cut, self._shortcut_cut_selection)
        add_shortcut(QtGui.QKeySequence.Paste, self._shortcut_paste_clipboard)
        add_shortcut(QtGui.QKeySequence.Undo, self._shortcut_undo)
        add_shortcut(QtGui.QKeySequence.Redo, self._shortcut_redo)
        add_shortcut(QtGui.QKeySequence.SelectAll, self._shortcut_select_all)
        add_shortcut(QtCore.Qt.Key_Delete, self.clear_selected_cells)
        add_shortcut(QtCore.Qt.Key_Backspace, self.clear_selected_cells)
        add_shortcut("Ctrl+D", self.fill_down)
        add_shortcut("Ctrl+R", self.fill_right)

    def _install_table_application_shortcut_filter(self):
        # Nexus also has workspace/global actions for common edit shortcuts.
        # Those can receive Ctrl+C/X/Z/Y before a focused table/editor sees them,
        # especially when the table lives inside the properties panel.  A lightweight
        # application event filter lets the active table accept ShortcutOverride and
        # KeyPress events first, but only while focus is inside this table.
        app = QtWidgets.QApplication.instance()
        if app is not None and not getattr(self, "_nexus_table_app_filter_installed", False):
            app.installEventFilter(self)
            self._nexus_table_app_filter_installed = True

    def _focus_widget_inside_table(self):
        focus = QtWidgets.QApplication.focusWidget()
        if focus is None:
            return None
        if focus is self or focus is self.viewport():
            return focus
        try:
            if self.isAncestorOf(focus):
                return focus
        except Exception:
            pass
        return None

    def _standard_table_shortcut_kind(self, event):
        if not isinstance(event, QtGui.QKeyEvent):
            return None
        try:
            if event.matches(QtGui.QKeySequence.Copy):
                return "copy"
            if event.matches(QtGui.QKeySequence.Cut):
                return "cut"
            if event.matches(QtGui.QKeySequence.Paste):
                return "paste"
            if event.matches(QtGui.QKeySequence.Undo):
                return "undo"
            if event.matches(QtGui.QKeySequence.Redo):
                return "redo"
            if event.matches(QtGui.QKeySequence.SelectAll):
                return "select_all"
        except Exception:
            pass
        modifiers = event.modifiers()
        if not (modifiers & (QtCore.Qt.ControlModifier | QtCore.Qt.MetaModifier)):
            return None
        key = event.key()
        shift = bool(modifiers & QtCore.Qt.ShiftModifier)
        if key == QtCore.Qt.Key_C and not shift:
            return "copy"
        if key == QtCore.Qt.Key_X and not shift:
            return "cut"
        if key == QtCore.Qt.Key_V and not shift:
            return "paste"
        if key == QtCore.Qt.Key_A and not shift:
            return "select_all"
        if key == QtCore.Qt.Key_Z:
            return "redo" if shift else "undo"
        if key == QtCore.Qt.Key_Y and not shift:
            return "redo"
        return None

    def _dispatch_table_shortcut(self, kind):
        if kind == "copy":
            self._shortcut_copy_selection(); return True
        if kind == "cut":
            self._shortcut_cut_selection(); return True
        if kind == "paste":
            self._shortcut_paste_clipboard(); return True
        if kind == "undo":
            self._shortcut_undo(); return True
        if kind == "redo":
            self._shortcut_redo(); return True
        if kind == "select_all":
            self._shortcut_select_all(); return True
        return False

    def _cell_editor_has_focus(self):
        focus = QtWidgets.QApplication.focusWidget()
        if focus is None or focus is self or focus is self.viewport():
            return False
        if self.state() != QtWidgets.QAbstractItemView.EditingState:
            return False
        try:
            return self.isAncestorOf(focus)
        except Exception:
            return False

    def _shortcut_copy_selection(self):
        # While actively editing a cell, preserve normal text-editor shortcuts.
        if self._cell_editor_has_focus():
            focus = QtWidgets.QApplication.focusWidget()
            if hasattr(focus, "copy"):
                focus.copy()
            return
        self.copy_selection()

    def _shortcut_cut_selection(self):
        if self._cell_editor_has_focus():
            focus = QtWidgets.QApplication.focusWidget()
            if hasattr(focus, "cut"):
                focus.cut()
            return
        self.cut_selection()

    def _shortcut_paste_clipboard(self):
        if self._cell_editor_has_focus():
            focus = QtWidgets.QApplication.focusWidget()
            if hasattr(focus, "paste"):
                focus.paste()
            return
        self.paste_clipboard()

    def _shortcut_undo(self):
        if self._cell_editor_has_focus():
            focus = QtWidgets.QApplication.focusWidget()
            if hasattr(focus, "undo"):
                focus.undo()
                return
        self.undo_table()

    def _shortcut_redo(self):
        if self._cell_editor_has_focus():
            focus = QtWidgets.QApplication.focusWidget()
            if hasattr(focus, "redo"):
                focus.redo()
                return
        self.redo_table()

    def _shortcut_select_all(self):
        if self._cell_editor_has_focus():
            focus = QtWidgets.QApplication.focusWidget()
            if hasattr(focus, "selectAll"):
                focus.selectAll()
            return
        self.selectAll()
        self.viewport().update()

    def _table_visual_bounds_rect(self, bounds):
        if bounds is None:
            return QtCore.QRect()
        r0, r1, c0, c1 = bounds
        if self.rowCount() <= 0 or self.columnCount() <= 0:
            return QtCore.QRect()
        r0 = max(0, min(self.rowCount() - 1, r0))
        r1 = max(0, min(self.rowCount() - 1, r1))
        c0 = max(0, min(self.columnCount() - 1, c0))
        c1 = max(0, min(self.columnCount() - 1, c1))
        rect = QtCore.QRect()
        for row in range(r0, r1 + 1):
            if self.isRowHidden(row):
                continue
            for col in range(c0, c1 + 1):
                if self.isColumnHidden(col):
                    continue
                cell_rect = self.visualRect(self.model().index(row, col))
                if cell_rect.isValid():
                    rect = cell_rect if rect.isNull() else rect.united(cell_rect)
        return rect

    def _selection_handle_rect(self):
        if not self._nexus_table_capabilities.get("spreadsheet", False):
            return QtCore.QRect()
        rect = self._table_visual_bounds_rect(self._selected_bounds())
        if rect.isNull():
            return QtCore.QRect()
        size = 7
        return QtCore.QRect(rect.right() - size + 1, rect.bottom() - size + 1, size, size)

    def _coerce_number(self, value):
        try:
            text = str(value).strip()
            if not text:
                return None
            return float(text)
        except Exception:
            return None

    def _format_fill_value(self, value, template_text=""):
        number = self._coerce_number(value)
        if number is None:
            return str(value)
        template = str(template_text or "")
        if template and "." not in template and abs(number - int(number)) < 1e-9:
            return str(int(number))
        return str(number).rstrip("0").rstrip(".") if "." in str(number) else str(number)

    def _fill_value_for(self, source_values, offset):
        values = ["" if v is None else str(v) for v in source_values]
        if not values:
            return ""
        numbers = [self._coerce_number(v) for v in values]
        if len(values) >= 2 and all(n is not None for n in numbers):
            step = numbers[-1] - numbers[-2]
            return self._format_fill_value(numbers[-1] + step * (offset + 1), values[-1])
        if len(values) == 1:
            return values[0]
        return values[offset % len(values)]

    def _apply_drag_fill(self, source_bounds, target_row, target_col):
        if source_bounds is None:
            return
        r0, r1, c0, c1 = source_bounds
        if self.rowCount() <= 0 or self.columnCount() <= 0:
            return
        target_row = max(0, min(self.rowCount() - 1, int(target_row)))
        target_col = max(0, min(self.columnCount() - 1, int(target_col)))
        if r0 <= target_row <= r1 and c0 <= target_col <= c1:
            return

        down = target_row - r1
        up = r0 - target_row
        right = target_col - c1
        left = c0 - target_col
        candidates = [(down, "down"), (up, "up"), (right, "right"), (left, "left")]
        distance, direction = max(candidates, key=lambda item: item[0])
        if distance <= 0:
            return

        self._push_table_undo()
        self._bulk_table_mutation = True
        try:
            if direction == "down":
                for col in range(c0, c1 + 1):
                    source_values = [self.item(row, col).text() if self.item(row, col) else "" for row in range(r0, r1 + 1)]
                    for offset, row in enumerate(range(r1 + 1, target_row + 1)):
                        self.setItem(row, col, QtWidgets.QTableWidgetItem(self._fill_value_for(source_values, offset)))
                self.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(r0, c0, target_row, c1), True)
            elif direction == "up":
                for col in range(c0, c1 + 1):
                    source_values = [self.item(row, col).text() if self.item(row, col) else "" for row in range(r1, r0 - 1, -1)]
                    for offset, row in enumerate(range(r0 - 1, target_row - 1, -1)):
                        self.setItem(row, col, QtWidgets.QTableWidgetItem(self._fill_value_for(source_values, offset)))
                self.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(target_row, c0, r1, c1), True)
            elif direction == "right":
                for row in range(r0, r1 + 1):
                    source_values = [self.item(row, col).text() if self.item(row, col) else "" for col in range(c0, c1 + 1)]
                    for offset, col in enumerate(range(c1 + 1, target_col + 1)):
                        self.setItem(row, col, QtWidgets.QTableWidgetItem(self._fill_value_for(source_values, offset)))
                self.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(r0, c0, r1, target_col), True)
            elif direction == "left":
                for row in range(r0, r1 + 1):
                    source_values = [self.item(row, col).text() if self.item(row, col) else "" for col in range(c1, c0 - 1, -1)]
                    for offset, col in enumerate(range(c0 - 1, target_col - 1, -1)):
                        self.setItem(row, col, QtWidgets.QTableWidgetItem(self._fill_value_for(source_values, offset)))
                self.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(r0, target_col, r1, c1), True)
        finally:
            self._bulk_table_mutation = False
            self._last_table_snapshot = self._table_snapshot()
            self.viewport().update()
        self.tableDataChanged.emit()

    def _draw_excel_selection_overlay(self, painter):
        if not self._nexus_table_capabilities.get("spreadsheet", False):
            return
        bounds = self._selected_bounds()
        if bounds is None:
            return
        selection_rect = self._table_visual_bounds_rect(bounds)
        if selection_rect.isNull():
            return

        palette = self.palette()
        base = QtGui.QColor(palette.highlight().color())
        fill = QtGui.QColor(base)
        fill.setAlpha(55)
        border = QtGui.QColor(base)
        border.setAlpha(230)
        active = QtGui.QColor(palette.text().color())
        active.setAlpha(220)

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        painter.fillRect(selection_rect.adjusted(1, 1, -1, -1), fill)
        pen = QtGui.QPen(border, 2)
        painter.setPen(pen)
        painter.drawRect(selection_rect.adjusted(1, 1, -2, -2))

        current = self.currentIndex()
        if current.isValid():
            current_rect = self.visualRect(current)
            if current_rect.isValid():
                painter.setPen(QtGui.QPen(active, 1))
                painter.drawRect(current_rect.adjusted(1, 1, -2, -2))

        handle_rect = self._selection_handle_rect()
        if handle_rect.isValid() and not handle_rect.isNull():
            painter.fillRect(handle_rect, border)
            painter.setPen(QtGui.QPen(palette.base().color(), 1))
            painter.drawRect(handle_rect.adjusted(0, 0, -1, -1))

        if self._drag_fill_active and self._drag_fill_target is not None and self._drag_fill_source_bounds is not None:
            sr0, sr1, sc0, sc1 = self._drag_fill_source_bounds
            tr, tc = self._drag_fill_target
            preview_bounds = (min(sr0, tr), max(sr1, tr), min(sc0, tc), max(sc1, tc))
            preview_rect = self._table_visual_bounds_rect(preview_bounds)
            if preview_rect.isValid() and not preview_rect.isNull():
                dash = QtGui.QPen(border, 1, QtCore.Qt.DashLine)
                painter.setPen(dash)
                painter.drawRect(preview_rect.adjusted(3, 3, -4, -4))
        painter.restore()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._nexus_table_capabilities.get("spreadsheet", False):
            painter = QtGui.QPainter(self.viewport())
            self._draw_excel_selection_overlay(painter)
            painter.end()

    def mousePressEvent(self, event):
        if (
            event.button() == QtCore.Qt.LeftButton
            and self._nexus_table_capabilities.get("spreadsheet", False)
            and self._selection_handle_rect().contains(event.pos())
        ):
            self._drag_fill_active = True
            self._drag_fill_source_bounds = self._selected_bounds()
            self._drag_fill_target = None
            self.setCursor(QtCore.Qt.CrossCursor)
            event.accept()
            return
        super().mousePressEvent(event)
        self.viewport().update()

    def mouseMoveEvent(self, event):
        if self._drag_fill_active:
            index = self.indexAt(event.pos())
            if index.isValid():
                self._drag_fill_target = (index.row(), index.column())
                self.viewport().update()
            event.accept()
            return
        hover = self._selection_handle_rect().contains(event.pos())
        if hover != getattr(self, "_drag_fill_hover_handle", False):
            self._drag_fill_hover_handle = hover
            self.setCursor(QtCore.Qt.CrossCursor if hover else QtCore.Qt.ArrowCursor)
        super().mouseMoveEvent(event)
        self.viewport().update()

    def mouseReleaseEvent(self, event):
        if self._drag_fill_active:
            target = self._drag_fill_target
            source = self._drag_fill_source_bounds
            self._drag_fill_active = False
            self._drag_fill_source_bounds = None
            self._drag_fill_target = None
            self.unsetCursor()
            if target is not None:
                self._apply_drag_fill(source, target[0], target[1])
            event.accept()
            return
        super().mouseReleaseEvent(event)
        self.viewport().update()

    def leaveEvent(self, event):
        if not self._drag_fill_active:
            self._drag_fill_hover_handle = False
            self.unsetCursor()
        super().leaveEvent(event)

    def copy_selection(self):
        if not self._nexus_table_capabilities.get("clipboard", True):
            return
        bounds = self._selected_bounds()
        if bounds is None:
            return
        r0, r1, c0, c1 = bounds
        lines = []
        for r in range(r0, r1 + 1):
            values = []
            for c in range(c0, c1 + 1):
                item = self.item(r, c)
                values.append(item.text() if item else "")
            lines.append("\t".join(values))
        QtWidgets.QApplication.clipboard().setText("\n".join(lines))

    def cut_selection(self):
        if not self._nexus_table_capabilities.get("clipboard", True):
            return
        self.copy_selection()
        self.clear_selected_cells()

    def paste_clipboard(self):
        if not self._nexus_table_capabilities.get("clipboard", True):
            return
        text = QtWidgets.QApplication.clipboard().text()
        if not text:
            return
        self._push_table_undo()
        self._bulk_table_mutation = True
        try:
            start = self.currentIndex()
            row0 = max(0, start.row())
            col0 = max(0, start.column())
            rows = [line.split("\t") for line in text.splitlines()]
            needed_rows = row0 + len(rows)
            needed_cols = col0 + max((len(row) for row in rows), default=0)
            if needed_rows > self.rowCount():
                self.setRowCount(needed_rows)
            if needed_cols > self.columnCount():
                old_cols = self.columnCount()
                self.setColumnCount(needed_cols)
                for col in range(old_cols, needed_cols):
                    self.setHorizontalHeaderItem(col, QtWidgets.QTableWidgetItem(f"Column {col + 1}"))
            for dr, row in enumerate(rows):
                for dc, value in enumerate(row):
                    self.setItem(row0 + dr, col0 + dc, QtWidgets.QTableWidgetItem(value))
        finally:
            self._bulk_table_mutation = False
            self._last_table_snapshot = self._table_snapshot()
        self.tableDataChanged.emit()
        self.structureChanged.emit()

    def clear_selected_cells(self):
        self._push_table_undo()
        self._bulk_table_mutation = True
        try:
            indexes = self.selectedIndexes()
            if not indexes and self.currentRow() >= 0 and self.currentColumn() >= 0:
                indexes = [self.currentIndex()]
            for index in indexes:
                item = self.item(index.row(), index.column())
                if item is None:
                    item = QtWidgets.QTableWidgetItem("")
                    self.setItem(index.row(), index.column(), item)
                item.setText("")
        finally:
            self._bulk_table_mutation = False
            self._last_table_snapshot = self._table_snapshot()
        self.tableDataChanged.emit()

    def fill_down(self):
        bounds = self._selected_bounds()
        if bounds is None:
            return
        r0, r1, c0, c1 = bounds
        if r1 <= r0:
            return
        self._push_table_undo()
        self._bulk_table_mutation = True
        try:
            for c in range(c0, c1 + 1):
                source = self.item(r0, c)
                value = source.text() if source else ""
                for r in range(r0 + 1, r1 + 1):
                    self.setItem(r, c, QtWidgets.QTableWidgetItem(value))
        finally:
            self._bulk_table_mutation = False
            self._last_table_snapshot = self._table_snapshot()
        self.tableDataChanged.emit()

    def fill_right(self):
        bounds = self._selected_bounds()
        if bounds is None:
            return
        r0, r1, c0, c1 = bounds
        if c1 <= c0:
            return
        self._push_table_undo()
        self._bulk_table_mutation = True
        try:
            for r in range(r0, r1 + 1):
                source = self.item(r, c0)
                value = source.text() if source else ""
                for c in range(c0 + 1, c1 + 1):
                    self.setItem(r, c, QtWidgets.QTableWidgetItem(value))
        finally:
            self._bulk_table_mutation = False
            self._last_table_snapshot = self._table_snapshot()
        self.tableDataChanged.emit()

    def insert_row_at_selection(self):
        if not self._nexus_table_capabilities.get("structure_edit", False):
            return
        self._push_table_undo()
        row = self.currentRow()
        self.insertRow(row if row >= 0 else self.rowCount())
        self._last_table_snapshot = self._table_snapshot()
        self.structureChanged.emit()

    def append_row(self):
        if not self._nexus_table_capabilities.get("structure_edit", False):
            return
        self._push_table_undo()
        self.insertRow(self.rowCount())
        self._last_table_snapshot = self._table_snapshot()
        self.structureChanged.emit()

    def delete_selected_rows(self):
        if not self._nexus_table_capabilities.get("structure_edit", False):
            return
        rows = sorted({i.row() for i in self.selectedIndexes()}, reverse=True)
        if not rows and self.currentRow() >= 0:
            rows = [self.currentRow()]
        if not rows:
            return
        self._push_table_undo()
        for row in rows:
            self.removeRow(row)
        self._last_table_snapshot = self._table_snapshot()
        self.structureChanged.emit()

    def insert_column_at_selection(self):
        if not self._nexus_table_capabilities.get("structure_edit", False):
            return
        self._push_table_undo()
        col = self.currentColumn()
        insert_at = col if col >= 0 else self.columnCount()
        self.insertColumn(insert_at)
        self.setHorizontalHeaderItem(insert_at, QtWidgets.QTableWidgetItem(self._unique_header_name(f"Column {insert_at + 1}")))
        self._last_table_snapshot = self._table_snapshot()
        self.structureChanged.emit()

    def delete_selected_columns(self):
        if not self._nexus_table_capabilities.get("structure_edit", False):
            return
        cols = sorted({i.column() for i in self.selectedIndexes()}, reverse=True)
        if not cols and self.currentColumn() >= 0:
            cols = [self.currentColumn()]
        if not cols:
            return
        self._push_table_undo()
        for col in cols:
            self.removeColumn(col)
        self._last_table_snapshot = self._table_snapshot()
        self.structureChanged.emit()

    def _unique_header_name(self, base, skip_col=None):
        base = str(base or "Column").strip() or "Column"
        existing = {
            self.horizontalHeaderItem(c).text()
            for c in range(self.columnCount())
            if c != skip_col and self.horizontalHeaderItem(c) is not None
        }
        candidate = base
        suffix = 2
        while candidate in existing:
            candidate = f"{base}_{suffix}"
            suffix += 1
        return candidate

    def _begin_header_inline_edit(self, column_index):
        if column_index < 0 or column_index >= self.columnCount():
            return
        header = self.horizontalHeader()
        item = self.horizontalHeaderItem(column_index)
        old_name = item.text() if item else f"Column {column_index + 1}"
        editor = QtWidgets.QLineEdit(header)
        editor.setText(old_name)
        editor.selectAll()
        editor.setFrame(True)
        x = header.sectionViewportPosition(column_index)
        w = header.sectionSize(column_index)
        editor.setGeometry(x + 1, 1, max(40, w - 2), max(20, header.height() - 2))
        editor.show()
        editor.setFocus(QtCore.Qt.MouseFocusReason)

        committed = {"done": False}

        def finish(accept=True):
            if committed["done"]:
                return
            committed["done"] = True
            text = editor.text() if accept else old_name
            editor.deleteLater()
            if not accept:
                return
            self._commit_column_rename(column_index, old_name, text)

        editor.editingFinished.connect(lambda: finish(True))
        editor._nexus_header_filter = _HeaderRenameEventFilter(editor, finish)
        editor.installEventFilter(editor._nexus_header_filter)

    def _commit_column_rename(self, column_index, old_name, requested_name):
        new_name = self._unique_header_name(str(requested_name or "").strip(), skip_col=column_index)
        if not new_name or new_name == old_name:
            return
        self._push_table_undo()
        self.setHorizontalHeaderItem(column_index, QtWidgets.QTableWidgetItem(new_name))
        self._last_table_snapshot = self._table_snapshot()
        self.columnRenamed.emit(column_index, old_name, new_name)
        self.structureChanged.emit()

    def rename_column_at_index(self, column_index):
        if not self._nexus_table_capabilities.get("column_rename", True):
            return
        self._begin_header_inline_edit(column_index)

    def _move_current_cell(self, delta_row=0, delta_col=0):
        if self.rowCount() <= 0 or self.columnCount() <= 0:
            return
        row = self.currentRow() if self.currentRow() >= 0 else 0
        col = self.currentColumn() if self.currentColumn() >= 0 else 0
        row = max(0, min(self.rowCount() - 1, row + delta_row))
        col = max(0, min(self.columnCount() - 1, col + delta_col))
        self.setCurrentCell(row, col)

    def keyPressEvent(self, event):
        shortcut_kind = self._standard_table_shortcut_kind(event)
        if shortcut_kind is not None:
            self._dispatch_table_shortcut(shortcut_kind); return
        if event.key() == QtCore.Qt.Key_Delete:
            self.clear_selected_cells(); return
        if self.state() != QtWidgets.QAbstractItemView.EditingState:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self._move_current_cell(-1 if event.modifiers() & QtCore.Qt.ShiftModifier else 1, 0); return
            if event.key() == QtCore.Qt.Key_Tab:
                self._move_current_cell(0, -1 if event.modifiers() & QtCore.Qt.ShiftModifier else 1); return
            if event.key() == QtCore.Qt.Key_Backtab:
                self._move_current_cell(0, -1); return
            if event.key() == QtCore.Qt.Key_F2 and self.currentItem() is not None:
                self.editItem(self.currentItem()); return
            text = event.text()
            modifiers = event.modifiers()
            if (
                self._nexus_table_capabilities.get("editable", False)
                and text
                and text >= " "
                and not (modifiers & (QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier | QtCore.Qt.MetaModifier))
                and self.currentRow() >= 0
                and self.currentColumn() >= 0
            ):
                row = self.currentRow()
                col = self.currentColumn()
                item = self.item(row, col)
                if item is None:
                    item = QtWidgets.QTableWidgetItem("")
                    self.setItem(row, col, item)
                self._push_table_undo(getattr(self, "_last_table_snapshot", None))
                item.setText(text)
                self.editItem(item)
                return
        super().keyPressEvent(event)

    def sort_current_column(self, order=QtCore.Qt.AscendingOrder):
        if not self._nexus_table_capabilities.get("sorting", True):
            return
        col = self.currentColumn()
        if col < 0:
            col = 0
        self.sortItems(col, order)

    def filter_current_column(self):
        if not self._nexus_table_capabilities.get("filtering", True):
            return
        col = self.currentColumn()
        if col < 0 or col >= self.columnCount():
            return
        text, accepted = QtWidgets.QInputDialog.getText(self, "Filter Column", "Show rows containing:")
        if not accepted:
            return
        self.clear_filters()
        needle = str(text or "").lower()
        if not needle:
            return
        for row in range(self.rowCount()):
            item = self.item(row, col)
            visible = needle in ((item.text() if item else "").lower())
            self.setRowHidden(row, not visible)
            if not visible:
                self._hidden_rows_by_filter.add(row)

    def clear_filters(self):
        for row in range(self.rowCount()):
            self.setRowHidden(row, False)
        self._hidden_rows_by_filter.clear()

    def contextMenuEvent(self, event):
        if not self._nexus_table_capabilities.get("context_menu", True):
            return super().contextMenuEvent(event)
        menu = QtWidgets.QMenu(self)
        menu.addAction("Undo", self.undo_table).setEnabled(bool(self._table_undo_stack))
        menu.addAction("Redo", self.redo_table).setEnabled(bool(self._table_redo_stack))
        menu.addSeparator()
        if self._nexus_table_capabilities.get("clipboard", True):
            menu.addAction("Cut", self.cut_selection)
            menu.addAction("Copy", self.copy_selection)
            menu.addAction("Paste", self.paste_clipboard)
            menu.addAction("Clear Cells", self.clear_selected_cells)
            menu.addAction("Fill Down", self.fill_down)
            menu.addAction("Fill Right", self.fill_right)
        if self._nexus_table_capabilities.get("structure_edit", False):
            menu.addSeparator()
            menu.addAction("Insert Row", self.insert_row_at_selection)
            menu.addAction("Append Row", self.append_row)
            menu.addAction("Delete Row(s)", self.delete_selected_rows)
            menu.addAction("Insert Column", self.insert_column_at_selection)
            menu.addAction("Delete Column(s)", self.delete_selected_columns)
        if self._nexus_table_capabilities.get("column_rename", True) and self.currentColumn() >= 0:
            menu.addAction("Rename Column", lambda: self.rename_column_at_index(self.currentColumn()))
        if self._nexus_table_capabilities.get("sorting", True):
            menu.addSeparator()
            menu.addAction("Sort Ascending", lambda: self.sort_current_column(QtCore.Qt.AscendingOrder))
            menu.addAction("Sort Descending", lambda: self.sort_current_column(QtCore.Qt.DescendingOrder))
        if self._nexus_table_capabilities.get("filtering", True):
            menu.addAction("Filter Column...", self.filter_current_column)
            menu.addAction("Clear Filters", self.clear_filters).setEnabled(bool(self._hidden_rows_by_filter))
        menu.exec_(event.globalPos())

    def set_headers(self, headers):
        self._bulk_table_mutation = True
        try:
            self.setColumnCount(len(headers or []))
            self.setHorizontalHeaderLabels([str(x) for x in headers or []])
        finally:
            self._bulk_table_mutation = False
            self._last_table_snapshot = self._table_snapshot()
        self.structureChanged.emit()
        return self

    def eventFilter(self, watched, event):
        event_type = event.type()
        if event_type in (QtCore.QEvent.ShortcutOverride, QtCore.QEvent.KeyPress):
            if self._focus_widget_inside_table() is not None:
                shortcut_kind = self._standard_table_shortcut_kind(event)
                if shortcut_kind is not None:
                    event.accept()
                    if event_type == QtCore.QEvent.KeyPress:
                        self._dispatch_table_shortcut(shortcut_kind)
                    return True
        return super().eventFilter(watched, event)

    def set_rows(self, rows):
        rows = list(rows or [])
        self._bulk_table_mutation = True
        try:
            self.setRowCount(len(rows))
            max_cols = max((len(row) for row in rows), default=self.columnCount())
            if max_cols > self.columnCount():
                self.setColumnCount(max_cols)
            for r, row in enumerate(rows):
                for c, value in enumerate(row):
                    self.setItem(r, c, QtWidgets.QTableWidgetItem("" if value is None else str(value)))
        finally:
            self._bulk_table_mutation = False
            self._last_table_snapshot = self._table_snapshot()
        self.tableDataChanged.emit()
        return self


class _HeaderRenameEventFilter(QtCore.QObject):
    def __init__(self, editor, finish_callback):
        super().__init__(editor)
        self._finish_callback = finish_callback

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                self._finish_callback(True)
                return True
            if event.key() == QtCore.Qt.Key_Escape:
                self._finish_callback(False)
                return True
        return False


class NexusTableView(NexusTableWidget):
    NEXUS_TYPE_ID = "nexus.table_view"

    def __init__(self, rows=0, columns=0, parent=None, *, object_name="NexusTableView", **kwargs):
        super().__init__(rows, columns, parent, object_name=object_name, edit_triggers=QtWidgets.QAbstractItemView.NoEditTriggers, editable_cells=False, allow_structure_edit=False, **kwargs)


class NexusTableEditor(NexusTableWidget):
    NEXUS_TYPE_ID = "nexus.table_editor"

    def __init__(self, rows=0, columns=0, parent=None, *, object_name="NexusTableEditor", **kwargs):
        edit_triggers = kwargs.pop("edit_triggers", QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed)
        kwargs.setdefault("editable_cells", True)
        kwargs.setdefault("allow_structure_edit", True)
        kwargs.setdefault("spreadsheet_mode", True)
        kwargs.setdefault("selection_behavior", QtWidgets.QAbstractItemView.SelectItems)
        kwargs.setdefault("selection_mode", QtWidgets.QAbstractItemView.ExtendedSelection)
        super().__init__(rows, columns, parent, object_name=object_name, edit_triggers=edit_triggers, **kwargs)


class NexusTextEditor(QtWidgets.QPlainTextEdit, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.text_editor"
    QT_BASE_CLASS = "QPlainTextEdit"

    def __init__(self, parent=None, *, object_name="NexusTextEditor", text="", placeholder="", read_only=False, line_wrap_mode=None, tab_changes_focus=None, maximum_block_count=None, enable_context_menu=True, enable_clipboard=True, enable_formatting=True, enable_search=True, auto_indent=False, tab_width=4, font_size=None, alignment="Left", word_wrap=True, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="input")
        self._nexus_text_capabilities = {}
        self.set_text_capabilities(
            context_menu=enable_context_menu,
            clipboard=enable_clipboard,
            formatting=enable_formatting,
            search=enable_search,
            auto_indent=auto_indent,
            tab_width=tab_width,
            word_wrap=word_wrap,
        )
        if text: self.setPlainText(str(text))
        if placeholder: self.setPlaceholderText(str(placeholder))
        self.setReadOnly(bool(read_only))
        if line_wrap_mode is not None: self.setLineWrapMode(line_wrap_mode)
        if tab_changes_focus is not None: self.setTabChangesFocus(bool(tab_changes_focus))
        if maximum_block_count is not None: self.setMaximumBlockCount(int(maximum_block_count))
        if font_size is not None: self.set_text_font(size=int(font_size))
        self.set_text_alignment(alignment)
        _apply_common_widget_options(self, **kwargs)

    def set_text_capabilities(self, *, context_menu=None, clipboard=None, formatting=None, search=None, auto_indent=None, tab_width=None, word_wrap=None):
        caps = getattr(self, "_nexus_text_capabilities", {}) or {}
        if context_menu is not None: caps["context_menu"] = bool(context_menu)
        if clipboard is not None: caps["clipboard"] = bool(clipboard)
        if formatting is not None: caps["formatting"] = bool(formatting)
        if search is not None: caps["search"] = bool(search)
        if auto_indent is not None: caps["auto_indent"] = bool(auto_indent)
        if tab_width is not None: caps["tab_width"] = max(1, int(tab_width))
        if word_wrap is not None:
            caps["word_wrap"] = bool(word_wrap)
            self.setLineWrapMode(QtWidgets.QPlainTextEdit.WidgetWidth if bool(word_wrap) else QtWidgets.QPlainTextEdit.NoWrap)
        self._nexus_text_capabilities = caps
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu if caps.get("context_menu", True) else QtCore.Qt.NoContextMenu)
        return self

    def set_text_font(self, *, family=None, size=None, bold=None, italic=None, underline=None):
        font = self.font()
        if family: font.setFamily(str(family))
        if size is not None: font.setPointSize(int(size))
        if bold is not None: font.setBold(bool(bold))
        if italic is not None: font.setItalic(bool(italic))
        if underline is not None: font.setUnderline(bool(underline))
        self.setFont(font)
        return self

    def set_text_alignment(self, alignment):
        name = str(alignment or "Left").lower()
        flags = {
            "left": QtCore.Qt.AlignLeft,
            "center": QtCore.Qt.AlignHCenter,
            "right": QtCore.Qt.AlignRight,
            "justify": QtCore.Qt.AlignJustify,
        }.get(name, QtCore.Qt.AlignLeft)
        self.selectAll()
        cursor = self.textCursor()
        block_format = cursor.blockFormat()
        block_format.setAlignment(flags)
        cursor.mergeBlockFormat(block_format)
        cursor.clearSelection()
        self.setTextCursor(cursor)
        return self

    def _find_text_dialog(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "Find", "Find text:")
        if ok and text:
            if not self.find(text):
                cursor = self.textCursor()
                cursor.movePosition(QtGui.QTextCursor.Start)
                self.setTextCursor(cursor)
                self.find(text)

    def keyPressEvent(self, event):
        caps = getattr(self, "_nexus_text_capabilities", {}) or {}
        if event.matches(QtGui.QKeySequence.Cut) and not caps.get("clipboard", True): return
        if event.matches(QtGui.QKeySequence.Copy) and not caps.get("clipboard", True): return
        if event.matches(QtGui.QKeySequence.Paste) and not caps.get("clipboard", True): return
        if event.matches(QtGui.QKeySequence.Find) and caps.get("search", True):
            self._find_text_dialog(); return
        if event.key() == QtCore.Qt.Key_Tab and not self.tabChangesFocus():
            spaces = " " * int(caps.get("tab_width", 4))
            self.insertPlainText(spaces); return
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and caps.get("auto_indent", False):
            cursor = self.textCursor()
            block = cursor.block().text()
            indent = block[:len(block) - len(block.lstrip())]
            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        caps = getattr(self, "_nexus_text_capabilities", {}) or {}
        if not caps.get("context_menu", True):
            return super().contextMenuEvent(event)
        menu = self.createStandardContextMenu()
        if not caps.get("clipboard", True):
            for action in menu.actions():
                if action.text().replace("&", "").lower() in {"cut", "copy", "paste"}:
                    action.setEnabled(False)
        if caps.get("search", True):
            menu.addSeparator()
            menu.addAction("Find...", self._find_text_dialog)
        if caps.get("formatting", True):
            menu.addSeparator()
            menu.addAction("Align Left", lambda: self.set_text_alignment("Left"))
            menu.addAction("Align Center", lambda: self.set_text_alignment("Center"))
            menu.addAction("Align Right", lambda: self.set_text_alignment("Right"))
        menu.exec_(event.globalPos())


class NexusProgressBar(QtWidgets.QProgressBar, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.progress_bar"
    QT_BASE_CLASS = "QProgressBar"

    def __init__(self, parent=None, *, object_name="NexusProgressBar", minimum=None, maximum=None, value=None, text_visible=None, format=None, orientation=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="progress")
        if minimum is not None: self.setMinimum(int(minimum))
        if maximum is not None: self.setMaximum(int(maximum))
        if value is not None: self.setValue(int(value))
        if text_visible is not None: self.setTextVisible(bool(text_visible))
        if format is not None: self.setFormat(str(format))
        if orientation is not None: self.setOrientation(orientation)
        _apply_common_widget_options(self, **kwargs)


class NexusStackedWidget(QtWidgets.QStackedWidget, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.stacked_widget"
    QT_BASE_CLASS = "QStackedWidget"

    def __init__(self, parent=None, *, object_name="NexusStackedWidget", current_index=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="stack")
        if current_index is not None: self.setCurrentIndex(int(current_index))
        _apply_common_widget_options(self, **kwargs)


class NexusScrollArea(QtWidgets.QScrollArea, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.scroll_area"
    QT_BASE_CLASS = "QScrollArea"

    def __init__(self, parent=None, *, object_name="NexusScrollArea", widget_resizable=True, frame_shape=QtWidgets.QFrame.NoFrame, horizontal_scrollbar_policy=None, vertical_scrollbar_policy=None, alignment=None, **kwargs):
        super().__init__(parent)
        self._init_nexus(object_name=object_name, theme_role="scroll")
        self.setWidgetResizable(bool(widget_resizable))
        self.setFrameShape(frame_shape)
        if horizontal_scrollbar_policy is not None: self.setHorizontalScrollBarPolicy(horizontal_scrollbar_policy)
        if vertical_scrollbar_policy is not None: self.setVerticalScrollBarPolicy(vertical_scrollbar_policy)
        if alignment is not None: self.setAlignment(alignment)
        _apply_common_widget_options(self, **kwargs)


class NexusSplitter(QtWidgets.QSplitter, NexusWidgetMixin):
    NEXUS_TYPE_ID = "nexus.splitter"
    QT_BASE_CLASS = "QSplitter"

    def __init__(self, orientation=QtCore.Qt.Horizontal, parent=None, *, object_name="NexusSplitter", children_collapsible=False, opaque_resize=None, handle_width=None, sizes=None, **kwargs):
        super().__init__(orientation, parent)
        self._init_nexus(object_name=object_name, theme_role="splitter")
        self.setChildrenCollapsible(bool(children_collapsible))
        if opaque_resize is not None: self.setOpaqueResize(bool(opaque_resize))
        if handle_width is not None: self.setHandleWidth(int(handle_width))
        if sizes is not None: self.setSizes([int(x) for x in sizes])
        _apply_common_widget_options(self, **kwargs)


class NexusContextMenu(NexusMenu):
    NEXUS_TYPE_ID = "nexus.context_menu"

    def __init__(self, title="", parent=None, *, object_name="NexusContextMenu", **kwargs):
        super().__init__(title=title, parent=parent, object_name=object_name, **kwargs)


class NexusTooltip:
    @staticmethod
    def show_text(global_pos, text: str, widget=None, rect=None, duration_ms: int = -1):
        QtWidgets.QToolTip.showText(global_pos, str(text or ""), widget, rect, duration_ms)

    @staticmethod
    def hide_text():
        QtWidgets.QToolTip.hideText()

    @staticmethod
    def set_tooltip(widget, text: str):
        if widget is not None:
            widget.setToolTip(str(text or ""))
        return widget


def get_nexus_widget_capabilities():
    widgets = [NexusFrame, NexusSection, NexusSubWindow, NexusMenuBar, NexusMenu, NexusLabel, NexusTextInput, NexusButton, NexusCheckBox, NexusRadioButton, NexusSlider, NexusComboBox, NexusSpinBox, NexusDoubleSpinBox, NexusTabWidget, NexusListWidget, NexusTreeWidget, NexusHierarchyView, NexusTableWidget, NexusTableView, NexusTableEditor, NexusTextEditor, NexusProgressBar, NexusStackedWidget, NexusScrollArea, NexusSplitter, NexusContextMenu]
    return {cls.__name__: cls.nexus_capabilities() for cls in widgets}


__all__ = [
    "NexusWidgetMixin", "get_nexus_widget_capabilities", "NexusButton", "NexusCheckBox", "NexusComboBox", "NexusContextMenu", "NexusDoubleSpinBox", "NexusFrame", "NexusHierarchyView", "NexusLabel", "NexusListWidget", "NexusMenu", "NexusMenuBar", "NexusProgressBar", "NexusRadioButton", "NexusScrollArea", "NexusSection", "NexusSlider", "NexusSpinBox", "NexusSplitter", "NexusStackedWidget", "NexusSubWindow", "NexusTabWidget", "NexusTableEditor", "NexusTableView", "NexusTableWidget", "NexusTextEditor", "NexusTextInput", "NexusTooltip", "NexusTreeWidget",
]
