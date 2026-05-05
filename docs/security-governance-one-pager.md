# Nexus Core Security and Governance One-Pager

## Classification

Nexus Core is a local-first application platform and plugin runtime for internal tooling. It provides shared platform capabilities such as workspace management, reusable UI components, plugin loading, event communication, shared state, and session persistence.

It does not provide domain-specific systems development, requirements development, test development, or STAT-specific functionality.

## Trusted Release Baseline

The Nexus Core release package includes:

- Core runtime
- Workspace framework
- Shared services
- Built-in plugins
- Official plugins maintained within the repository

Built-in and official plugins are part of the trusted baseline. They are governed by the same development, security scanning, dependency monitoring, and release validation processes as the core platform.

## External Plugin Boundary

External or third-party plugins are not included in the Nexus Core release package and are not governed by Nexus Core processes. These plugins should be reviewed and approved independently according to organizational policy prior to deployment.

## Security Controls

- GitHub CodeQL static analysis enabled
- GitHub Dependabot vulnerability monitoring enabled
- Local filesystem persistence
- No outbound network calls by default
- Manual plugin installation
- Python 3.8+ and PyQt5 runtime requirements

## Known Limitations

- Plugins execute in-process
- Nexus Core does not currently enforce sandboxing
- External plugin trust is policy-governed

## Approval Recommendation

Approve Nexus Core as a governed application platform baseline. Treat built-in and official plugins as part of the approved release package. Require separate review only for plugins introduced from outside the Nexus Core repository or release package.
