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

Each patch needs:

- module id from the owning manifest
- patch id
- target host file
- anchor text
- source patch file
- occurrence number

During `prepare`, patches materialize into `.dynamic_modules_build/patched/`.
The host checkout is not modified.

## Future BYOND-aware patching

The first implementation anchors on text lines. A later patch engine should be
able to target BYOND types and procs directly, for example:

```toml
target = "/mob/living/carbon/human/proc/Move"
mode = "insert_before_return"
```

That future parser should produce the same `index.json` shape so the VS Code
extension and `explain` command continue to work.

