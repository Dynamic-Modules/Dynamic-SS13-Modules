# Hooks And Patches

Dynamic SS13 Modules supports patches, but they should be the last option.

Preferred integration order:

1. Normal DM files with no upstream modification.
2. Existing signals, components, elements, subsystems, and config hooks.
3. Stable downstream-owned hook points.
4. Generated hook points owned by Dynamic Modules.
5. Structured patches as an escape hatch.

## Structured patches

Patches are declarative. They do not run arbitrary code.

Supported modes:

- `insert_before`
- `insert_after`
- `replace`
- `replace_between`

Each patch needs:

- module id from the owning manifest
- patch id
- target host file
- anchor text
- source patch file
- occurrence number

Anchors may be a single line or a multiline block. Single-line anchors keep the
legacy behavior: `insert_before`, `insert_after`, and `replace` operate on the
entire line containing the anchor. Multiline anchors match an exact text block,
which lets generated tools replace larger hunks without converting an entire
file into module-owned source. The `occurrence` field selects which matching
line or block to use.

`replace_between` uses `anchor` as the start anchor and `end_anchor` as the
first matching end anchor after it. The generated content replaces the text
between those anchors while leaving both anchor lines or blocks in place.

During `prepare`, patches materialize into `.dynamic_modules_build/patched/`.
The host checkout is not modified.

## Server-local module patches

Servers may also carry tiny local patches against installed module source
without making the module submodule dirty. Put patch manifests under:

```text
config/dynamic_modules/patches/**/*.toml
```

Each manifest contains `[[patches]]` tables. The `module` field selects the
installed module by id, `target_file` is relative to that module root, and
`file` is relative to the local patch manifest's directory.

```toml
[[patches]]
module = "trip-system"
id = "server-trip-extra-state"
target_file = "code/trip_system.dm"
mode = "insert_after"
anchor = "var/trip_chance = 5"
file = "extra_state.dm"
occurrence = 1
risk = "server_local"
```

During `prepare`, local module patches materialize into:

```text
.dynamic_modules_build/module_patches/<module-id>/<target_file>
```

The generated module include file points at the materialized copy instead of
the installed module file. This keeps the module checkout clean while making
local server edits reproducible in local builds, TGS builds, and CI.

Local module patches only apply to files that are explicitly matched by the
module's `build.dm_files` or `build.test_files`; otherwise the build fails so
servers do not accidentally create a patch that never compiles.

## BYOND-aware patching direction

Dynamic DM owns maintainer tooling that can infer these text/block patches from
real downstream DM edits and verify that applying them to a base file recreates
the edited file. A later patch engine can build on that and target BYOND types
and procs directly, for example:

```toml
target = "/mob/living/carbon/human/proc/Move"
mode = "insert_before_return"
```

That future parser should produce the same `index.json` shape so the VS Code
extension and `explain` command continue to work.
