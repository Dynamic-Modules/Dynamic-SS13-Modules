# VS Code Extension

The VS Code extension reads `.dynamic_modules_build/index.json`. It does not
resolve modules itself.

Planned and scaffolded features:

- Activity Bar view for enabled modules
- refresh command
- explain current file command
- open generated index command
- CodeLens banner when a host file has module interactions
- hover details for files touched by hooks or patches

The extension should remain a thin UI over CLI output. If a detail is missing,
add it to `index.json` rather than duplicating resolver logic in JavaScript.

## Multi-root module editing

A future command should generate a `.code-workspace` containing the host repo
and every installed module root. That gives maintainers smooth editing without
opening twenty separate VS Code windows.

