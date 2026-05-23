# Manifest Format

Module manifests are TOML files ending in `.module.toml`.

```toml
id = "trip-system"
name = "Trip System"
version = "1.2.0"
module_api = "1"
description = "Adds slipping and tripping interactions."

[source]
repo = "https://github.com/example/trip-system.git"
default_branch = "main"

[compat]
target = "tgstation"
minimum_dynamic_modules = "0.1.0"

[load]
requires = ["example-module >= 1.0.0"]
optional = ["movement-hooks"]
conflicts = ["old-trip-system"]
load_after = ["movement-hooks"]
load_before = ["combat-overrides"]

[build]
dm_files = ["code/**/*.dm"]
test_files = ["tests/**/*.dm"]
assets = ["icons/**/*.dmi", "sound/**/*.ogg"]
tgui = ["tgui/**/*.tgui.ts"]

[[prepare_plugins]]
id = "trip-build-metadata"
command = "python3"
args = ["tools/prepare_plugin.py"]
description = "Writes extra build metadata consumed by this module."

[config]
schema = "config/config.schema.json"
defaults = "config/default.toml"
version = 1

[[hooks]]
id = "human-movement-trip-check"
target = "/mob/living/carbon/human/proc/Move"
target_file = "code/modules/mob/living/carbon/human/human_movement.dm"
mode = "generated_hook"
file = "hooks/human_movement_trip_check.dm"

[[patches]]
id = "legacy-human-move-anchor"
target_file = "code/modules/mob/living/carbon/human/human_movement.dm"
mode = "insert_after"
anchor = "return ..()"
file = "patches/human_move_trip_check.dm"
occurrence = 1
risk = "escape_hatch"
```

## Dependency syntax

Dependencies support simple semantic version constraints:

```text
module-id
module-id >= 1.2.0
module-id == 1.2.3
module-id < 2.0.0
```

`requires` is mandatory. Missing or incompatible required modules fail
resolution.

`optional` only affects load order when the module is present and satisfies the
constraint.

`load_after` and `load_before` are ordering hints. Missing hint targets produce
warnings, not hard failures.

## Prepare plugins

`[[prepare_plugins]]` lets a module run a small build-time integration step
during `dynamic-modules prepare`. Plugins run in resolved module load order
after core DM/test/config/patch materialization and before the final
`.dynamic_modules_build/index.json` is written.

The plugin command runs with its working directory set to the module root.
Arguments are passed exactly as listed in the manifest, so relative script
paths resolve naturally from that module root.

The framework passes these environment variables:

```text
DYNAMIC_MODULES_PREPARE_API=1
DYNAMIC_MODULES_PREPARE_CONTEXT=/absolute/path/to/.dynamic_modules_build/prepare_plugins/context.json
DYNAMIC_MODULES_PREPARE_OUTPUT=/absolute/path/to/.dynamic_modules_build/prepare_plugins/<module>__<plugin>.json
DYNAMIC_MODULES_PREPARE_PLUGIN_ID=<plugin id>
DYNAMIC_MODULES_PREPARE_PLUGIN_MODULE=<module id>
DYNAMIC_MODULES_HOST_ROOT=/absolute/path/to/host
DYNAMIC_MODULES_BUILD_DIR=/absolute/path/to/host/.dynamic_modules_build
DYNAMIC_MODULES_INDEX=/absolute/path/to/host/.dynamic_modules_build/index.json
```

The context JSON contains `api_version`, host/build paths, `load_order`, and
per-module metadata including collected `dm_files`, `test_files`, `tgui_files`,
`asset_files`, hooks, patches, and plugin declarations.

The plugin must write a JSON object to `DYNAMIC_MODULES_PREPARE_OUTPUT`:

```json
{
  "generated": {
    "example_file": ".dynamic_modules_build/generated/example.json"
  },
  "modules": {
    "trip-system": {
      "extra_metadata": ["value"]
    }
  },
  "files": {
    "code/example.dm": [
      {
        "kind": "prepare_plugin",
        "module": "trip-system",
        "id": "trip-build-metadata"
      }
    ]
  },
  "warnings": []
}
```

All top-level fields are optional. `generated` is merged into
`index.generated`, `modules` is merged into matching `index.modules` entries,
`files` adds explainable interactions to `index.files`, and `warnings` are
prefixed with the owning module/plugin id.

## TGUI overlays

`build.tgui` lists module-owned Dynamic TGUI manifest files. During `prepare`,
matching files are written to the generated index as `tgui_files` for the
owning module.

Dynamic TGUI consumes those files in resolved module load order. Modules that
ship tgui overlays should depend on `dynamic-tgui`:

```toml
[load]
requires = ["dynamic-tgui"]

[build]
tgui = ["tgui/**/*.tgui.ts"]
```

Dynamic TGUI owns its prepare plugin and emits `.dynamic_modules_build/tgui/cli.ts`,
a stable wrapper for host `tgui/package.json` scripts.
