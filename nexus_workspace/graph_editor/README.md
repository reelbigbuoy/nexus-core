# Nexus Graph Editor Shared Framework

This package contains a reusable, domain-neutral graph editor implementation for Nexus Core.

The graph editor framework provides shared graph models, node definitions, view manifests, scene/view behavior, graphics items, wire routing, validation hooks, table-node behavior, templates, and serialization support.

Domain-specific graph semantics should be implemented by plugins using plugin-owned node definitions, view manifests, validation rules, services, or tool wrappers. Nexus Core should keep this package focused on generic graph editing infrastructure.
