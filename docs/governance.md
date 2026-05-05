# Governance

## Project Stewardship

Nexus Core is developed and maintained by Reel Big Buoy Company. Project direction, architecture decisions, release approvals, and merge approvals remain under Reel Big Buoy Company stewardship.

## Current Contributor Model

Nexus Core currently has a single primary contributor. Contribution workflows are structured to support pull requests and future peer review, but current releases may be reviewed and approved by the maintainer.

This should be represented transparently in enterprise submissions. The current governance approach relies on:

- version-controlled source history;
- documented project scope;
- automated GitHub Code Scanning;
- GitHub Dependabot monitoring;
- functional validation prior to release;
- documented release gates;
- explicit maintainer ownership.

## Project Scope Control

Nexus Core is a domain-neutral platform. Governance decisions should protect the boundary between core platform infrastructure and plugin-specific functionality.

Accepted core scope includes:

- workspace shell;
- plugin runtime;
- UI framework;
- shared services;
- command/action/context/data infrastructure;
- local state persistence;
- generic graph editor framework;
- platform utility plugins;
- documentation and examples.

Excluded from core scope:

- proprietary workflows;
- organization-specific business logic;
- domain-specific systems development processes;
- specialized requirements or test development flows;
- premium plugin capabilities;
- private plugin documentation.

## Contribution Review Criteria

Contributions should be evaluated against:

- alignment with domain-neutral platform scope;
- maintainability;
- security impact;
- dependency impact;
- compatibility with existing plugin contracts;
- effect on local persistence contracts;
- user experience consistency;
- documentation completeness.

## Merge Authority

All merges remain subject to approval by Reel Big Buoy Company or authorized maintainers designated by Reel Big Buoy Company.

## Future Governance

As the project grows, governance may expand to include:

- additional maintainers;
- required peer review for pull requests;
- signed release artifacts;
- formal maintainer roles;
- plugin certification criteria;
- release branch protections;
- security advisory workflow through GitHub.
