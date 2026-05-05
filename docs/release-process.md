# Release Process

## Purpose

This document defines a lightweight release process for Nexus Core. The process is intended to support open-source use and enterprise review while recognizing that the project is currently maintained by a single primary contributor.

## Versioning

Semantic versioning is recommended:

```text
MAJOR.MINOR.PATCH
```

Guidance:

- Increment MAJOR for incompatible platform, plugin, manifest, or state-contract changes.
- Increment MINOR for backward-compatible platform features.
- Increment PATCH for backward-compatible bug fixes and documentation updates.

## Release Artifacts

A release should include:

- source code archive;
- changelog or release notes;
- documentation updates;
- dependency manifest, when available;
- SBOM, when available;
- scan status summary;
- approved plugin list, when applicable.

## Release Readiness Checklist

Before tagging a release:

- Application starts with `python nexus.py`.
- Bundled platform plugins load.
- Plugin Manager opens and shows plugin metadata.
- Workspace layout can be created, saved, and restored.
- Theme switching works across the workspace.
- Command registry and shortcut registry initialize.
- Local state persistence is verified.
- GitHub Code Scanning findings are reviewed.
- Dependabot alerts are reviewed.
- Documentation is updated for changed behavior.
- Known limitations are documented.

## Security Review Gate

For each release candidate:

1. Review GitHub Code Scanning findings.
2. Resolve or document findings.
3. Review Dependabot alerts.
4. Resolve or document dependency vulnerabilities.
5. Confirm no unintended outbound network behavior was added to core.
6. Confirm plugin execution model and trust boundaries remain accurately documented.

## Functional Validation Gate

At minimum, validate:

- startup from repository root;
- plugin discovery;
- opening bundled utility tools;
- opening official generic tools included with the repo, when present;
- workspace split/tab/floating behavior;
- state save/restore;
- theme switching;
- command palette or command discovery features;
- plugin enablement preferences.

## Documentation Gate

Update documentation when a release changes:

- plugin manifest schema;
- plugin discovery behavior;
- supported Python or Qt versions;
- local persistence format;
- security posture;
- source folder trust classifications;
- public framework APIs;
- command/action/context/service patterns;
- user-facing workspace behavior.

## Single-Contributor Release Control

Nexus Core currently has a single primary contributor. Releases should therefore rely on documented release gates and automated analysis to provide repeatability.

Recommended release evidence:

- commit hash;
- release tag;
- Code Scanning status;
- Dependabot status;
- functional validation notes;
- list of known limitations;
- generated SBOM, when available.

## Changelog Guidance

Release notes should separate:

- Added;
- Changed;
- Fixed;
- Security;
- Documentation;
- Known Limitations.

Avoid mixing plugin-specific release notes into Nexus Core release notes unless the plugin is bundled as part of the core distribution and the change affects platform behavior.

## Enterprise Release Approval Package

For enterprise adoption, package:

- source archive;
- README;
- LICENSE;
- NOTICE;
- SECURITY.md;
- `docs/` folder;
- SBOM;
- dependency manifest;
- scan summary;
- approved plugin inventory;
- deployment notes;
- release tag or commit hash.
