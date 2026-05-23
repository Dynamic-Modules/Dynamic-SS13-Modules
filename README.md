# Dynamic SS13 Modules

Dynamic SS13 Modules is a build-time module manager for tgstation-style SS13
downstreams. It is designed to let servers install, pin, update, configure,
test, and explain portable modules without committing generated source edits.

The core promise is:

```text
Host repo stays clean.
Modules live under dynamic_modules/.
Build artifacts live under .dynamic_modules_build/.
Exact resolved module state lives in dynamic_modules.lock.json.
Everything generated is traceable back to a manifest entry.
```

## Current implementation

This repo contains the first working framework slice:

- Python CLI exposed as `dynamic-modules`
- host config loading from `dynamic_modules.toml`
- recursive `*.module.toml` discovery
- manifest validation
- dependency, conflict, and load-order resolution
- deterministic lockfile generation
- generated DM include and unit-test include manifests
- module config defaults and host override export
- structured patch materialization into disposable build output
- server-local module source patch overlays
- machine-readable `.dynamic_modules_build/index.json`
- `doctor`, `explain`, and `test-plan` maintainer commands
- generated editor metadata consumed by the dedicated VS Code extension

## Quick start

From a host tg-style repo:

```bash
dynamic-modules init
dynamic-modules scan
dynamic-modules resolve --write-lock
dynamic-modules prepare
dynamic-modules explain code/modules/mob/living/carbon/human/human.dm
```

Generated output is disposable. Commit the host config, module manifests or
submodule gitlinks, and `dynamic_modules.lock.json`; do not commit
`.dynamic_modules_build/`.

## Documentation

- [Architecture](docs/architecture.md)
- [Manifest format](docs/manifest.md)
- [Hooks and patches](docs/hooks-and-patches.md)
- [TGS integration](docs/tgs-integration.md)
- [Maintainer workflows](docs/maintainer-workflows.md)
- [VS Code extension integration](docs/vscode-extension.md)

## Development

Run the test suite with the standard library runner:

```bash
python3 -m unittest discover -s tests
```

Run the CLI directly from a checkout:

```bash
python3 -m dynamic_ss13_modules --help
```
