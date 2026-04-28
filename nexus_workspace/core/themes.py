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
# File: themes.py
# Description: Defines theme metadata and helpers for applying visual themes across the application.
#============================================================================

from __future__ import absolute_import

from collections import OrderedDict
from dataclasses import dataclass, field

from nexus_workspace.framework.qt import QtCore


NODE_WIDTH = 180
TITLE_HEIGHT = 28
PORT_RADIUS = 6
PORT_SPACING = 24
NODE_CORNER_RADIUS = 10
GRID_SIZE = 20
RESIZE_MARGIN = 8

ZOOM_MIN = 0.25
ZOOM_MAX = 2.5
ZOOM_STEP = 1.15
FIT_PADDING = 80

SETTINGS_ORG = "OpenAI"
SETTINGS_APP = "PyQt5VisualTestEditorPrototype"
SETTINGS_VERSION = 1


@dataclass
class ThemeTokens:
    colors: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    fonts: dict = field(default_factory=dict)


@dataclass
class ThemeDefinition:
    id: str
    display_name: str
    category: str
    is_dark: bool
    tokens: ThemeTokens


DEFAULT_METRICS = {
    "radius_sm": 3,
    "radius_md": 4,
    "radius_lg": 8,
    "border_width": 1,
    "focus_width": 1,
    "tab_height": 28,
    "toolbar_height": 28,
}


def _merge_dicts(base, overrides):
    merged = dict(base)
    merged.update(overrides or {})
    return merged


def _theme_colors(base, overrides=None):
    return _merge_dicts(base, overrides)


BASE_DARK = {
    "app_bg": "#1E1E1E",
    "window_bg": "#1E1E1E",
    "panel_bg": "#2B2B2B",
    "panel_alt_bg": "#252526",
    "input_bg": "#252526",
    "menu_bg": "#2B2B2B",
    "toolbar_bg": "#2B2B2B",
    "tab_bg": "#2B2B2B",
    "tab_active_bg": "#3C78D8",
    "tab_inactive_close_bg": "rgba(255, 255, 255, 0.10)",
    "scrollbar_bg": "#23252B",
    "scrollbar_handle": "#4A5261",
    "scrollbar_handle_hover": "#5A6476",
    "scrollbar_handle_pressed": "#6B7790",
    "scrollbar_border": "#3A404C",
    "text": "#F0F0F0",
    "muted_text": "#C8C8C8",
    "disabled_text": "#8F8F8F",
    "placeholder_text": "#9A9A9A",
    "border": "#555555",
    "border_strong": "#707070",
    "separator": "#555555",
    "accent": "#3C78D8",
    "accent_alt": "#F5C542",
    "accent_hover": "#4B89EA",
    "accent_pressed": "#305FAE",
    "accent_text": "#FFFFFF",
    "hover_bg": "#3A3D41",
    "pressed_bg": "#32353A",
    "focus_ring": "#3C78D8",
    "selection_bg": "#3C78D8",
    "selection_text": "#FFFFFF",
    "success": "#2FA572",
    "warning": "#F5C542",
    "error": "#E05D5D",
    "info": "#4FC3F7",
    "grid_bg": "#202020",
    "grid_line": "#2C2C2C",
    "grid_minor": "#2C2C2C",
    "grid_major": "#3A3A3A",
    "node_bg": "#2B2B2B",
    "node_title": "#3C78D8",
    "node_border": "#555555",
    "node_selected": "#F5C542",
    "node_selected_border": "#F5C542",
    "port_input": "#81C784",
    "port_output": "#4FC3F7",
    "connection": "#E0E0E0",
    "wire": "#E0E0E0",
    "wire_selected": "#F5C542",
    "titlebar_bg": "#252526",
    "titlebar_button_hover": "#3A3D41",
    "titlebar_close_hover": "#C42B1C",
    "table_header_bg": "#2B2B2B",
    "table_header_text": "#F0F0F0",
    "table_grid": "#555555",
    "table_selection_bg": "#3C78D8",
    "table_selection_border": "#F5C542",
    "current_cell_bg": "rgba(60, 120, 216, 0.18)",
    "current_cell_border": "#F5C542",
    "editor_bg": "#252526",
    "editor_text": "#F0F0F0",
}

BASE_LIGHT = {
    "app_bg": "#F5F7FA",
    "window_bg": "#F5F7FA",
    "panel_bg": "#FFFFFF",
    "panel_alt_bg": "#F0F2F5",
    "input_bg": "#F0F2F5",
    "menu_bg": "#FFFFFF",
    "toolbar_bg": "#FFFFFF",
    "tab_bg": "#FFFFFF",
    "tab_active_bg": "#3B82F6",
    "tab_inactive_close_bg": "rgba(0, 0, 0, 0.08)",
    "scrollbar_bg": "#E6EBF2",
    "scrollbar_handle": "#B2BCCB",
    "scrollbar_handle_hover": "#9CA7B9",
    "scrollbar_handle_pressed": "#8895A8",
    "scrollbar_border": "#D2D9E3",
    "text": "#1F2933",
    "muted_text": "#52606D",
    "disabled_text": "#8A99A6",
    "placeholder_text": "#7B8794",
    "border": "#CBD2D9",
    "border_strong": "#AEB7C0",
    "separator": "#D9E2EC",
    "accent": "#3B82F6",
    "accent_alt": "#14B8A6",
    "accent_hover": "#2563EB",
    "accent_pressed": "#1D4ED8",
    "accent_text": "#FFFFFF",
    "hover_bg": "#E5E7EB",
    "pressed_bg": "#D9DEE4",
    "focus_ring": "#3B82F6",
    "selection_bg": "#3B82F6",
    "selection_text": "#FFFFFF",
    "success": "#22C55E",
    "warning": "#D97706",
    "error": "#DC2626",
    "info": "#0EA5E9",
    "grid_bg": "#F8FAFC",
    "grid_line": "#E2E8F0",
    "grid_minor": "#E2E8F0",
    "grid_major": "#CBD5E1",
    "node_bg": "#FFFFFF",
    "node_title": "#3B82F6",
    "node_border": "#CBD2D9",
    "node_selected": "#14B8A6",
    "node_selected_border": "#14B8A6",
    "port_input": "#22C55E",
    "port_output": "#0EA5E9",
    "connection": "#334155",
    "wire": "#334155",
    "wire_selected": "#14B8A6",
    "titlebar_bg": "#FFFFFF",
    "titlebar_button_hover": "#E5E7EB",
    "titlebar_close_hover": "#F87171",
    "table_header_bg": "#FFFFFF",
    "table_header_text": "#1F2933",
    "table_grid": "#CBD2D9",
    "table_selection_bg": "#3B82F6",
    "table_selection_border": "#1D4ED8",
    "current_cell_bg": "rgba(59, 130, 246, 0.10)",
    "current_cell_border": "#1D4ED8",
    "editor_bg": "#F0F2F5",
    "editor_text": "#1F2933",
}


def _theme_definition(theme_id, display_name, category, is_dark, base_colors, overrides):
    colors = _theme_colors(base_colors, overrides)
    return ThemeDefinition(
        id=theme_id,
        display_name=display_name,
        category=category,
        is_dark=is_dark,
        tokens=ThemeTokens(colors=colors, metrics=dict(DEFAULT_METRICS), fonts={}),
    )


def _hex_to_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return '#{0:02X}{1:02X}{2:02X}'.format(*rgb)


def _blend(color_a, color_b, amount):
    rgb_a = _hex_to_rgb(color_a)
    rgb_b = _hex_to_rgb(color_b)
    mixed = []
    for idx in range(3):
        mixed.append(int(round(rgb_a[idx] + (rgb_b[idx] - rgb_a[idx]) * amount)))
    return _rgb_to_hex(tuple(mixed))


def _with_alpha(hex_color, alpha):
    rgb = _hex_to_rgb(hex_color)
    return 'rgba({0}, {1}, {2}, {3:.2f})'.format(rgb[0], rgb[1], rgb[2], alpha)


