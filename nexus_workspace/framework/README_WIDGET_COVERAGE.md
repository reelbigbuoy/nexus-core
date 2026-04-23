# Nexus UI Framework Widget Coverage

This note summarizes the framework-level wrappers now available under `nexus_workspace.framework`.

## Core controls

- Frame: `NexusFrame`
- Sub-Window: `NexusSubWindow`
- Menu: `NexusMenuBar`, `NexusMenu`
- Sub-Menus: `NexusMenu.add_nexus_menu(...)`
- Label: `NexusLabel`
- Text Input: `NexusTextInput`
- Buttons: `NexusButton`
- Checkboxes: `NexusCheckBox`
- Radio Buttons: `NexusRadioButton`
- Sliders: `NexusSlider`
- Combo Box: `NexusComboBox`
- Spinbox: `NexusSpinBox`, `NexusDoubleSpinBox`
- Table Viewer: `NexusTableView`
- Table Editor: `NexusTableEditor`
- Text Editor: `NexusTextEditor`
- Hierarchy View: `NexusHierarchyView`
- Progress Bar: `NexusProgressBar`
- Tab View: `NexusTabWidget`
- List View: `NexusListWidget`
- Tooltip: `NexusTooltip`
- Stacked Widget: `NexusStackedWidget`
- Scroll Area: `NexusScrollArea`
- Context Menu: `NexusContextMenu`
- Custom Toolbars: `NexusToolbar`, `NexusToolbarRow`

## Windowing and dialogs

- Window: `NexusWindowBase`
- Dialog Box: `NexusDialogBase`, `NexusMessageDialog`
- Title bar and shared chrome: `NexusTitleBar`

## Graph and charts

- Graph canvas: `NexusSimpleGraphCanvas`
- Bar chart: `NexusBarChartView`
- Pie chart: `NexusPieChartView`
- Line chart: `NexusLineChartView`
- Generic chart surface: `NexusChartView`

## Notes

- Chart wrappers gracefully fall back to a placeholder surface when the Qt chart module is not installed.
- Existing framework classes remain available; these wrappers expand the UI surface so plugins can avoid direct Qt imports in common cases.


## Qt import policy

Nexus framework now includes `nexus_workspace.framework.qt` as the single compatibility bridge for Qt modules outside the framework implementation itself. Plugin and shared widget code should not import `PyQt5` or `PySide6` directly. Prefer Nexus wrapper controls from `nexus_workspace.framework` for standard UI widgets and use `nexus_workspace.framework.qt` only for lower-level Qt types such as events, painters, graphics scenes, timers, models, or enums that do not yet have first-class Nexus wrappers.
