# Nexus Core

Nexus Core is an open-source, domain-agnostic desktop application platform for building and hosting plugin-based tools.

Created and maintained by Reel Big Buoy Company, Nexus Core provides the shared infrastructure needed to build modern workspace-style applications with docking layouts, reusable UI primitives, command-driven interactions, local session persistence, plugin-based extensibility, shared data services, and reusable graph-capable framework components.

Nexus Core standardizes **how tools are hosted, integrated, and developed**. It does not define specialized domain workflows. Domain-specific capabilities belong in separately reviewed plugins.

---

## What Nexus Core Provides

Nexus Core includes foundational platform capabilities:

- Workspace and docking system for multi-pane layouts.
- Multi-window, tabbed, floating, and dockable tool hosting.
- Plugin discovery, manifest validation, loading, and lifecycle management.
- Shared service registry and plugin context.
- Event bus for decoupled communication.
- Shared observable data store.
- Command and action frameworks.
- Context tracking for active tools and windows.
- Local session and workspace state persistence.
- Theme system and reusable UI framework.
- Qt compatibility bridge and enhanced reusable widgets.
- Generic graph editor framework components.
- Bundled generic platform utility plugins.

---

## What Nexus Core Is Not

Nexus Core is not a complete end-user solution and is not a domain-specific systems development toolkit.

This repository does **not** provide:

- proprietary business logic;
- organization-specific data models;
- premium plugin capabilities;
- approval of third-party plugins.

Those capabilities may be built as plugins and reviewed independently.

---

## Architecture Overview

Nexus Core is organized into several platform layers:

```text
Plugins / Tools
    ↓
Nexus Runtime and Plugin Loader
    ↓
Core Services: events, data, commands, actions, context, state
    ↓
Framework: reusable widgets, tools, surfaces, graph services
    ↓
Workspace Shell: windows, panes, tabs, layout, themes
    ↓
Python 3.8+ / PyQt5 / Operating System
```

See [`docs/architecture.md`](docs/architecture.md) for the full architecture description.

---

## Repository Structure

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
docs/                            Platform documentation
```

---

## Requirements

- Python 3.8 or later.
- PyQt5.
- A desktop environment capable of running Qt applications.

A standardized dependency manifest is recommended for enterprise deployment.

---

## Running Nexus Core

From the repository root:

```bash
python nexus.py
```

---

## Plugin Model

Plugins are manually placed into plugin folders and discovered through `plugin.json` manifests. Nexus Core can also load user-local plugins and plugins from paths listed in the `NEXUS_PLUGIN_PATH` environment variable.

Plugins execute in-process in the same Python interpreter as Nexus Core. Only deploy trusted or reviewed plugins in controlled environments.

See [`docs/plugin-author-guide.md`](docs/plugin-author-guide.md) for plugin authoring details.

---

## Security Posture

Nexus Core is local-first and does not make outbound network calls by default. Workspace/session state is stored locally. Plugins execute in-process and must be reviewed separately.

The repository uses GitHub Code Scanning for static analysis and GitHub Dependabot for dependency vulnerability monitoring.

See [`SECURITY.md`](SECURITY.md) and [`docs/security.md`](docs/security.md).

---

## Documentation

Start with [`docs/documentation-index.md`](docs/documentation-index.md).

Key documents:

- [`docs/architecture.md`](docs/architecture.md)
- [`docs/developer-guide.md`](docs/developer-guide.md)
- [`docs/plugin-author-guide.md`](docs/plugin-author-guide.md)
- [`docs/user-guide.md`](docs/user-guide.md)
- [`docs/security.md`](docs/security.md)
- [`docs/dependency-management.md`](docs/dependency-management.md)
- [`docs/release-process.md`](docs/release-process.md)
- [`docs/governance.md`](docs/governance.md)
- [`docs/enterprise-adoption.md`](docs/enterprise-adoption.md)

---

## Governance

Nexus Core is currently maintained by Reel Big Buoy Company with a single primary contributor. Contribution workflows are structured to support future peer review and multi-contributor governance, but current release control relies on maintainer review, automated scanning, and functional validation.

See [`docs/governance.md`](docs/governance.md).

---

## License

Nexus Core is licensed under the Apache License, Version 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
