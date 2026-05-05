# Nexus Core User Guide

## What Nexus Core Is

Nexus Core is a desktop application platform for hosting plugin-based tools. It provides the workspace shell, plugin runtime, shared UI framework, local session persistence, command palette, plugin manager, and shared data mechanisms.

The core application is domain-neutral. Specific workflows and specialized capabilities are provided by plugins.

## Requirements

Nexus Core requires:

- Python 3.8 or later.
- PyQt5.
- A desktop environment that supports Qt applications.

## Starting Nexus Core

From the repository root, run:

```bash
python nexus.py
```

## Workspace Basics

The workspace provides a desktop-style environment for hosted tools. Depending on the installed plugins, tools can be opened from menus and arranged in the workspace.

Common workspace capabilities include:

- docked tools;
- tabbed panes;
- split layouts;
- floating windows;
- multi-window workspace behavior;
- persisted layout restoration.

## Opening Tools

Plugins register tools with the workspace. Available tools appear through the workspace UI, typically in tool or plugin menus. Opening a tool creates a hosted tool instance in the current workspace.

## Plugin Manager

The Plugin Manager displays discovered plugins and their metadata, including source and trust classification where available. Plugin enablement preferences may be saved in local workspace state.

Plugin changes may require restarting Nexus Core to fully apply load/unload behavior.

## Command Palette

Nexus Core includes a command system. Commands registered by the platform and plugins can be surfaced through command-oriented UI such as a command palette or menu actions.

Commands may also define keyboard shortcuts when supported by the command registry.

## Themes

Nexus Core includes a theme system. Runtime theme changes are intended to apply across the workspace and open tools that follow the Nexus framework theme patterns.

## Local Session State

Nexus Core saves local workspace state, including:

- window layout;
- open tool state envelopes;
- theme preference;
- shortcut bindings;
- recent entries;
- plugin enablement preferences.

State is stored locally using the operating system's application configuration location when available, with fallback behavior under the user's home directory.

## Adding Plugins

Plugins are manually placed into plugin folders. Typical repository plugin folders include:

```text
plugins/builtin/
plugins/official/
plugins/organization/
plugins/enterprise/
plugins/marketplace/
plugins/third_party/
```

User-local plugins may also be placed under:

```text
~/.nexus/plugins/
```

Additional plugin search paths can be provided with the `NEXUS_PLUGIN_PATH` environment variable.

Only use plugins from trusted or reviewed sources in controlled environments.

## Generated Plugins

The built-in Plugin Builder can export an initial plugin framework into a plugin folder. Generated plugins are starting points and should be reviewed before use in enterprise environments.

## Data and Network Behavior

Nexus Core itself is local-first and does not make outbound network calls by default. Plugins may implement their own file access or network behavior, so plugin behavior should be reviewed separately.

## Troubleshooting

### Application Does Not Start

Check that Python 3.8+ and PyQt5 are installed and that the application is being run from the repository root.

### Plugin Does Not Appear

Verify that:

- the plugin folder contains `plugin.json`;
- the manifest uses the supported schema;
- the module and class fields point to importable Python code;
- the plugin is in a searched plugin path;
- the plugin is enabled;
- the plugin is compatible with the current Nexus version.

### Workspace Layout Looks Wrong

Try using workspace recovery options if available, or remove the local workspace state file after backing it up. This will allow Nexus Core to start with a fresh layout.

### Theme Does Not Apply to a Tool

The tool may not be using Nexus framework theme patterns. Plugin authors should use Nexus framework widgets and theme hooks where practical.