def _balanced_theme(theme_id, display_name, category, is_dark, palette):
    base = BASE_DARK if is_dark else BASE_LIGHT
    app_bg = palette['app_bg']
    panel_bg = palette['panel_bg']
    panel_alt_bg = palette['panel_alt_bg']
    input_bg = palette.get('input_bg', panel_alt_bg)
    text = palette['text']
    muted_text = palette['muted_text']
    border = palette['border']
    accent = palette['accent']
    accent_alt = palette['accent_alt']
    selection_bg = palette.get('selection_bg', _blend(accent, panel_bg, 0.35 if is_dark else 0.22))
    selection_text = palette.get('selection_text', '#FFFFFF' if is_dark else '#FFFFFF')
    titlebar_bg = palette.get('titlebar_bg', panel_alt_bg)
    close_hover = palette.get('titlebar_close_hover', palette.get('error', '#D64D4D' if is_dark else '#DC2626'))
    button_hover = palette.get('titlebar_button_hover', _blend(panel_bg, '#FFFFFF' if is_dark else '#000000', 0.10 if is_dark else 0.08))
    grid_bg = palette.get('grid_bg', panel_alt_bg)
    grid_minor = palette.get('grid_minor', _blend(grid_bg, '#FFFFFF' if is_dark else '#000000', 0.07 if is_dark else 0.08))
    grid_major = palette.get('grid_major', _blend(grid_bg, '#FFFFFF' if is_dark else '#000000', 0.15 if is_dark else 0.16))
    node_bg = palette.get('node_bg', panel_bg)
    node_title = palette.get('node_title', accent)
    node_border = palette.get('node_border', border)
    node_selected = palette.get('node_selected', accent_alt)
    port_input = palette.get('port_input', palette.get('success', '#6EE7B7' if is_dark else '#22C55E'))
    port_output = palette.get('port_output', palette.get('info', accent))
    connection = palette.get('connection', _blend(text, accent, 0.18))
    table_header_bg = palette.get('table_header_bg', panel_bg)
    table_selection_bg = palette.get('table_selection_bg', selection_bg)
    table_selection_border = palette.get('table_selection_border', accent_alt)
    editor_bg = palette.get('editor_bg', input_bg)
    disabled_text = palette.get('disabled_text', _blend(muted_text, panel_bg if is_dark else app_bg, 0.35))
    placeholder_text = palette.get('placeholder_text', _blend(muted_text, text, 0.25))
    hover_bg = palette.get('hover_bg', _blend(panel_bg, '#FFFFFF' if is_dark else '#000000', 0.10 if is_dark else 0.06))
    pressed_bg = palette.get('pressed_bg', _blend(panel_bg, '#FFFFFF' if is_dark else '#000000', 0.16 if is_dark else 0.12))
    tab_inactive_close_bg = palette.get('tab_inactive_close_bg', 'rgba(255, 255, 255, 0.12)' if is_dark else 'rgba(0, 0, 0, 0.08)')
    scrollbar_bg = palette.get('scrollbar_bg', _blend(panel_alt_bg, panel_bg, 0.45 if is_dark else 0.35))
    scrollbar_handle = palette.get('scrollbar_handle', _blend(accent, panel_bg if is_dark else panel_alt_bg, 0.55 if is_dark else 0.72))
    scrollbar_handle_hover = palette.get('scrollbar_handle_hover', _blend(scrollbar_handle, '#FFFFFF' if is_dark else '#000000', 0.12 if is_dark else 0.08))
    scrollbar_handle_pressed = palette.get('scrollbar_handle_pressed', _blend(scrollbar_handle, '#FFFFFF' if is_dark else '#000000', 0.22 if is_dark else 0.16))
    scrollbar_border = palette.get('scrollbar_border', _blend(border, app_bg, 0.18))
    overrides = {
        'app_bg': app_bg,
        'window_bg': app_bg,
        'panel_bg': panel_bg,
        'panel_alt_bg': panel_alt_bg,
        'input_bg': input_bg,
        'menu_bg': panel_bg,
        'toolbar_bg': panel_bg,
        'tab_bg': panel_bg,
        'tab_active_bg': accent,
        'tab_inactive_close_bg': tab_inactive_close_bg,
        'scrollbar_bg': scrollbar_bg,
        'scrollbar_handle': scrollbar_handle,
        'scrollbar_handle_hover': scrollbar_handle_hover,
        'scrollbar_handle_pressed': scrollbar_handle_pressed,
        'scrollbar_border': scrollbar_border,
        'text': text,
        'muted_text': muted_text,
        'disabled_text': disabled_text,
        'placeholder_text': placeholder_text,
        'border': border,
        'border_strong': palette.get('border_strong', _blend(border, '#FFFFFF' if is_dark else '#000000', 0.18 if is_dark else 0.15)),
        'separator': palette.get('separator', _blend(border, app_bg, 0.20)),
        'accent': accent,
        'accent_alt': accent_alt,
        'accent_hover': palette.get('accent_hover', _blend(accent, '#FFFFFF', 0.12 if is_dark else 0.08)),
        'accent_pressed': palette.get('accent_pressed', _blend(accent, '#000000', 0.18 if is_dark else 0.12)),
        'accent_text': palette.get('accent_text', '#FFFFFF' if is_dark else '#FFFFFF'),
        'hover_bg': hover_bg,
        'pressed_bg': pressed_bg,
        'focus_ring': palette.get('focus_ring', accent),
        'selection_bg': selection_bg,
        'selection_text': selection_text,
        'success': palette.get('success', '#2FA572' if is_dark else '#22C55E'),
        'warning': palette.get('warning', '#F5C542' if is_dark else '#D97706'),
        'error': palette.get('error', '#E05D5D' if is_dark else '#DC2626'),
        'info': palette.get('info', port_output),
        'grid_bg': grid_bg,
        'grid_line': grid_minor,
        'grid_minor': grid_minor,
        'grid_major': grid_major,
        'node_bg': node_bg,
        'node_title': node_title,
        'node_border': node_border,
        'node_selected': node_selected,
        'node_selected_border': palette.get('node_selected_border', node_selected),
        'port_input': port_input,
        'port_output': port_output,
        'connection': connection,
        'wire': palette.get('wire', connection),
        'wire_selected': palette.get('wire_selected', node_selected),
        'titlebar_bg': titlebar_bg,
        'titlebar_button_hover': button_hover,
        'titlebar_close_hover': close_hover,
        'table_header_bg': table_header_bg,
        'table_header_text': palette.get('table_header_text', text),
        'table_grid': palette.get('table_grid', border),
        'table_selection_bg': table_selection_bg,
        'table_selection_border': table_selection_border,
        'current_cell_bg': palette.get('current_cell_bg', _with_alpha(accent, 0.18 if is_dark else 0.10)),
        'current_cell_border': palette.get('current_cell_border', accent_alt),
        'editor_bg': editor_bg,
        'editor_text': palette.get('editor_text', text),
    }
    return _theme_definition(theme_id, display_name, category, is_dark, base, overrides)


