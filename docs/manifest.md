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

When `dynamic-tgui` is installed, `prepare` also emits
`.dynamic_modules_build/tgui/cli.ts`, a stable wrapper for host
`tgui/package.json` scripts.
