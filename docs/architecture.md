# Nexus Core Architecture

## Purpose

Nexus Core is a domain-agnostic desktop application platform for hosting, developing, and integrating plugin-based tools. The core repository provides the runtime environment, shared services, workspace shell, reusable UI framework, local state persistence, and plugin loading infrastructure needed to build tooling applications quickly and consistently.

Nexus Core is intentionally not a domain-specific systems development environment. Domain workflows, specialized analysis logic, proprietary capabilities, and organization-specific functionality belong in separately reviewed plugins.

## Architectural Goals

Nexus Core is designed around the following goals:

- Provide a consistent workspace for plugin-hosted tools.
- Reduce duplicated UI and application infrastructure across tools.
- Enable plugins to communicate through shared services instead of tight coupling.
- Keep the platform layer reusable, domain-neutral, and suitable for enterprise governance.
- Support local-first execution with no required external service dependency.
- Allow organizations to control which plugins are deployed and trusted.

## High-Level Layering

```text
+--------------------------------------------------------------+
| Plugins                                                      |
| Tool UIs, domain logic, generated tools, organization tools   |
+--------------------------------------------------------------+
| Nexus Core Runtime                                           |
| Plugin discovery, manifest validation, service registration   |
+--------------------------------------------------------------+
| Nexus Core Services                                          |
| EventBus, DataStore, commands, actions, context, sessions     |
+--------------------------------------------------------------+
| Nexus Framework                                              |
| Qt compatibility bridge, wrapped widgets, tools, surfaces     |
+--------------------------------------------------------------+
| Workspace Shell                                              |
| Main window, panes, docking, tabs, floating windows, themes   |
+--------------------------------------------------------------+
| Python 3.8+ / PyQt5 / Operating System                       |
+--------------------------------------------------------------+
```

## Major Packages

### `nexus_workspace.core`

The `core` package contains shared contracts and platform services used by the runtime, workspace, framework, and plugins.

Important modules include:

- `events.py` — event bus for publish/subscribe communication.
- `data_store.py` — observable shared state store.
- `command_service.py` and `command_contract.py` — command registration, search, execution, and shortcuts.
- `action_dispatcher.py` and `action_contract.py` — centralized action routing between tools and handlers.
- `context_service.py` and `context_contract.py` — active tool/context tracking.
- `plugin_contract.py` — plugin manifest data contracts and helper builders.
- `service_registry.py` and `services.py` — platform service registration and plugin context access.
- `state.py`, `state_contract.py`, `session.py`, and `serialization.py` — local session and workspace persistence.
- `themes.py` — theme registry and theme token definitions.

### `nexus_workspace.framework`

The `framework` package provides reusable UI, tool, and domain-neutral infrastructure. It wraps Qt objects where appropriate so plugin developers can use consistent Nexus widgets and patterns instead of repeatedly wiring low-level Qt behavior.

Important modules include:

- `qt.py` — compatibility bridge for Qt imports.
- `controls.py`, `forms.py`, `documents.py`, `charts.py`, and `surfaces.py` — reusable UI controls and composition primitives.
- `tools.py` — base classes for hosted Nexus tools.
- `actions.py` — higher-level command/action helpers.
- `windowing.py` — icon and window-related helpers.
- `projects.py`, `references.py`, `review.py`, and `graph.py` — domain-neutral registries for project/file conventions, references, reviewable artifacts, and graph domains.

### `nexus_workspace.workspace`

The `workspace` package implements the desktop shell and multi-pane workspace experience.

Important modules include:

- `main_window.py` — primary application window and startup coordination.
- `workspace_window.py` — workspace-level window behavior, menus, plugin manager access, and persisted layout interaction.
- `manager_workspace.py` — workspace model coordination and tool registration.
- `layout_model.py`, `renderer.py`, `pane.py`, `area.py`, and `tab_bar.py` — pane layout model, rendering, tabs, and interactive workspace composition.
- `frameless.py` — custom window chrome.
- `drop_overlay.py` — drag/drop placement affordances.

### `nexus_workspace.runtime`

The `runtime` package handles platform startup and plugin discovery.

Important modules include:

- `plugin_loader.py` — discovers `plugin.json` manifests, normalizes source metadata, validates manifest schema, checks version compatibility, imports plugin modules, and registers loaded plugins.
- `platform_bootstrap.py` — registers built-in platform services.
- `app_metadata.py` — application and manifest schema metadata.
- `dev_validation.py` — development-time validation support.

### `nexus_workspace.plugins`

The `plugins` package contains platform-level plugin abstractions and built-in generic tools.

Important modules include:

- `base.py` — `WorkspacePlugin` and `ToolDescriptor` base contracts.
- `manager.py` — plugin registration and tool descriptor management.
- `data_inspector` and `property_inspector` — bundled platform utility plugins.

### `nexus_workspace.shared_widgets`

The `shared_widgets` package contains reusable UI widgets that support the workspace experience, such as the command palette, plugin manager dialog, property grid, and shortcut preferences UI.

### `nexus_workspace.graph_editor`

The `graph_editor` package contains a reusable, domain-neutral graph editing framework. It provides graph models, node definitions, view manifests, graphics items, scene/view behavior, validation support, and graph authoring commands. It is part of Nexus Core because graph editing is treated as a reusable platform capability, not as a domain-specific workflow.

## Runtime Startup Flow

A typical startup sequence is:

1. `nexus.py` starts the application.
2. `WorkspaceMainWindow` initializes the core services and workspace manager.
3. `platform_bootstrap.bootstrap_platform_services()` registers shared platform services.
4. `PluginLoader.discover_and_load()` searches configured plugin locations.
5. Each discovered `plugin.json` manifest is loaded and normalized.
6. Valid and enabled plugins are imported into the Python process.
7. Plugin classes are instantiated and registered with the `PluginManager`.
8. Tool descriptors, commands, services, and plugin metadata are published to shared state.
9. Workspace state is restored from the local state file when available.

