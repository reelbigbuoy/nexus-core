# Nexus Core Developer Guide

## Scope

This guide is for developers modifying Nexus Core itself. It focuses on the platform, workspace, runtime, framework, and shared service layers. It does not describe domain-specific plugin development beyond the platform interfaces needed to keep core code extensible.

For plugin development, see [Plugin Author Guide](plugin-author-guide.md).

## Development Environment

Nexus Core requires:

- Python 3.8 or later.
- PyQt5.
- A desktop operating system capable of running Qt applications.

The repository currently does not include a standardized dependency manifest such as `requirements.txt` or `pyproject.toml`. Enterprise deployments should define and version-control a dependency manifest for the approved environment.

## Running the Application

From the repository root:

```bash
python nexus.py
```

## Repository Map

```text
nexus.py                         Application entry point
nexus_workspace/core/            Core contracts, services, state, events, commands
nexus_workspace/framework/       Reusable UI and tool framework
nexus_workspace/runtime/         Bootstrap and plugin loader
nexus_workspace/workspace/       Workspace shell, panes, windows, layout rendering
nexus_workspace/plugins/         Platform plugin base classes and bundled utilities
nexus_workspace/shared_widgets/  Shared workspace widgets
nexus_workspace/graph_editor/    Domain-neutral graph editor framework
plugins/                         Source-categorized plugin folders
```

## Design Principles

### Keep Core Domain-Agnostic

Nexus Core should provide platform infrastructure, not specialized workflow logic. When reviewing changes, ask whether the change benefits the general platform. If it only benefits one workflow, it probably belongs in a plugin.

### Prefer Services Over Direct Coupling

Use platform services, events, commands, action dispatching, and shared state to avoid direct plugin-to-plugin or tool-to-tool dependencies.

### Prefer Nexus Framework Widgets

Use the framework wrappers and `nexus_workspace.framework.qt` compatibility bridge where possible. Direct PyQt5 imports should be limited to framework internals or cases where no wrapper exists.

### Keep Persistence Versioned

Persisted state should use explicit contracts and version fields. Changes to state shape should be backward compatible or normalized through the state contract layer.

### Fail Gracefully

The platform should continue to start when an optional plugin fails to load. Plugin load errors should be visible through plugin loader records and diagnostics without crashing the application whenever possible.

## Core Services

### EventBus

Use EventBus for loosely coupled publish/subscribe behavior. This is appropriate for notifications such as tool activation, registry changes, or state-related events.

### DataStore

Use DataStore for shared observable state. Publish structured snapshots for platform registries and shared context. Avoid storing plugin-private implementation details in global platform keys.

### CommandService

Use CommandService for discoverable commands. Commands should have stable identifiers and clear metadata so they can be displayed in menus, palettes, shortcut preferences, or future automation layers.

### ActionDispatcher

Use ActionDispatcher when one component wants to request an action without knowing which component owns the implementation.

### ContextService

Use ContextService to make active tool/window context available to commands and UI behavior.

### ServiceRegistry

Use ServiceRegistry to publish reusable platform services behind stable service IDs. Service IDs should be namespaced, for example `platform.graph`.

## Workspace Development

Workspace-related work lives primarily under `nexus_workspace/workspace`.

The workspace layer owns:

- main windows and secondary workspace windows;
- pane and split models;
- tab behavior;
- drag/drop overlays;
- floating windows;
- workspace rendering;
- layout persistence and restoration integration.

When modifying workspace behavior, verify:

- layout save/restore still works;
- multi-monitor geometry remains safe;
- tabs and panes preserve expected tool identity;
- theme changes propagate to open tools and windows;
- plugin tools still register and open correctly.

## Framework Development

Framework-related work lives under `nexus_workspace/framework`.

Framework additions should be:

- reusable across multiple plugins;
- theme-aware;
- compatible with Qt capabilities;
- documented when they introduce new authoring patterns;
- stable enough for plugin authors to depend on.

The UI framework should reduce plugin burden without hiding essential Qt capabilities. Nexus widgets should remain at least as capable as their Qt base controls while adding Nexus metadata, theme roles, variants, and capability schemas.

## Runtime and Plugin Loader Development

Runtime-related work lives under `nexus_workspace/runtime`.

The plugin loader is responsible for:

- discovering plugin manifests;
- normalizing plugin metadata;
- validating manifest schema;
- checking version compatibility;
- importing plugin modules;
- instantiating plugin classes;
- registering plugins with the plugin manager;
- publishing loader state.

Any change to plugin loading should be reviewed carefully because plugins execute in-process and have full Python capability.

## State and Persistence Development

State-related work lives under `nexus_workspace/core/state.py` and related state contract modules.

Nexus Core persists workspace state locally. Persisted state includes preferences, shortcuts, plugin enablement overrides, recent entries, window geometry, workspace layout, and open tool state envelopes.

When changing persisted state:

- update state contracts where applicable;
- maintain version fields;
- normalize older state when possible;
- avoid storing sensitive data in platform state;
- allow plugins to own their own tool state boundaries.

## Graph Editor Framework Development

The graph editor under `nexus_workspace/graph_editor` is a reusable framework. It should remain domain-neutral. Generic graph functions such as node rendering, wire routing, selection, validation hooks, serialization, templates, and view manifests can live in core. Domain-specific node sets, validation policies, and workflows should live in plugins.

## Error Handling Guidelines

Use explicit exceptions where failure should stop the operation. Use graceful handling where failure should not bring down the entire workspace, such as optional plugin load failures or optional UI refreshes.

When an exception is intentionally suppressed, include a short explanatory comment before `pass` or the equivalent no-op behavior so static analysis reviewers can see the intent.

## Documentation Expectations

Changes should update documentation when they affect:

- plugin manifest fields;
- plugin loading behavior;
- public framework APIs;
- state contracts;
- service IDs;
- command/action patterns;
- security posture;
- deployment assumptions;
- user-visible workflows.

## Quality and Security Scanning

GitHub Code Scanning and Dependabot are enabled for the repository. Code changes should be reviewed against automated findings before release. The project is currently maintained by a single primary contributor, so automated analysis and functional validation are important release gates.

## Release Readiness Checklist

Before publishing a release candidate:

- Application starts successfully with the bundled plugins.
- Plugin Manager opens and displays plugin metadata.
- Command palette opens and command registry is populated.
- Workspace state saves and restores locally.
- Theme switching works across the workspace.
- Code scanning findings are reviewed and remediated or documented.
- Dependabot alerts are reviewed and remediated or documented.
- Documentation is updated for user-visible or API-impacting changes.
