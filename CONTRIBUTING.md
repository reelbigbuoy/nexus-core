# Contributing to Nexus Core

Thank you for your interest in contributing to Nexus Core.

Nexus Core is an open-source platform developed and maintained by Reel Big Buoy Company. Contributions are welcome when they improve the reusable, domain-neutral platform.

## Project Scope

Nexus Core provides platform infrastructure:

- workspace shell;
- plugin runtime;
- reusable UI framework;
- command, action, context, event, service, and data infrastructure;
- local session persistence;
- generic graph editor framework;
- generic platform utility plugins;
- documentation and examples.

Nexus Core should not include domain-specific workflows, proprietary business logic, or private/premium plugin capabilities.

## Getting Started

Before contributing:

1. Read the README.
2. Review [`docs/architecture.md`](docs/architecture.md).
3. Review [`docs/developer-guide.md`](docs/developer-guide.md).
4. Confirm your change belongs in Nexus Core rather than a plugin.
5. Open an issue for significant changes before implementation.

## Types of Contributions

Contributions may include:

- bug fixes;
- performance improvements;
- documentation updates;
- framework/widget improvements;
- workspace usability improvements;
- generic plugin runtime improvements;
- generic graph framework improvements;
- security hardening.

## Contribution Guidelines

Please:

- keep changes focused and well-scoped;
- follow existing code style and project structure;
- avoid unnecessary dependencies;
- preserve backward compatibility where practical;
- update documentation when behavior or public interfaces change;
- avoid direct PyQt imports outside framework or low-level Qt integration points when a Nexus wrapper exists;
- avoid adding domain-specific assumptions to core;
- include explanatory comments for intentionally suppressed exceptions or no-op exception handling.

## Pull Request Process

1. Fork the repository.
2. Create a feature branch.
3. Make focused changes.
4. Run local functional validation.
5. Review GitHub Code Scanning and Dependabot results when available.
6. Update documentation where applicable.
7. Submit a pull request with a clear description.

Pull request workflows are supported. The project currently has a single primary contributor, so current review may be maintainer self-review supported by automated analysis and functional validation. As the project grows, workflows are intended to support independent peer review.

## Security Contributions

Do not open public issues for security vulnerabilities. See [`SECURITY.md`](SECURITY.md) for reporting instructions.

## Project Governance

Nexus Core is maintained under the stewardship of Reel Big Buoy Company. Project direction, architecture decisions, releases, and merge approvals remain under Reel Big Buoy Company authority.

Not all contributions may be accepted, especially if they:

- conflict with the platform scope;
- introduce domain-specific behavior;
- create unnecessary dependencies;
- reduce maintainability;
- weaken plugin boundaries;
- bypass security or governance expectations.

See [`docs/governance.md`](docs/governance.md).

## License

By contributing to Nexus Core, you agree that your contributions will be licensed under the Apache License, Version 2.0.