def _build_builtin_themes():
    specs = [
        ('midnight', 'Midnight', 'Professional', True, {'app_bg':'#1B1D22','panel_bg':'#252932','panel_alt_bg':'#181B21','text':'#E8ECF3','muted_text':'#A9B2C3','border':'#394150','accent':'#4F8EF7','accent_alt':'#F4C84A','port_input':'#6CCF8D','port_output':'#59C2FF','node_selected':'#F4C84A','titlebar_close_hover':'#D95C5C'}),
        ('carbon_pro', 'Carbon Pro', 'Professional', True, {'app_bg':'#16181D','panel_bg':'#20242C','panel_alt_bg':'#111318','text':'#E6E9EF','muted_text':'#A7AFBD','border':'#323947','accent':'#6A8DFF','accent_alt':'#52D2C2','port_input':'#84D39B','port_output':'#6A8DFF','node_selected':'#52D2C2','titlebar_close_hover':'#D15C6A'}),
        ('arctic_glass', 'Arctic Glass', 'Professional', False, {'app_bg':'#EEF3F8','panel_bg':'#FFFFFF','panel_alt_bg':'#E8EEF5','text':'#233142','muted_text':'#607080','border':'#CAD5E2','accent':'#4A7DFF','accent_alt':'#2CB1BC','port_input':'#40B36C','port_output':'#3B82F6','node_selected':'#2CB1BC','titlebar_close_hover':'#E26767'}),
        ('warm_paper', 'Warm Paper', 'Professional', False, {'app_bg':'#F8F3EA','panel_bg':'#FFFCF6','panel_alt_bg':'#F1E9DB','text':'#3E352E','muted_text':'#76695E','border':'#D9CEBF','accent':'#C47A4A','accent_alt':'#6E9F72','port_input':'#6E9F72','port_output':'#C47A4A','node_selected':'#6E9F72','titlebar_close_hover':'#D56B6B'}),
        ('slate', 'Slate', 'Professional', True, {'app_bg':'#20242B','panel_bg':'#2A303A','panel_alt_bg':'#1A1E25','text':'#EDF1F7','muted_text':'#B5BFCC','border':'#3B4452','accent':'#7AA2F7','accent_alt':'#F6BD60','port_input':'#86D39E','port_output':'#7AA2F7','node_selected':'#F6BD60','titlebar_close_hover':'#D96868'}),
        ('steel', 'Steel', 'Professional', False, {'app_bg':'#EFF3F7','panel_bg':'#F9FBFD','panel_alt_bg':'#E2E8F0','text':'#243041','muted_text':'#65758A','border':'#C3CFDB','accent':'#4A6FA5','accent_alt':'#3FB0AC','port_input':'#4CAF50','port_output':'#4A6FA5','node_selected':'#3FB0AC','titlebar_close_hover':'#DE6A6A'}),
        ('graphite', 'Graphite', 'Professional', True, {'app_bg':'#17191D','panel_bg':'#20242A','panel_alt_bg':'#101216','text':'#E7EAEE','muted_text':'#A6AFBA','border':'#303640','accent':'#5E9CFF','accent_alt':'#8DD3C7','port_input':'#7AD39C','port_output':'#5E9CFF','node_selected':'#8DD3C7','titlebar_close_hover':'#D15B5B'}),
        ('ivory', 'Ivory', 'Professional', False, {'app_bg':'#FAF8F2','panel_bg':'#FFFDF9','panel_alt_bg':'#F0ECE3','text':'#312D28','muted_text':'#756D62','border':'#D9D1C5','accent':'#9A6B3A','accent_alt':'#4F9D8E','port_input':'#6FA57E','port_output':'#9A6B3A','node_selected':'#4F9D8E','titlebar_close_hover':'#D86F6F'}),

        ('dracula_pulse', 'Dracula Pulse', 'Developer Favorites', True, {'app_bg':'#282A36','panel_bg':'#343746','panel_alt_bg':'#21222C','text':'#F8F8F2','muted_text':'#C8CBE0','border':'#6272A4','accent':'#BD93F9','accent_alt':'#FF79C6','port_input':'#50FA7B','port_output':'#8BE9FD','node_selected':'#FF79C6','titlebar_close_hover':'#FF5555'}),
        ('one_dark_pro', 'One Dark Pro', 'Developer Favorites', True, {'app_bg':'#282C34','panel_bg':'#2F3541','panel_alt_bg':'#21252B','text':'#ABB2BF','muted_text':'#8D95A3','border':'#4B5263','accent':'#61AFEF','accent_alt':'#C678DD','port_input':'#98C379','port_output':'#61AFEF','node_selected':'#C678DD','titlebar_close_hover':'#E06C75'}),
        ('nord', 'Nord', 'Developer Favorites', True, {'app_bg':'#2E3440','panel_bg':'#3B4252','panel_alt_bg':'#242933','text':'#ECEFF4','muted_text':'#D8DEE9','border':'#4C566A','accent':'#88C0D0','accent_alt':'#81A1C1','port_input':'#A3BE8C','port_output':'#88C0D0','node_selected':'#81A1C1','titlebar_close_hover':'#BF616A'}),
        ('github_dark', 'GitHub Dark', 'Developer Favorites', True, {'app_bg':'#0D1117','panel_bg':'#161B22','panel_alt_bg':'#0B0F14','text':'#C9D1D9','muted_text':'#8B949E','border':'#30363D','accent':'#2F81F7','accent_alt':'#58A6FF','port_input':'#3FB950','port_output':'#2F81F7','node_selected':'#58A6FF','titlebar_close_hover':'#DA3633'}),
        ('github_light', 'GitHub Light', 'Developer Favorites', False, {'app_bg':'#FFFFFF','panel_bg':'#F6F8FA','panel_alt_bg':'#FFFFFF','text':'#24292F','muted_text':'#57606A','border':'#D0D7DE','accent':'#0969DA','accent_alt':'#1A7F37','port_input':'#1A7F37','port_output':'#0969DA','node_selected':'#1A7F37','titlebar_close_hover':'#FA4549'}),
        ('solarized_dark', 'Solarized Dark', 'Developer Favorites', True, {'app_bg':'#002B36','panel_bg':'#073642','panel_alt_bg':'#00212B','text':'#93A1A1','muted_text':'#839496','border':'#586E75','accent':'#268BD2','accent_alt':'#2AA198','port_input':'#859900','port_output':'#268BD2','node_selected':'#2AA198','titlebar_close_hover':'#DC322F'}),
        ('solarized_light', 'Solarized Light', 'Developer Favorites', False, {'app_bg':'#FDF6E3','panel_bg':'#EEE8D5','panel_alt_bg':'#F5EFD9','text':'#586E75','muted_text':'#657B83','border':'#93A1A1','accent':'#268BD2','accent_alt':'#2AA198','port_input':'#859900','port_output':'#268BD2','node_selected':'#2AA198','titlebar_close_hover':'#DC322F'}),
        ('tokyo_night', 'Tokyo Night', 'Developer Favorites', True, {'app_bg':'#1A1B26','panel_bg':'#1F2335','panel_alt_bg':'#16161E','text':'#C0CAF5','muted_text':'#7F89B0','border':'#2C3250','accent':'#7AA2F7','accent_alt':'#BB9AF7','port_input':'#9ECE6A','port_output':'#7DCFFF','node_selected':'#BB9AF7','titlebar_close_hover':'#F7768E'}),
        ('gruvbox_dark', 'Gruvbox Dark', 'Developer Favorites', True, {'app_bg':'#282828','panel_bg':'#32302F','panel_alt_bg':'#1D2021','text':'#EBDBB2','muted_text':'#BDAE93','border':'#504945','accent':'#D79921','accent_alt':'#B16286','port_input':'#98971A','port_output':'#458588','node_selected':'#B16286','titlebar_close_hover':'#CC241D'}),
        ('night_owl', 'Night Owl', 'Developer Favorites', True, {'app_bg':'#011627','panel_bg':'#10243A','panel_alt_bg':'#01111D','text':'#D6DEEB','muted_text':'#7F97A8','border':'#23425C','accent':'#82AAFF','accent_alt':'#C792EA','port_input':'#A3BE8C','port_output':'#82AAFF','node_selected':'#C792EA','titlebar_close_hover':'#EF5350'}),
        ('ayu_dark', 'Ayu Dark', 'Developer Favorites', True, {'app_bg':'#0F1419','panel_bg':'#14191F','panel_alt_bg':'#0B1015','text':'#E6E1CF','muted_text':'#9AA5B1','border':'#27313A','accent':'#FFB454','accent_alt':'#59C2FF','port_input':'#7FD962','port_output':'#59C2FF','node_selected':'#FF8F40','titlebar_close_hover':'#F07178'}),
        ('monokai_pro', 'Monokai Pro', 'Developer Favorites', True, {'app_bg':'#2D2A2E','panel_bg':'#363337','panel_alt_bg':'#221F22','text':'#FCFCFA','muted_text':'#C1C0C0','border':'#5B595C','accent':'#AB9DF2','accent_alt':'#FF6188','port_input':'#A9DC76','port_output':'#78DCE8','node_selected':'#FF6188','titlebar_close_hover':'#FF4D6D'}),
        ('material_dark', 'Material Dark', 'Developer Favorites', True, {'app_bg':'#263238','panel_bg':'#31424A','panel_alt_bg':'#1E272C','text':'#EEFFFF','muted_text':'#B0BEC5','border':'#41545F','accent':'#82AAFF','accent_alt':'#C792EA','port_input':'#C3E88D','port_output':'#89DDFF','node_selected':'#FFCB6B','titlebar_close_hover':'#F07178'}),

        ('oled_dark', 'OLED Dark', 'Minimal', True, {'app_bg':'#000000','panel_bg':'#0D0D0D','panel_alt_bg':'#050505','text':'#F3F4F6','muted_text':'#9CA3AF','border':'#262626','accent':'#3B82F6','accent_alt':'#A855F7','port_input':'#22C55E','port_output':'#0EA5E9','node_selected':'#A855F7','titlebar_close_hover':'#DC2626'}),
        ('zen_gray', 'Zen Gray', 'Minimal', False, {'app_bg':'#F3F4F6','panel_bg':'#FCFCFD','panel_alt_bg':'#F1F3F5','text':'#2F3440','muted_text':'#6B7280','border':'#D1D5DB','accent':'#64748B','accent_alt':'#94A3B8','port_input':'#84CC16','port_output':'#64748B','node_selected':'#94A3B8','titlebar_close_hover':'#F87171'}),
        ('paper', 'Paper', 'Minimal', False, {'app_bg':'#FFFDF8','panel_bg':'#FFFEFB','panel_alt_bg':'#F7F3EA','text':'#35312D','muted_text':'#7A726A','border':'#D8D0C4','accent':'#8C6A43','accent_alt':'#A78B5F','port_input':'#7DA27D','port_output':'#8C6A43','node_selected':'#A78B5F','titlebar_close_hover':'#D97757'}),
        ('zen_dark', 'Zen Dark', 'Minimal', True, {'app_bg':'#202124','panel_bg':'#2A2B2E','panel_alt_bg':'#1A1B1E','text':'#E8EAED','muted_text':'#9AA0A6','border':'#3C4043','accent':'#8AB4F8','accent_alt':'#A1C2FA','port_input':'#81C995','port_output':'#8AB4F8','node_selected':'#C58AF9','titlebar_close_hover':'#EA4335'}),
        ('linen', 'Linen', 'Minimal', False, {'app_bg':'#F7F2E8','panel_bg':'#FCF9F1','panel_alt_bg':'#EFE7D7','text':'#3A342D','muted_text':'#7A7266','border':'#D5CCBC','accent':'#A17C5B','accent_alt':'#6B9F8D','port_input':'#6B9F8D','port_output':'#A17C5B','node_selected':'#6B9F8D','titlebar_close_hover':'#D96B6B'}),
        ('fog', 'Fog', 'Minimal', False, {'app_bg':'#EEF1F4','panel_bg':'#FAFBFC','panel_alt_bg':'#E5E9EE','text':'#30363D','muted_text':'#6E7781','border':'#CBD5DF','accent':'#5B7C99','accent_alt':'#7FA8C9','port_input':'#5FAE8B','port_output':'#5B7C99','node_selected':'#7FA8C9','titlebar_close_hover':'#E06A6A'}),

        ('neon_noir', 'Neon Noir', 'Creative', True, {'app_bg':'#16181D','panel_bg':'#1F2430','panel_alt_bg':'#11151C','text':'#F5F7FA','muted_text':'#C7D0D9','border':'#3A4252','accent':'#00C2FF','accent_alt':'#FF4D9D','port_input':'#7EE787','port_output':'#00C2FF','node_selected':'#FF4D9D','titlebar_close_hover':'#D63B5D'}),
        ('sunset_synth', 'Sunset Synth', 'Creative', True, {'app_bg':'#1D1724','panel_bg':'#2A2233','panel_alt_bg':'#191320','text':'#F8F3FF','muted_text':'#D8CCE8','border':'#4B3F59','accent':'#9B5DE5','accent_alt':'#F15BB5','port_input':'#7BD389','port_output':'#F6BD60','node_selected':'#F15BB5','titlebar_close_hover':'#C44569'}),
        ('miami_vice', 'Miami Vice', 'Creative', True, {'app_bg':'#1B1028','panel_bg':'#24153A','panel_alt_bg':'#180F28','text':'#F8F5FF','muted_text':'#D8CCE8','border':'#503A73','accent':'#00E5FF','accent_alt':'#FF4FA3','port_input':'#7CFFCB','port_output':'#00E5FF','node_selected':'#FF4FA3','titlebar_close_hover':'#FF5C7A'}),
        ('synthwave', 'Synthwave', 'Creative', True, {'app_bg':'#1A0F2B','panel_bg':'#22133A','panel_alt_bg':'#120A1E','text':'#F8F8F2','muted_text':'#B6A8D6','border':'#3E2B5B','accent':'#FF6AC1','accent_alt':'#7DF9FF','port_input':'#8AFF80','port_output':'#7DF9FF','node_selected':'#FF6AC1','titlebar_close_hover':'#FF4D8D'}),
        ('emerald_glow', 'Emerald Glow', 'Creative', True, {'app_bg':'#0F1F1C','panel_bg':'#162926','panel_alt_bg':'#0A1614','text':'#D4F5EF','muted_text':'#7EA39B','border':'#29524D','accent':'#2ECC71','accent_alt':'#7FFFD4','port_input':'#7FFFD4','port_output':'#2ECC71','node_selected':'#7FFFD4','titlebar_close_hover':'#E45A6A'}),
        ('aurora', 'Aurora', 'Creative', True, {'app_bg':'#151B2E','panel_bg':'#1E2742','panel_alt_bg':'#101625','text':'#EAF2FF','muted_text':'#AEBEDB','border':'#324567','accent':'#6EE7F9','accent_alt':'#B490FF','port_input':'#8EF0A7','port_output':'#6EE7F9','node_selected':'#B490FF','titlebar_close_hover':'#F472B6'}),

        ('high_contrast_dark', 'High Contrast Dark', 'Accessibility', True, {'app_bg':'#000000','panel_bg':'#111111','panel_alt_bg':'#000000','text':'#FFFFFF','muted_text':'#F0F0F0','border':'#FFFFFF','border_strong':'#FFFFFF','accent':'#FFD400','accent_alt':'#00E5FF','selection_bg':'#FFD400','selection_text':'#000000','port_input':'#7CFF00','port_output':'#00E5FF','node_selected':'#00E5FF','titlebar_close_hover':'#FF3B30','table_selection_border':'#00E5FF','current_cell_border':'#00E5FF'}),
        ('high_contrast_light', 'High Contrast Light', 'Accessibility', False, {'app_bg':'#FFFFFF','panel_bg':'#FFFFFF','panel_alt_bg':'#F3F3F3','text':'#000000','muted_text':'#111111','border':'#000000','border_strong':'#000000','accent':'#005FCC','accent_alt':'#B00020','selection_bg':'#005FCC','selection_text':'#FFFFFF','port_input':'#0A7D00','port_output':'#005FCC','node_selected':'#B00020','titlebar_close_hover':'#FF6B6B','table_selection_border':'#B00020','current_cell_border':'#B00020'}),
        ('blue_orange_safe', 'Blue Orange Safe', 'Accessibility', False, {'app_bg':'#F6F8FB','panel_bg':'#FFFFFF','panel_alt_bg':'#E9EEF4','text':'#1F2937','muted_text':'#5B6472','border':'#B8C4D3','accent':'#1D70B8','accent_alt':'#E67E22','port_input':'#2E8B57','port_output':'#1D70B8','node_selected':'#E67E22','selection_bg':'#1D70B8','selection_text':'#FFFFFF','titlebar_close_hover':'#D45D5D'}),
        ('dark_yellow', 'Dark Yellow', 'Accessibility', True, {'app_bg':'#101010','panel_bg':'#181818','panel_alt_bg':'#080808','text':'#FFF9DB','muted_text':'#E8D98B','border':'#F4D03F','accent':'#F4D03F','accent_alt':'#5BC0DE','selection_bg':'#F4D03F','selection_text':'#000000','port_input':'#7DFF7D','port_output':'#5BC0DE','node_selected':'#5BC0DE','titlebar_close_hover':'#FF6B6B'}),

        ('notion_dark', 'Notion Dark', 'Ecosystem', True, {'app_bg':'#191919','panel_bg':'#202020','panel_alt_bg':'#171717','text':'#EDEDED','muted_text':'#B4B4B4','border':'#303030','accent':'#2F80ED','accent_alt':'#8A5CF6','port_input':'#27AE60','port_output':'#2F80ED','node_selected':'#8A5CF6','titlebar_close_hover':'#C0392B'}),
        ('notion_light', 'Notion Light', 'Ecosystem', False, {'app_bg':'#F7F6F3','panel_bg':'#FFFFFF','panel_alt_bg':'#F1EFEB','text':'#37352F','muted_text':'#78746E','border':'#DDD9D2','accent':'#2F80ED','accent_alt':'#6C63FF','port_input':'#27AE60','port_output':'#2F80ED','node_selected':'#6C63FF','titlebar_close_hover':'#E06A6A'}),
        ('slack_dark', 'Slack Dark', 'Ecosystem', True, {'app_bg':'#1A1D21','panel_bg':'#222529','panel_alt_bg':'#14171A','text':'#F8F8F8','muted_text':'#B5BCC4','border':'#34393F','accent':'#36C5F0','accent_alt':'#E01E5A','port_input':'#2EB67D','port_output':'#36C5F0','node_selected':'#E01E5A','titlebar_close_hover':'#E25D75'}),
        ('figma_dark', 'Figma Dark', 'Ecosystem', True, {'app_bg':'#1E1E1E','panel_bg':'#2C2C2C','panel_alt_bg':'#171717','text':'#FFFFFF','muted_text':'#B3B3B3','border':'#444444','accent':'#0ACF83','accent_alt':'#A259FF','port_input':'#0ACF83','port_output':'#1ABCFE','node_selected':'#A259FF','titlebar_close_hover':'#F24E1E'}),
        ('vscode_dark', 'VS Code Dark', 'Ecosystem', True, {'app_bg':'#1E1E1E','panel_bg':'#252526','panel_alt_bg':'#1B1B1C','text':'#D4D4D4','muted_text':'#9D9D9D','border':'#3C3C3C','accent':'#007ACC','accent_alt':'#C586C0','port_input':'#89D185','port_output':'#4FC1FF','node_selected':'#C586C0','titlebar_close_hover':'#E35E5E'}),

        ('forest', 'Forest', 'Nature', True, {'app_bg':'#1B2B24','panel_bg':'#22352C','panel_alt_bg':'#142019','text':'#D6E8D9','muted_text':'#86A892','border':'#355040','accent':'#6FCF97','accent_alt':'#B8E986','port_input':'#9BE28C','port_output':'#6FCF97','node_selected':'#B8E986','titlebar_close_hover':'#D96A6A'}),
        ('ocean_breeze', 'Ocean Breeze', 'Nature', True, {'app_bg':'#162028','panel_bg':'#1C2B36','panel_alt_bg':'#10171D','text':'#D4ECFF','muted_text':'#7FA1B7','border':'#2E4656','accent':'#4FC3F7','accent_alt':'#64D8CB','port_input':'#8FD694','port_output':'#4FC3F7','node_selected':'#64D8CB','titlebar_close_hover':'#E06A6A'}),
        ('desert_sand', 'Desert Sand', 'Nature', False, {'app_bg':'#F4ECD8','panel_bg':'#EDE3C4','panel_alt_bg':'#E6DAB5','text':'#5C4A2E','muted_text':'#A08A63','border':'#D4C39A','accent':'#C48A3A','accent_alt':'#7DA27D','port_input':'#7DA27D','port_output':'#C48A3A','node_selected':'#7DA27D','titlebar_close_hover':'#D67676'}),
        ('glacier', 'Glacier', 'Nature', False, {'app_bg':'#EFF6FB','panel_bg':'#F9FCFF','panel_alt_bg':'#E4EEF6','text':'#29465B','muted_text':'#6B8BA0','border':'#C4D7E5','accent':'#4AA3DF','accent_alt':'#78DCCA','port_input':'#63C38D','port_output':'#4AA3DF','node_selected':'#78DCCA','titlebar_close_hover':'#D96F6F'}),
        ('autumn', 'Autumn', 'Nature', True, {'app_bg':'#241A17','panel_bg':'#2D211D','panel_alt_bg':'#17100E','text':'#F3E7DD','muted_text':'#C0A89A','border':'#5A4339','accent':'#D97706','accent_alt':'#B45309','port_input':'#84A98C','port_output':'#D97706','node_selected':'#B45309','titlebar_close_hover':'#DC6A5E'}),


        ('rose_pulse', 'Rose Pulse', 'Creative', True, {'app_bg':'#24141F','panel_bg':'#301B29','panel_alt_bg':'#190E15','text':'#FFEAF4','muted_text':'#D7AFC4','border':'#6A4257','accent':'#FF5FA2','accent_alt':'#FFB3D1','port_input':'#9FF3C6','port_output':'#FF82B2','node_selected':'#FFB3D1','titlebar_close_hover':'#E45878'}),
        ('sunflower', 'Sunflower', 'Creative', False, {'app_bg':'#FFF8D9','panel_bg':'#FFFDF0','panel_alt_bg':'#F8EDB4','text':'#5B4600','muted_text':'#8D7727','border':'#D8C15A','accent':'#E4B400','accent_alt':'#F59E0B','port_input':'#7DBE74','port_output':'#D4A017','node_selected':'#F59E0B','selection_bg':'#E4B400','selection_text':'#2C2200','titlebar_close_hover':'#D96C5C'}),
        ('blood_moon', 'Blood Moon', 'Creative', True, {'app_bg':'#1B0A0D','panel_bg':'#281114','panel_alt_bg':'#120709','text':'#FBEAEC','muted_text':'#C79B9F','border':'#663239','accent':'#A1121D','accent_alt':'#D7263D','port_input':'#7BC47F','port_output':'#E85D75','node_selected':'#D7263D','selection_bg':'#6B0F18','selection_text':'#FFF1F2','titlebar_close_hover':'#FF6B6B'}),
        ('mint_frost', 'Mint Frost', 'Nature', False, {'app_bg':'#EAFBF5','panel_bg':'#F7FFFC','panel_alt_bg':'#D8F3E8','text':'#1F4F45','muted_text':'#5F8D84','border':'#A9D8C8','accent':'#38BFA7','accent_alt':'#8BE3CF','port_input':'#52C788','port_output':'#38BFA7','node_selected':'#8BE3CF','titlebar_close_hover':'#DE6E77'}),
        ('pistachio_cream', 'Pistachio Cream', 'Nature', False, {'app_bg':'#F5F8E8','panel_bg':'#FBFDF4','panel_alt_bg':'#E8EFCF','text':'#3B4A22','muted_text':'#6F7E52','border':'#C6D39A','accent':'#A4B465','accent_alt':'#6FB98F','port_input':'#76B67A','port_output':'#8FA54A','node_selected':'#6FB98F','titlebar_close_hover':'#D97878'}),
        ('cyan_drift', 'Cyan Drift', 'Nature', True, {'app_bg':'#0F1E24','panel_bg':'#152A33','panel_alt_bg':'#0A1418','text':'#E2FBFF','muted_text':'#8CB7C2','border':'#2E5965','accent':'#18C6E3','accent_alt':'#7EE8FA','port_input':'#7CE3B0','port_output':'#18C6E3','node_selected':'#7EE8FA','selection_bg':'#12495A','selection_text':'#F3FEFF','titlebar_close_hover':'#E56B6F'}),
        ('lavender_haze', 'Lavender Haze', 'Creative', True, {'app_bg':'#191528','panel_bg':'#221C36','panel_alt_bg':'#110E1C','text':'#F2EDFF','muted_text':'#BDB1DA','border':'#54487A','accent':'#A78BFA','accent_alt':'#F0ABFC','port_input':'#9BE7C4','port_output':'#A78BFA','node_selected':'#F0ABFC','titlebar_close_hover':'#F472B6'}),
        ('citrus_pop', 'Citrus Pop', 'Creative', False, {'app_bg':'#FFFBEA','panel_bg':'#FFFFFF','panel_alt_bg':'#FFF1B8','text':'#4E3F00','muted_text':'#8E7A2F','border':'#E5CF6B','accent':'#D4E157','accent_alt':'#FFB300','port_input':'#66BB6A','port_output':'#C0CA33','node_selected':'#FFB300','selection_bg':'#D4E157','selection_text':'#243000','titlebar_close_hover':'#E57373'}),
        ('matrix', 'Matrix', 'Retro', True, {'app_bg':'#000000','panel_bg':'#050505','panel_alt_bg':'#000000','text':'#00FF41','muted_text':'#00A32A','border':'#0F5C1A','accent':'#00FF41','accent_alt':'#7CFF00','selection_bg':'#003D10','selection_text':'#00FF41','port_input':'#7CFF00','port_output':'#00FF41','node_selected':'#7CFF00','titlebar_close_hover':'#FF3B30'}),
        ('amber_crt', 'Amber CRT', 'Retro', True, {'app_bg':'#1A1200','panel_bg':'#201700','panel_alt_bg':'#120C00','text':'#FFB347','muted_text':'#C6892D','border':'#6A480A','accent':'#FFB347','accent_alt':'#FFD166','selection_bg':'#5C3B00','selection_text':'#FFF4D6','port_input':'#FFD166','port_output':'#FFB347','node_selected':'#FFD166','titlebar_close_hover':'#FF6B35'}),
        ('dos_blue', 'DOS Blue', 'Retro', True, {'app_bg':'#0000AA','panel_bg':'#0000AA','panel_alt_bg':'#000088','text':'#FFFFFF','muted_text':'#C7D2FE','border':'#7EA6FF','accent':'#55FFFF','accent_alt':'#FFFF55','selection_bg':'#0033CC','selection_text':'#FFFFFF','port_input':'#55FF55','port_output':'#55FFFF','node_selected':'#FFFF55','titlebar_close_hover':'#FF5555'}),
        ('retro_purple', 'Retro Purple', 'Retro', True, {'app_bg':'#1B1431','panel_bg':'#241B42','panel_alt_bg':'#120E21','text':'#F3ECFF','muted_text':'#BBAEDB','border':'#5A4C88','accent':'#B388FF','accent_alt':'#FF80AB','port_input':'#80CBC4','port_output':'#B388FF','node_selected':'#FF80AB','titlebar_close_hover':'#FF5C8A'}),
    ]
    return [_balanced_theme(*spec) for spec in specs]

