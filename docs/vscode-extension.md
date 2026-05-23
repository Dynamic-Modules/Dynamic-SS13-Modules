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
