# Plugin Builder

Visual Nexus plugin designer with a layout-first editor, hierarchy tree, and export to `plugins/plugin-sandbox`.

## v1.6.0 layout editor notes

- Renames the former Visual Sandbox to **Layout Editor**.
- Adds responsive layout containers: **Vertical Stack** and **Horizontal Row**.
- Layout containers use real Qt/Nexus layouts in preview instead of fixed child coordinates.
- Layout container properties include spacing, margin, and fill-parent behavior.
- Child widgets inside layout containers are managed by the layout and scale with the workspace.
- Exported plugins now create a responsive root canvas and honor layout containers where used.
- Freeform geometry remains available for legacy/non-layout placement.

Visual Nexus plugin designer with a graphical sandbox, hierarchy tree, and export to `plugins/plugin-sandbox`.

## v1.5.9 manual hierarchy reorder notes

This iteration starts the move toward a model-driven Plugin Builder:

- toolbox drag payloads now use `application/x-pluginbuilder-widget`, matching the sandbox creation path
- hierarchy drag/drop now sends stable node IDs and mutates the builder model first instead of letting `QTreeWidget` become the source of truth
- hierarchy drops support before, after, and inside target zones
- existing nodes can be reparented from hierarchy into sandbox containers
- property editors now update the selected widget immediately instead of requiring Apply for every widget-specific property
- geometry spin boxes now update the preview immediately
- preview buttons now receive explicit theme-aware button styling so they no longer render like plain labels

The builder is still largely contained in `tool.py`; the next major refactor should split model, registry, renderer, controllers, and export into dedicated modules.

## v1.5.9 manual hierarchy reorder notes
- Replaces Qt item-view hierarchy drag/drop with controlled mouse-drag reordering.
- Avoids the forbidden Qt drag cursor path entirely.
- Supports moving before, after, and inside valid container/root targets.
