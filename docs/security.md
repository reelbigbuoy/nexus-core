# Security Documentation

## Plugin Governance Model

Nexus Core includes **built-in and official plugins as part of its release package**. These plugins are:

- Maintained within the Nexus Core repository
- Subject to the same development, security scanning (CodeQL), and dependency monitoring (Dependabot)
- Reviewed and validated as part of the Nexus Core release process

As such, built-in and official plugins are considered part of the **trusted platform baseline** and **do not require separate approval or review**.

Plugins that are not included in the Nexus Core repository (external or third-party plugins) are **not governed by Nexus Core processes** and must be reviewed and approved independently according to organizational policy prior to use.
