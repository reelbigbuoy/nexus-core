# Dependency Management

## Scope

This document describes dependency management expectations for Nexus Core. Plugin-specific dependencies should be documented and approved separately.

## Runtime Dependencies

Nexus Core requires:

- Python 3.8 or later.
- PyQt5.

The repository currently does not include a standardized dependency manifest such as `requirements.txt` or `pyproject.toml`. For enterprise adoption, the approved deployment should define and version-control an explicit dependency manifest.

## Recommended Dependency Manifest

A future release should add one of the following:

- `requirements.txt` for a simple pinned runtime environment.
- `pyproject.toml` for package metadata, dependency declaration, build configuration, and tooling configuration.

For enterprise review, pinned dependency versions are preferred over unbounded ranges.

Example policy:

```text
PyQt5==<approved_version>
```

## Dependency Review Principles

Nexus Core dependencies should be:

- necessary for platform functionality;
- actively maintained;
- compatible with Python 3.8+;
- license-compatible with Apache-2.0 distribution;
- reviewed through GitHub Dependabot when represented in dependency manifests;
- minimized to reduce supply chain risk.

## GitHub Dependabot

Dependabot is enabled for the repository. Dependabot monitors dependency manifests for known vulnerabilities and can propose updates when patched versions are available.

Dependabot alerts should be triaged before release. Accepted or deferred alerts should be documented according to organizational policy.

## GitHub Code Scanning

GitHub Code Scanning is enabled for static analysis of the codebase. While Code Scanning is not a dependency manager, it helps identify vulnerable patterns in application code and should be part of release readiness.

## SBOM Recommendation

For enterprise adoption, generate a Software Bill of Materials for approved release packages. The SBOM should include:

- direct dependencies;
- transitive dependencies where tooling supports it;
- package versions;
- licenses;
- generation date;
- Nexus Core release version or commit hash.

Recommended formats:

- CycloneDX JSON.
- SPDX JSON.

## Plugin Dependencies

Plugins may introduce additional dependencies. Because plugins execute in-process, plugin dependencies become part of the effective application runtime when the plugin is installed.

Each plugin should document:

- additional Python packages;
- native libraries;
- external applications;
- file formats;
- network or service dependencies;
- license obligations.

Enterprise approval should treat plugin dependencies separately from Nexus Core dependencies.

## Dependency Update Process

Recommended process:

1. Review Dependabot alert or planned dependency update.
2. Confirm license compatibility.
3. Update dependency manifest.
4. Run application startup validation.
5. Validate plugin discovery and bundled tools.
6. Review Code Scanning results.
7. Document the change in release notes.
8. Tag or archive the approved version.

## Approved Environment Record

Enterprise users should maintain an approved environment record containing:

- Nexus Core version or commit hash;
- Python version;
- PyQt5 version;
- OS version;
- dependency manifest;
- SBOM;
- approved plugin list;
- scan status at approval time.
