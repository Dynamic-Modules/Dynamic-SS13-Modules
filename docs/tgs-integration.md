# TGS Integration

TGS and CI should run Dynamic Modules as a noninteractive prebuild step.

Recommended command:

```bash
python3 -m dynamic_ss13_modules prepare
```

or, when installed:

```bash
dynamic-modules prepare
```

The command must complete before DreamMaker compiles the DME.

## Host bootstrap include

The host downstream should add one stable include path that points at the
generated module include file:

```dm
#include ".dynamic_modules_build/generated/_dynamic_modules_includes.dm"
```

Unit-test builds can include:

```dm
#include ".dynamic_modules_build/generated/_dynamic_modules_tests.dm"
```

The exact bootstrap location should be chosen per downstream. Keep this as a
small downstream-owned hook so module updates can remain generated output.

## Generated files

`.dynamic_modules_build/` should be ignored by Git. It is safe to delete and
regenerate.
