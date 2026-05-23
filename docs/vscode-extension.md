# VS Code Extension Integration

The VS Code extension now lives in its own repository:

```text
https://github.com/Dynamic-Modules/VS-Code-Extensions
```

The extension reads `.dynamic_modules_build/index.json`. It does not resolve
modules itself, and it should remain a thin UI over framework output. If editor
tooling needs more structured data, add that data to the generated index rather
than duplicating resolver, patch, or manifest logic in JavaScript.

## Generated workspace

The framework still owns workspace generation:

```bash
dynamic-modules workspace-generate
```

This creates `.dynamic_modules_build/dynamic-modules.code-workspace` with the
host repo and all resolved module roots. The VS Code extension can open that
workspace or add individual module roots to the current workspace for smoother
module maintenance.

## Authoring workspaces

The extension also owns maintainer authoring sessions. `Dynamic Modules:
Generate Authoring Workspace` runs `prepare`, copies selected final/materialized
files into `.dynamic_modules_authoring/<session>/files`, and records the
baseline in the same session folder. Maintainers can edit those final files
freely, then run `Dynamic Modules: Deconvert Authoring Workspace` to generate a
new module from the session delta.

Deconversion delegates to the core modules where possible:

- `.dm` files use Dynamic DM patch conversion
- `tgui/` files use Dynamic TGUI's smart conversion
- binary assets are copied as Dynamic Assets contributions

The authoring folder is local scratch state. The extension adds it to
`.git/info/exclude` for host repos when possible; it should not be committed.