class ThemeRegistry(object):
    def __init__(self):
        self._themes_by_name = OrderedDict()
        self._themes_by_id = OrderedDict()

    def register(self, theme):
        self._themes_by_name[theme.display_name] = theme
        self._themes_by_id[theme.id] = theme

    def all_themes(self):
        return list(self._themes_by_name.values())

    def by_name(self, display_name):
        return self._themes_by_name[display_name]

    def categories(self):
        grouped = OrderedDict()
        for theme in self._themes_by_name.values():
            grouped.setdefault(theme.category, []).append(theme.display_name)
        return grouped


class ThemeManager(QtCore.QObject):
    themeChanged = QtCore.pyqtSignal(str)

    def __init__(self, registry=None):
        super().__init__()
        self.registry = registry or ThemeRegistry()
        self._current_theme_name = None

    def register_theme(self, theme):
        self.registry.register(theme)

    def theme_names_by_category(self):
        return self.registry.categories()

    def set_current_theme(self, theme_name):
        if theme_name not in self.registry._themes_by_name:
            raise KeyError("Unknown theme: {0}".format(theme_name))
        if theme_name == self._current_theme_name:
            return
        self._current_theme_name = theme_name
        self.themeChanged.emit(theme_name)

    def current_theme_name(self):
        return self._current_theme_name

    def current_theme(self):
        return self.theme_definition(self._current_theme_name)

    def theme_definition(self, theme_name):
        return self.registry.by_name(theme_name)

    def color_tokens(self, theme_name):
        return self.theme_definition(theme_name).tokens.colors


