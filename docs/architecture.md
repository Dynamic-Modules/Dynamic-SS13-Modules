# Architecture

Dynamic SS13 Modules is a build-time layer for tgstation-style downstreams.
It intentionally keeps generated files out of the normal Git history.

## Layers

1. Bootstrap CLI

   The `dynamic-modules` command runs before DreamMaker, CI, or TGS compile
   steps. It discovers modules, validates manifests, resolves load order, and
   generates disposable build output.

2. Host config

   A server repo owns `dynamic_modules.toml`. It defines module roots,
   registry allowlists, build output location, config override location, and
   update policy.

3. Module manifests

   Each module owns a `*.module.toml` file. The manifest declares the module
   id, version, source repo, dependencies, load hints, DM files, tests, config,
   hooks, and patches.

4. Lockfile

   `dynamic_modules.lock.json` records exact resolved module commits and
   manifest hashes. Git submodules handle checkout mechanics; the lockfile
   explains the module state in a reviewable way.

5. Generated build layer

   `.dynamic_modules_build/` contains generated include files, config exports,
   patch overlays, prepare-plugin output, and `index.json`. It is disposable
   and should be gitignored.

## Standard flow

```text
scan -> validate -> resolve -> prepare -> compile/test
```

`prepare` emits:

- `.dynamic_modules_build/generated/_dynamic_modules_includes.dm`
- `.dynamic_modules_build/generated/_dynamic_modules_tests.dm`
- `.dynamic_modules_build/generated/dynamic_modules_config.json`
- `.dynamic_modules_build/prepare_plugins/context.json`
- module-owned prepare-plugin output, such as Dynamic TGUI's wrapper
- `.dynamic_modules_build/index.json`
- `.dynamic_modules_build/patched/...` when patches are used

The host repo should have one stable bootstrap include/hook that consumes the
generated include file. That stable hook belongs in the downstream repo, while
module-specific output stays generated.

## Design rules

- Prefer normal DM files, components, signals, and generated hook points.
- Use structured patches only when a module cannot integrate cleanly another
  way.
- Make every generated change explainable by module id, manifest path, source
  commit, and hook or patch id.
- Keep TGS and CI integration noninteractive.
