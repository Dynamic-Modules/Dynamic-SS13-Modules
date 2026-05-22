# Maintainer Workflows

## Install a module

The intended production path is Git submodules plus a lockfile:

```bash
git submodule add https://github.com/example/trip-system.git dynamic_modules/installed/trip-system
dynamic-modules resolve --write-lock
dynamic-modules prepare
```

## Explain a file

```bash
dynamic-modules prepare
dynamic-modules explain code/modules/mob/living/carbon/human/human_movement.dm
```

This reports hooks and patches that interact with the host file.

Preview a patched overlay:

```bash
dynamic-modules preview-file code/modules/mob/living/carbon/human/human_movement.dm
dynamic-modules preview-file code/modules/mob/living/carbon/human/human_movement.dm --contents
```

List all structured patches:

```bash
dynamic-modules patch-report
```

## Diagnose the host

```bash
dynamic-modules doctor
```

`doctor` checks discovery, validation, dependency resolution, lockfile presence,
and generated build output presence.

## Update modules

Dry run:

```bash
dynamic-modules update
```

Apply and regenerate:

```bash
dynamic-modules update --apply
```

Commit and push are intentionally explicit:

```bash
dynamic-modules update --apply --commit --push
```

Host config must set `update.direct_push = true` before `--push` is allowed.

## Generate a VS Code workspace

```bash
dynamic-modules workspace-generate
```

This creates `.dynamic_modules_build/dynamic-modules.code-workspace` with the
host repo and all resolved module roots.
