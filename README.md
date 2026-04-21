# Nexus Core

Nexus Core is an open-source modular application framework for building extensible desktop tooling environments.

Created and maintained by Reel Big Buoy Company, Nexus Core provides the shared infrastructure needed to build modern workspace-style applications with docking layouts, reusable UI primitives, command-driven interactions, plugin-based extensibility, and graph-capable workflows.

Nexus Core is designed to serve as a strong foundation for developers and organizations that want to build custom tools on top of a consistent, scalable desktop platform architecture.

---

## Overview

Nexus Core focuses on providing a clean, flexible platform layer that can be used to construct a wide range of desktop applications. It emphasizes modularity, extensibility, and separation of concerns through a structured framework and plugin system.

The platform is intentionally domain-agnostic and can be adapted to support many different types of tooling and workflows.

---

## What’s Included

Nexus Core includes the foundational components required to build extensible desktop applications:

- Workspace and docking system for multi-pane layouts
- Windowing and dialog abstractions
- Command and action frameworks
- Shared service and context systems
- Plugin discovery, loading, and lifecycle management
- Theme and application state management
- Reusable UI widgets and inspector infrastructure
- Generic graph-capable framework components

---

## What Nexus Core Is For

Nexus Core can be used to build:

- Internal desktop tools
- Technical workspaces
- Editor-style applications
- Plugin-driven platforms
- Visualization and graph-based tools
- Custom enterprise or engineering utilities

---

## What Nexus Core Is Not

Nexus Core is a platform foundation, not a complete end-user solution.

This repository focuses on reusable core infrastructure and bundled platform utilities. Domain-specific tools, private extensions, and proprietary plugin ecosystems may be built on top of Nexus Core separately and are not implied to be part of this repository.

---

## Architecture Overview

Nexus Core is structured into several major layers:

- **Workspace Layer**  
  Provides docking, layout management, panes, and window coordination.

- **Framework Layer**  
  Includes reusable UI components, graph support, tool abstractions, and interaction patterns.

- **Core Services Layer**  
  Handles commands, events, state management, context propagation, and shared services.

- **Plugin System**  
  Supports dynamic discovery, loading, and integration of external tools and extensions.

- **Bundled Utilities**  
  Includes a small set of generic inspector-style tools to support platform usage.

---

## Getting Started

### Requirements

- Python 3.8+ (or your current supported version)
- Required dependencies (see your requirements file if applicable)

### Run Nexus Core

```bash
python nexus.py