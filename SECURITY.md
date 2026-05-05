# Security Policy

## Scope

This policy applies to the Nexus Core repository only.

Nexus Core is a local-first, plugin-based desktop application platform. It provides workspace, runtime, UI framework, service, and plugin-hosting infrastructure. Plugins, extensions, generated tools, organization-specific tools, and third-party integrations may have their own security posture and must be reviewed separately unless explicitly included in the reviewed release scope.

## Security Posture Summary

Current Nexus Core security characteristics:

- Nexus Core does not make outbound network calls by default.
- Workspace and session state are persisted locally.
- Plugins execute in-process within the same Python interpreter as Nexus Core.
- Plugins are discovered from local plugin folders and manifest files.
- Nexus Core does not currently enforce plugin sandboxing or per-plugin runtime permissions.
- GitHub Code Scanning is enabled for static analysis.
- GitHub Dependabot is enabled for dependency vulnerability monitoring.
- The project is currently maintained by a single primary contributor under Reel Big Buoy Company stewardship.

See [`docs/security.md`](docs/security.md) for the full security posture.

## Supported Versions

Security review and remediation are focused on the current active branch and tagged releases when available. Enterprise users should approve a specific release tag or commit hash and maintain their own approved dependency and plugin inventory.

## Reporting a Vulnerability

If you discover a security vulnerability in Nexus Core, please report it responsibly.

Do not open a public issue for security vulnerabilities.

Report the issue directly to:

**Email:** security@reelbigbuoy.com

Please include as much detail as possible:

- description of the vulnerability;
- affected files, versions, or commit hashes;
- steps to reproduce;
- potential impact;
- whether the issue affects core, bundled utilities, or a plugin;
- suggested mitigation, if available.

## Response Process

Reel Big Buoy Company will review reported vulnerabilities and determine appropriate action.

The intended response process is:

1. Acknowledge receipt when possible.
2. Validate and reproduce the issue.
3. Determine affected scope.
4. Develop and test remediation.
5. Release or document mitigation.
6. Coordinate disclosure when appropriate.

Response times may vary based on severity, reproducibility, and maintainer availability.

## Disclosure

Please do not publicly disclose a vulnerability until it has been reviewed and addressed or a coordinated disclosure date has been agreed upon.

## Plugin Security

Plugins are executable Python code loaded into the Nexus Core process. Users and organizations are responsible for reviewing plugins before deployment.

A plugin security review should consider:

- source and ownership;
- dependency list;
- file access;
- network behavior;
- subprocess usage;
- dynamic code execution;
- persistence behavior;
- sensitive data handling.

## Enterprise Use

Organizations integrating Nexus Core into controlled environments should review [`docs/enterprise-adoption.md`](docs/enterprise-adoption.md), generate or retain dependency/SBOM records, approve plugin inventory separately, and archive code scanning/dependency status for the approved release.
