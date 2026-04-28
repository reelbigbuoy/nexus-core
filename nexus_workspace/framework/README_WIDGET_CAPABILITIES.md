# Nexus UI Widget Capability Standard

The Nexus UI framework now treats wrappers as **Qt capability-preserving controls**. First-class Nexus widgets subclass their Qt base widgets directly, so native Qt methods, properties, signals, models, delegates, drag/drop behavior, and event handling remain available.

The Nexus layer adds:

- `nexus_id`
- `nexus_metadata()` / `set_nexus_metadata()`
- `set_nexus_meta()` / `nexus_meta()`
- `set_nexus_theme_role()`
- `set_nexus_variant()`
- `nexus_capabilities()`
- `get_nexus_widget_capabilities()` registry helper

Design rule:

> A Nexus widget must be at least as capable as its Qt base widget, then add Nexus-specific theme, metadata, schema, and convenience behavior.

Plugin Builder should use these capability schemas as the foundation for widget-specific properties and future signal/slot mapping.