_REGISTRY = ThemeRegistry()
for _theme in _build_builtin_themes():
    _REGISTRY.register(_theme)

_THEME_MANAGER = ThemeManager(_REGISTRY)
_THEME_MANAGER.set_current_theme("Midnight")


THEMES = OrderedDict((theme.display_name, theme.tokens.colors) for theme in _REGISTRY.all_themes())
THEME_CATEGORIES = _REGISTRY.categories()


def get_theme_manager():
    return _THEME_MANAGER


def get_theme_definition(theme_name):
    return _REGISTRY.by_name(theme_name)


def get_theme_colors(theme_name):
    return THEMES[theme_name]


def build_stylesheet(theme_or_name):
    theme = theme_or_name if isinstance(theme_or_name, dict) else get_theme_colors(theme_or_name)
    theme = dict(theme)
    theme.setdefault('subtle_text', theme.get('muted_text', theme.get('text_secondary', theme.get('text', '#AAB2C0'))))
    theme.setdefault('panel_border', theme.get('border', '#3A4160'))
    theme.setdefault('toolbar_bg', theme.get('panel_bg', theme.get('surface', '#22283B')))
    theme.setdefault('menu_bg', theme.get('panel_bg', theme.get('surface', '#22283B')))
    theme.setdefault('menu_hover', theme.get('hover_bg', theme.get('accent', '#7E57C2')))
    theme.setdefault('menu_separator', theme.get('border', '#3A4160'))
    theme.setdefault('tab_active_bg', theme.get('accent', '#7E57C2'))
    theme.setdefault('tab_inactive_bg', theme.get('tab_bg', theme.get('panel_bg', theme.get('surface', '#22283B'))))
    theme.setdefault('tab_hover_bg', theme.get('hover_bg', theme.get('accent', '#7E57C2')))
    theme.setdefault('status_bg', theme.get('panel_bg', theme.get('surface', '#22283B')))
    theme.setdefault('status_text', theme.get('text', '#FFFFFF'))
    theme.setdefault('input_bg', theme.get('surface_alt', theme.get('surface', '#1E2433')))
    theme.setdefault('input_border', theme.get('border', '#3A4160'))
    theme.setdefault('selection_bg', theme.get('accent', '#7E57C2'))
    theme.setdefault('selection_text', theme.get('accent_text', theme.get('text_on_accent', '#FFFFFF')))

    # Semantic Nexus UI control tokens. These centralize framework widget styling so
    # plugins and design previews inherit a consistent look without local styling.
    panel_bg = theme.get('panel_bg', theme.get('app_bg', '#20242B'))
    panel_alt_bg = theme.get('panel_alt_bg', theme.get('input_bg', panel_bg))
    input_bg = theme.get('input_bg', panel_alt_bg)
    border = theme.get('border', theme.get('input_border', '#3A4160'))
    border_strong = theme.get('border_strong', border)
    accent = theme.get('accent', '#3B82F6')
    theme.setdefault('control_bg', input_bg)
    theme.setdefault('control_alt_bg', panel_alt_bg)
    theme.setdefault('control_hover_bg', theme.get('hover_bg', panel_alt_bg))
    theme.setdefault('control_pressed_bg', theme.get('pressed_bg', panel_alt_bg))
    theme.setdefault('control_border', border)
    theme.setdefault('control_border_hover', border_strong)
    theme.setdefault('control_focus_border', theme.get('focus_ring', accent))
    theme.setdefault('control_text', theme.get('text', '#FFFFFF'))
    theme.setdefault('control_disabled_bg', panel_alt_bg)
    theme.setdefault('control_disabled_text', theme.get('disabled_text', theme.get('muted_text', '#AAB2C0')))
    theme.setdefault('button_bg', panel_alt_bg)
    theme.setdefault('button_hover_bg', theme.get('hover_bg', panel_alt_bg))
    theme.setdefault('button_pressed_bg', theme.get('pressed_bg', panel_alt_bg))
    theme.setdefault('button_border', border_strong)
    theme.setdefault('button_hover_border', accent)
    theme.setdefault('button_pressed_border', theme.get('accent_pressed', accent))
    theme.setdefault('button_text', theme.get('text', '#FFFFFF'))
    theme.setdefault('button_disabled_bg', theme.get('control_disabled_bg'))
    theme.setdefault('button_disabled_text', theme.get('control_disabled_text'))
    theme.setdefault('primary_button_bg', accent)
    theme.setdefault('primary_button_hover_bg', theme.get('accent_hover', accent))
    theme.setdefault('primary_button_pressed_bg', theme.get('accent_pressed', accent))
    theme.setdefault('primary_button_border', accent)
    theme.setdefault('primary_button_text', theme.get('accent_text', '#FFFFFF'))
    theme.setdefault('row_alt_bg', panel_alt_bg)
    theme.setdefault('row_hover_bg', theme.get('hover_bg', panel_alt_bg))
    theme.setdefault('frame_bg', theme.get('panel_bg', panel_bg))
    theme.setdefault('frame_border', theme.get('panel_border', border))
    theme.setdefault('frame_border_hover', theme.get('border_strong', border_strong))
    theme.setdefault('frame_radius', 8)
    theme.setdefault('corner_radius_rounded', theme.get('frame_radius', 8))
    theme.setdefault('corner_radius_square', 0)
    theme.setdefault('widget_padding_sm', 4)
    theme.setdefault('widget_padding_md', 8)
    theme.setdefault('table_radius', theme.get('frame_radius', 8))
    return """
    QMainWindow, QWidget {{
        background-color: {app_bg};
        color: {text};
    }}

    #titleBar {{
        background-color: {titlebar_bg};
        border-bottom: 1px solid {border};
    }}

    #titleLabel {{
        color: {text};
        font-weight: 600;
        padding: 0 12px;
    }}

    #titleMenuHost {{
        background: transparent;
    }}

    #btnNexusMenu, #btnCommandsMenu, #btnViewMenu, #btnToolsMenu, #btnThemesMenu {{
        background-color: transparent;
        color: {text};
        border: none;
        min-height: 28px;
        padding: 0 10px;
        border-radius: 6px;
    }}

    #btnNexusMenu:hover, #btnCommandsMenu:hover, #btnViewMenu:hover, #btnToolsMenu:hover, #btnThemesMenu:hover {{
        background-color: {titlebar_button_hover};
    }}

    #btnNexusMenu::menu-indicator, #btnCommandsMenu::menu-indicator, #btnViewMenu::menu-indicator, #btnToolsMenu::menu-indicator, #btnThemesMenu::menu-indicator {{
        image: none;
        width: 0px;
    }}

    #btnMinimize, #btnMaximize, #btnClose {{
        background-color: transparent;
        color: {text};
        border: none;
        min-width: 36px;
        max-width: 36px;
        min-height: 28px;
        max-height: 28px;
        font-size: 14px;
    }}

    #btnMinimize:hover, #btnMaximize:hover {{
        background-color: {titlebar_button_hover};
    }}


    #btnClose:hover {{
        background-color: {titlebar_close_hover};
    }}

    #nexusDialogSurface {{
        background-color: {app_bg};
        border: 1px solid {border};
    }}

    #nexusDialogContent {{
        background-color: {app_bg};
    }}

    #nexusWindowSurface {{
        background-color: {app_bg};
        border: 1px solid {border};
    }}

    #NexusToolHeader {{
        background-color: {panel_bg};
        border-bottom: 1px solid {border};
    }}

    #NexusToolHeaderTitle {{
        color: {text};
        font-weight: 700;
    }}

    #NexusToolHeaderSubtitle {{
        color: {muted_text};
    }}

    #NexusToolbarRow {{
        background-color: {panel_bg};
        border-bottom: 1px solid {border};
    }}

    QFrame[nexusControl="frame"],
    QFrame[nexusThemeRole="surface"] {{
        background-color: transparent;
        border: none;
    }}

    QFrame[nexusFrameStyle="bordered"] {{
        background-color: {frame_bg};
        border: 1px solid {frame_border};
        border-radius: {frame_radius}px;
    }}

    QFrame[nexusFrameStyle="borderless"] {{
        background-color: transparent;
        border: none;
    }}

    QFrame[nexusCorner="square"],
    QTableWidget[nexusCorner="square"],
    QTableView[nexusCorner="square"],
    QLineEdit[nexusCorner="square"],
    QTextEdit[nexusCorner="square"],
    QPushButton[nexusCorner="square"] {{
        border-radius: {corner_radius_square}px;
    }}

    QFrame[nexusCorner="rounded"],
    QTableWidget[nexusCorner="rounded"],
    QTableView[nexusCorner="rounded"],
    QLineEdit[nexusCorner="rounded"],
    QTextEdit[nexusCorner="rounded"],
    QPushButton[nexusCorner="rounded"] {{
        border-radius: {corner_radius_rounded}px;
    }}

    QFrame[nexusBorder="none"],
    QTableWidget[nexusBorder="none"],
    QTableView[nexusBorder="none"] {{
        border: none;
    }}

    QFrame[nexusBorder="strong"],
    QTableWidget[nexusBorder="strong"],
    QTableView[nexusBorder="strong"] {{
        border: 1px solid {border_strong};
    }}

    #NexusPanel, #NexusSurface {{
        background-color: {frame_bg};
        border: 1px solid {frame_border};
        border-radius: {frame_radius}px;
    }}

    QMenuBar {{
        background-color: {menu_bg};
        color: {text};
        border-bottom: 1px solid {border};
    }}

    QMenuBar::item {{
        padding: 6px 10px;
        background: transparent;
    }}

    QMenuBar::item:selected {{
        background-color: {accent};
        color: {accent_text};
    }}

    QMenu {{
        background-color: {menu_bg};
        color: {text};
        border: 1px solid {border};
    }}

    QMenu::item:selected {{
        background-color: {accent};
        color: {accent_text};
    }}

    QDockWidget {{
        color: {text};
    }}

    QDockWidget::title {{
        background-color: {panel_bg};
        text-align: left;
        padding-left: 8px;
        padding-top: 4px;
        padding-bottom: 4px;
        border-bottom: 1px solid {border};
    }}

    QTabBar::tab {{
        background-color: {tab_bg};
        color: {text};
        border: 1px solid {border};
        padding: 6px 12px;
        margin-right: 1px;
    }}

    QTabBar::tab:selected {{
        background-color: {tab_active_bg};
        color: {accent_text};
    }}

    QTabBar::tab:hover:!selected {{
        background-color: {hover_bg};
    }}

    QTabBar::close-button {{
        subcontrol-position: right;
        margin-left: 8px;
        width: 14px;
        height: 14px;
        background-color: {tab_inactive_close_bg};
        border-radius: 7px;
    }}

    QTabBar::close-button:hover {{
        background-color: {titlebar_close_hover};
    }}

    QTabWidget::pane {{
        border: 1px solid {border};
        top: -1px;
    }}

    QWidget#dockTitleBar {{
        background-color: {panel_bg};
        border-bottom: 1px solid {border};
    }}

    QLabel#dockTitleLabel {{
        color: {text};
        font-weight: bold;
        padding-left: 6px;
    }}

    QPushButton#dockFloatButton, QPushButton#dockCloseButton {{
        background-color: transparent;
        color: {text};
        border: none;
        min-width: 28px;
        max-width: 28px;
        min-height: 24px;
        max-height: 24px;
        padding: 0px;
    }}

    QPushButton#dockFloatButton:hover {{
        background-color: {titlebar_button_hover};
    }}

    QPushButton#dockCloseButton:hover {{
        background-color: {titlebar_close_hover};
    }}

    QLabel {{
        color: {text};
        background-color: transparent;
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {control_bg};
        color: {control_text};
        border: 1px solid {control_border};
        border-radius: 6px;
        padding: 4px 6px;
        selection-background-color: {selection_bg};
        selection-color: {selection_text};
    }}

    QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {{
        border-color: {control_border_hover};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border-color: {control_focus_border};
    }}

    QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
        background-color: {control_disabled_bg};
        color: {control_disabled_text};
        border-color: {control_border};
    }}

    QTextEdit, QPlainTextEdit {{
        background-color: {editor_bg};
        color: {editor_text};
    }}

    QPushButton {{
        background-color: {button_bg};
        color: {button_text};
        border: 1px solid {button_border};
        border-radius: 6px;
        padding: 6px 12px;
        min-height: 18px;
    }}

    QPushButton:hover {{
        background-color: {button_hover_bg};
        border-color: {button_hover_border};
    }}

    QPushButton:pressed {{
        background-color: {button_pressed_bg};
        border-color: {button_pressed_border};
    }}

    QPushButton:focus {{
        border-color: {control_focus_border};
    }}

    QPushButton:disabled {{
        background-color: {button_disabled_bg};
        color: {button_disabled_text};
        border-color: {control_border};
    }}

    QPushButton[nexusVariant="primary"] {{
        background-color: {primary_button_bg};
        color: {primary_button_text};
        border-color: {primary_button_border};
        font-weight: 600;
    }}

    QPushButton[nexusVariant="primary"]:hover {{
        background-color: {primary_button_hover_bg};
        border-color: {primary_button_hover_bg};
    }}

    QPushButton[nexusVariant="primary"]:pressed {{
        background-color: {primary_button_pressed_bg};
        border-color: {primary_button_pressed_bg};
    }}

    QToolButton {{
        background-color: transparent;
        color: {text};
        border: 1px solid transparent;
        border-radius: 6px;
        padding: 4px 6px;
    }}

    QToolButton:hover {{
        background-color: {button_hover_bg};
        border-color: {button_border};
    }}

    QToolButton:pressed {{
        background-color: {button_pressed_bg};
        border-color: {button_pressed_border};
    }}

    QCheckBox, QRadioButton {{
        color: {control_text};
        background-color: transparent;
        spacing: 6px;
    }}

    QCheckBox::indicator, QRadioButton::indicator {{
        width: 14px;
        height: 14px;
        background-color: {control_bg};
        border: 1px solid {button_border};
    }}

    QCheckBox::indicator {{
        border-radius: 3px;
    }}

    QRadioButton::indicator {{
        border-radius: 7px;
    }}

    QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
        border-color: {button_hover_border};
        background-color: {button_hover_bg};
    }}

    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {primary_button_bg};
        border-color: {primary_button_bg};
    }}

    QCheckBox:disabled, QRadioButton:disabled {{
        color: {control_disabled_text};
    }}

    QSlider::groove:horizontal {{
        height: 6px;
        background: {control_alt_bg};
        border: 1px solid {control_border};
        border-radius: 3px;
    }}

    QSlider::handle:horizontal {{
        width: 14px;
        margin: -5px 0;
        border-radius: 7px;
        background: {primary_button_bg};
        border: 1px solid {primary_button_border};
    }}

    QProgressBar {{
        background-color: {control_bg};
        color: {control_text};
        border: 1px solid {control_border};
        border-radius: 6px;
        text-align: center;
        min-height: 18px;
    }}

    QProgressBar::chunk {{
        background-color: {primary_button_bg};
        border-radius: 5px;
    }}

    QToolBar {{
        background-color: {toolbar_bg};
        border-bottom: 1px solid {border};
        spacing: 2px;
    }}

    QToolBar::separator {{
        width: 1px;
        background-color: {separator};
        margin: 4px 6px;
    }}

    QScrollBar:vertical {{
        background-color: {scrollbar_bg};
        width: 14px;
        margin: 0px;
        border-left: 1px solid {scrollbar_border};
    }}

    QScrollBar::handle:vertical {{
        background-color: {scrollbar_handle};
        min-height: 28px;
        border-radius: 6px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {scrollbar_handle_hover};
    }}

    QScrollBar::handle:vertical:pressed {{
        background-color: {scrollbar_handle_pressed};
    }}

    QScrollBar:horizontal {{
        background-color: {scrollbar_bg};
        height: 14px;
        margin: 0px;
        border-top: 1px solid {scrollbar_border};
    }}

    QScrollBar::handle:horizontal {{
        background-color: {scrollbar_handle};
        min-width: 28px;
        border-radius: 6px;
        margin: 2px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {scrollbar_handle_hover};
    }}

    QScrollBar::handle:horizontal:pressed {{
        background-color: {scrollbar_handle_pressed};
    }}

    QScrollBar::add-line, QScrollBar::sub-line {{
        background: transparent;
        border: none;
        width: 0px;
        height: 0px;
    }}

    QScrollBar::add-page, QScrollBar::sub-page {{
        background: transparent;
    }}

    QAbstractScrollArea::corner {{
        background-color: {scrollbar_bg};
        border-top: 1px solid {scrollbar_border};
        border-left: 1px solid {scrollbar_border};
    }}

    QStatusBar {{
        background-color: {panel_bg};
        color: {muted_text};
    }}

    QGraphicsView {{
        background-color: {grid_bg};
        border: none;
    }}

    QTableWidget, QTableView {{
        background-color: {control_bg};
        alternate-background-color: {row_alt_bg};
        color: {text};
        gridline-color: {table_grid};
        border: 1px solid {border};
        border-radius: {table_radius}px;
        selection-background-color: {table_selection_bg};
        selection-color: {selection_text};
    }}

    QTableWidget::item, QTableView::item {{
        background-color: {input_bg};
        color: {text};
    }}

    QListWidget, QListView, QTreeWidget, QTreeView {{
        background-color: {control_bg};
        alternate-background-color: {row_alt_bg};
        color: {text};
        border: 1px solid {border};
        outline: 0;
    }}

    QListWidget::item, QListView::item, QTreeWidget::item, QTreeView::item {{
        background: transparent;
        color: {text};
        padding: 2px 4px;
    }}

    QListWidget::item:selected, QListView::item:selected, QTreeWidget::item:selected, QTreeView::item:selected {{
        background-color: {table_selection_bg};
        color: {selection_text};
    }}

    QListWidget::item:selected:active, QListView::item:selected:active, QTreeWidget::item:selected:active, QTreeView::item:selected:active {{
        background-color: {table_selection_bg};
        color: {selection_text};
    }}

    QListWidget::item:selected:!active, QListView::item:selected:!active, QTreeWidget::item:selected:!active, QTreeView::item:selected:!active {{
        background-color: {table_selection_bg};
        color: {selection_text};
    }}

    QListWidget::item:hover, QListView::item:hover, QTreeWidget::item:hover, QTreeView::item:hover {{
        background-color: {row_hover_bg};
    }}

    QTreeWidget::branch:selected, QTreeView::branch:selected {{
        background-color: {table_selection_bg};
    }}

    QHeaderView {{
        background-color: {table_header_bg};
    }}

    QHeaderView::section {{
        background-color: {table_header_bg};
        color: {table_header_text};
        border: 1px solid {border};
        padding: 4px 6px;
    }}

    QTableCornerButton::section {{
        background-color: {table_header_bg};
        border: 1px solid {border};
    }}
    
    #statusBrandingLabel {{
        color: {subtle_text};
        padding: 0 6px;
        font-size: 11px;
        font-weight: 600;
    }}

""".format(**theme)