## Plugin Discovery and Loading

The plugin loader searches these locations by default:

- Repository `plugins/` folder.
- Repository `plugins_external/` folder, when present.
- User-local `~/.nexus/plugins` folder.
- Additional paths listed in the `NEXUS_PLUGIN_PATH` environment variable.

When the loader searches the repository `plugins/` folder, it expects source-category subfolders such as:

- `builtin`
- `official`
- `organization`
- `enterprise`
- `marketplace`
- `third_party`
- `user`

Each plugin is expected to live in its own folder with a `plugin.json` manifest.

## Plugin Source Metadata

`plugin_loader.py` classifies plugin sources into distribution and trust metadata. This metadata is used for visibility, governance, and review. It does not sandbox plugin execution.

Examples of source classification include:

| Source folder | Distribution channel | Distribution source | Trust label | Ownership label |
| ------------- | -------------------- | ------------------- | ----------- | --------------- |
| `builtin` | builtin | bundled | platform | platform |
| `official` | official | official | first_party | first_party |
| `organization` | organization | private | organization | organization |
| `enterprise` | enterprise | private | organization | organization |
| `marketplace` | marketplace | signed | verified | third_party |
| `third_party` | manual | external | unverified | third_party |
| `user` | manual | user | local | unknown |

These labels help reviewers and users understand where a plugin came from and how it should be governed.

## Plugin Execution Model

Plugins currently execute in-process within the same Python interpreter as Nexus Core. The platform imports plugin modules using Python import mechanisms and instantiates the configured plugin class. This means plugins have the same Python execution capability as any other code running in the application process.

Nexus Core does not currently enforce plugin sandboxing, process isolation, file-system permissions, or network permissions. Plugin trust is therefore managed through deployment policy, repository review, and organizational controls.

## Core Service Model

### Plugin Context

Plugins interact with platform services through `PluginContext`. This context exposes controlled access to shared platform capabilities such as:

- registering tools;
- publishing and reading shared state;
- subscribing to events;
- registering action handlers;
- registering and executing commands;
- registering and looking up platform services;
- publishing active tool context.

### Event Bus

The event bus enables decoupled communication. Components publish events and subscribers react without requiring direct references to one another.

Use events when a plugin or service needs to notify other parts of the workspace that something occurred.

### Data Store

The data store is a shared observable state container. It supports platform state publication such as plugin registry snapshots, command registries, service registries, current context, and other local runtime state.

Use the data store for state that should be observable or shared between components. Avoid using it as a hidden global store for plugin internals.

### Command Service

The command service provides centralized command registration and execution. It supports command metadata, categories, optional shortcuts, availability callbacks, and command search.

Use commands for actions that should be discoverable, invokable from menus or palettes, or available through keyboard shortcuts.

### Action Dispatcher

The action dispatcher routes structured actions to registered handlers. It is useful when tools need to request behavior without knowing which component will handle it.

### Context Service

The context service publishes the active tool/window context and enables context-aware command availability and UI behavior.

### Service Registry

The service registry lets platform services and plugins publish service instances under stable identifiers. This helps avoid direct imports and tight coupling across plugins.

## Local Persistence

Nexus Core persists workspace state locally using `StateManager`. The state file is written under Qt's application configuration location when available, with a fallback under the user's home directory.

Persisted state includes:

- current theme preference;
- shortcut bindings;
- recent entries;
- plugin enablement overrides;
- window geometry;
- workspace panes and layout model;
- open tool state envelopes.

The core platform does not use cloud persistence or a remote database.

## UI Framework and Qt Boundary

Nexus Core uses PyQt5 and provides a framework layer that wraps or standardizes common UI behaviors. Plugin code should prefer Nexus framework widgets and the `nexus_workspace.framework.qt` compatibility bridge instead of importing PyQt5 directly, unless lower-level Qt behavior is required and no Nexus wrapper exists.

This approach provides:

- consistent theme integration;
- consistent widget metadata and capability reporting;
- reduced duplicate UI code;
- easier future migration or framework evolution;
- a more consistent plugin authoring experience.

## Graph Editor Framework

The graph editor is a reusable platform framework for node-and-edge style UI. It provides generic graph authoring infrastructure and is not tied to a particular domain.

Core responsibilities include:

- graph and node data models;
- node definition loading;
- view manifest loading;
- scene/view interaction;
- graphics item rendering;
- connection handling;
- validation infrastructure;
- graph serialization support.

Domain-specific graph semantics should be implemented by plugins through view manifests, node definitions, services, or plugin-specific validation layers.

## Boundaries: What Belongs in Nexus Core

Appropriate Nexus Core content includes:

- workspace and shell behavior;
- plugin loading and metadata;
- generic UI framework improvements;
- shared state, command, action, context, and service infrastructure;
- local session persistence;
- generic graph editor capabilities;
- generic bundled utility tools;
- documentation, examples, and extension guides.

## Boundaries: What Does Not Belong in Nexus Core

The following should not be added to Nexus Core documentation or core platform code:

- proprietary business logic;
- organization-specific workflows;
- domain-specific systems development processes;
- specialized requirements development flows;
- specialized test development flows;
- program-specific schemas or data models;
- premium plugin features;
- private plugin documentation.

Those capabilities should remain in separately governed plugins.

## Enterprise Adoption Considerations

Nexus Core is structured to support enterprise review by separating reusable platform infrastructure from plugin-specific capabilities. Enterprise adopters can review the core once as a common runtime and then review plugins independently based on their source, trust level, functionality, dependencies, and deployment context.
