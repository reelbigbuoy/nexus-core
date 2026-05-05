# Nexus Plugins

Nexus Core loads plugins from source-specific subfolders under this directory.

Plugins provide tool-specific functionality. Nexus Core provides the host/runtime environment, shared framework, and platform services.

## Layout

```text
plugins/
  builtin/        Platform-shipped utility plugins
  official/       First-party plugins
  organization/   Organization-controlled private plugins
  enterprise/     Enterprise/private plugins
  marketplace/    Verified marketplace plugins, if used
  third_party/    Manually installed external plugins
```

Each plugin should live in its own subdirectory and include a `plugin.json` manifest.

## Security Note

Plugins execute in-process with the Nexus Core Python interpreter. Only install and enable trusted or reviewed plugins in controlled environments.

See `docs/plugin-author-guide.md` and `docs/security.md`.
