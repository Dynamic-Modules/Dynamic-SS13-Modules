from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dynamic_ss13_modules.config import validate_config_schema
from dynamic_ss13_modules.errors import BuildError
from dynamic_ss13_modules.errors import ValidationError as DynamicValidationError
from dynamic_ss13_modules.io import merge_dicts, read_json, read_toml, write_json
from dynamic_ss13_modules.lockfile import build_lockfile, write_lockfile
from dynamic_ss13_modules.manifest.models import HostConfig, ModuleManifest, PatchSpec
from dynamic_ss13_modules.patches.engine import AppliedPatch, apply_patch_text
from dynamic_ss13_modules.paths import include_path
from dynamic_ss13_modules.resolver.graph import ResolvedGraph


@dataclass(frozen=True)
class PrepareResult:
    build_dir: Path
    index_path: Path
    include_path: Path
    tests_path: Path
    config_path: Path
    tgui_cli_path: Path | None
    lockfile_written: bool


@dataclass(frozen=True)
class LocalModulePatch:
    module_id: str
    patch: PatchSpec
    manifest_path: Path


@dataclass(frozen=True)
class AppliedModulePatch:
    module_id: str
    patch_id: str
    target_file: str
    source_file: str
    output_file: str
    mode: str
    anchor: str
    anchor_line: int
    occurrence: int
    risk: str


def prepare_build(host: HostConfig, graph: ResolvedGraph, write_lock: bool = True) -> PrepareResult:
    build_dir = host.build.build_dir
    _assert_safe_build_dir(host.root, build_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    generated_dir = build_dir / "generated"
    patched_dir = build_dir / "patched"
    module_patched_dir = build_dir / "module_patches"
    generated_dir.mkdir(parents=True, exist_ok=True)

    patch_output_dir = patched_dir
    if host.build.materialize_mode == "full-copy":
        patch_output_dir = build_dir / "worktree"
        _copy_host_to_worktree(host.root, patch_output_dir, build_dir.name)

    include_file = generated_dir / "_dynamic_modules_includes.dm"
    tests_file = generated_dir / "_dynamic_modules_tests.dm"
    config_file = generated_dir / "dynamic_modules_config.json"
    tgui_cli_file = _write_tgui_cli_wrapper(host, graph, build_dir / "tgui" / "cli.ts")

    dm_files = _collect_files(graph, "dm")
    test_files = _collect_files(graph, "tests")
    tgui_files = _collect_files(graph, "tgui")
    included_module_sources = {path.resolve() for _module, path in dm_files + test_files}
    applied_module_patches, module_patch_outputs = _apply_local_module_patches(
        host,
        graph,
        module_patched_dir,
        included_module_sources,
    )
    dm_files = _rewrite_module_file_outputs(dm_files, module_patch_outputs)
    test_files = _rewrite_module_file_outputs(test_files, module_patch_outputs)
    _write_include_file(include_file, dm_files, "Dynamic SS13 module source includes")
    _write_include_file(tests_file, test_files, "Dynamic SS13 module unit-test includes")
    write_json(config_file, _collect_config(host, graph))

    applied_patches = _apply_patches(host, graph, patch_output_dir)
    index = _build_index(
        host=host,
        graph=graph,
        dm_files=dm_files,
        test_files=test_files,
        tgui_files=tgui_files,
        applied_patches=applied_patches,
        applied_module_patches=applied_module_patches,
        include_file=include_file,
        tests_file=tests_file,
        config_file=config_file,
        tgui_cli_file=tgui_cli_file,
    )
    index_path = build_dir / "index.json"
    write_json(index_path, index)

    lockfile_written = False
    if write_lock:
        write_lockfile(host, graph)
        lockfile_written = True

    return PrepareResult(
        build_dir=build_dir,
        index_path=index_path,
        include_path=include_file,
        tests_path=tests_file,
        config_path=config_file,
        tgui_cli_path=tgui_cli_file,
        lockfile_written=lockfile_written,
    )


def _assert_safe_build_dir(host_root: Path, build_dir: Path) -> None:
    root = host_root.resolve()
    build_dir = build_dir.resolve()
    try:
        build_dir.relative_to(root)
    except ValueError as exc:
        raise BuildError(f"build dir must be inside host root: {build_dir}") from exc
    if build_dir == root:
        raise BuildError("build dir cannot be the host root")
    if build_dir.name in {"", ".", ".."}:
        raise BuildError(f"unsafe build dir: {build_dir}")


def _copy_host_to_worktree(host_root: Path, worktree: Path, build_dir_name: str) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored = {".git", build_dir_name, "node_modules", ".pytest_cache", "__pycache__"}
        return {name for name in names if name in ignored}

    shutil.copytree(host_root, worktree, ignore=ignore)


def _collect_files(graph: ResolvedGraph, kind: str) -> list[tuple[ModuleManifest, Path]]:
    collected: list[tuple[ModuleManifest, Path]] = []
    for module in graph.ordered_modules():
        if kind == "dm":
            patterns = module.build.dm_files
        elif kind == "tests":
            patterns = module.build.test_files
        elif kind == "tgui":
            patterns = module.build.tgui
        else:
            raise BuildError(f"unknown build file kind: {kind}")
        for pattern in patterns:
            for path in sorted(module.root.glob(pattern)):
                if path.is_file():
                    collected.append((module, path.resolve()))
    return collected


def _write_tgui_cli_wrapper(host: HostConfig, graph: ResolvedGraph, path: Path) -> Path | None:
    module = graph.modules.get("dynamic-tgui")
    if module is None:
        return None

    cli_path = module.root / "tools" / "cli.ts"
    if not cli_path.exists():
        raise BuildError(f"dynamic-tgui: missing tools/cli.ts")

    path.parent.mkdir(parents=True, exist_ok=True)
    module_cli_import = include_path(path, cli_path)
    lines = [
        "#!/usr/bin/env bun",
        "// Generated by Dynamic SS13 Modules. Do not edit.",
        f"process.env.DYNAMIC_MODULES_HOST_ROOT ??= {str(host.root)!r};",
        f"process.env.DYNAMIC_MODULES_INDEX ??= {str(host.build.build_dir / 'index.json')!r};",
        f"await import({module_cli_import!r});",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return path


def _rewrite_module_file_outputs(
    files: list[tuple[ModuleManifest, Path]],
    module_patch_outputs: dict[Path, Path],
) -> list[tuple[ModuleManifest, Path]]:
    return [(module, module_patch_outputs.get(path.resolve(), path)) for module, path in files]


def _write_include_file(path: Path, files: list[tuple[ModuleManifest, Path]], title: str) -> None:
    lines = [
        f"// {title}",
        "// Generated by Dynamic SS13 Modules. Do not edit.",
        "",
    ]
    for module, file_path in files:
        lines.append(f"// {module.id}")
        lines.append(f'#include "{include_path(path, file_path)}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def _collect_config(host: HostConfig, graph: ResolvedGraph) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for module in graph.ordered_modules():
        data: dict[str, Any] = {}
        if module.config.defaults:
            defaults_path = module.root / module.config.defaults
            if defaults_path.exists():
                data = read_toml(defaults_path)
            else:
                raise BuildError(f"{module.id}: config defaults file missing: {module.config.defaults}")
        override_path = host.config_dir / f"{module.id}.toml"
        if override_path.exists():
            data = merge_dicts(data, read_toml(override_path))
        if module.config.schema:
            schema_path = module.root / module.config.schema
            if not schema_path.exists():
                raise BuildError(f"{module.id}: config schema file missing: {module.config.schema}")
            try:
                validate_config_schema(data, read_json(schema_path), module.id)
            except DynamicValidationError as exc:
                raise BuildError(f"{module.id}: config failed schema validation: {exc}") from exc
        result[module.id] = {
            "config_version": module.config.version,
            "values": data,
        }
    return result


def _load_local_module_patches(host: HostConfig) -> list[LocalModulePatch]:
    patch_root = host.config_dir / "patches"
    if not patch_root.exists():
        return []
    if not patch_root.is_dir():
        raise BuildError(f"local module patch path is not a directory: {patch_root}")

    local_patches: list[LocalModulePatch] = []
    for manifest_path in sorted(patch_root.rglob("*.toml")):
        data = read_toml(manifest_path)
        patches_raw = data.get("patches", [])
        if not isinstance(patches_raw, list):
            raise BuildError(f"{manifest_path}: patches must be an array of tables")
        for raw_patch in patches_raw:
            if not isinstance(raw_patch, dict):
                raise BuildError(f"{manifest_path}: patches entries must be tables")
            module_id = raw_patch.get("module")
            if not isinstance(module_id, str) or not module_id.strip():
                raise BuildError(f"{manifest_path}: patch.module must be a non-empty string")
            local_patches.append(
                LocalModulePatch(
                    module_id=module_id,
                    patch=PatchSpec.from_raw(raw_patch, manifest_path),
                    manifest_path=manifest_path,
                )
            )
    return local_patches


def _apply_local_module_patches(
    host: HostConfig,
    graph: ResolvedGraph,
    module_patched_dir: Path,
    included_module_sources: set[Path],
) -> tuple[list[AppliedModulePatch], dict[Path, Path]]:
    local_patches = _load_local_module_patches(host)
    if not local_patches:
        return [], {}

    patches_by_module: dict[str, list[LocalModulePatch]] = {}
    for local_patch in local_patches:
        if local_patch.module_id not in graph.modules:
            raise BuildError(
                f"{local_patch.manifest_path}: local patch {local_patch.patch.id} "
                f"targets unknown module {local_patch.module_id!r}"
            )
        patches_by_module.setdefault(local_patch.module_id, []).append(local_patch)

    applied: list[AppliedModulePatch] = []
    outputs_by_source: dict[Path, Path] = {}
    buffers: dict[Path, str] = {}
    host_root = host.root.resolve()
    config_root = host.config_dir.resolve()

    for module in graph.ordered_modules():
        module_root = module.root.resolve()
        for local_patch in patches_by_module.get(module.id, []):
            patch = local_patch.patch
            source_path = (module.root / patch.target_file).resolve()
            patch_path = (local_patch.manifest_path.parent / patch.file).resolve()

            if not source_path.exists():
                raise BuildError(
                    f"{module.id}:{patch.id}: target module file does not exist: {patch.target_file}"
                )
            if source_path not in included_module_sources:
                raise BuildError(
                    f"{module.id}:{patch.id}: target module file is not included by build.dm_files "
                    f"or build.test_files: {patch.target_file}"
                )
            if not patch_path.exists():
                raise BuildError(
                    f"{local_patch.manifest_path}: patch file does not exist: {patch.file}"
                )
            try:
                source_path.relative_to(module_root)
            except ValueError as exc:
                raise BuildError(f"{module.id}:{patch.id}: target escapes module root") from exc
            try:
                patch_path.relative_to(config_root)
            except ValueError as exc:
                raise BuildError(f"{module.id}:{patch.id}: patch file escapes config dir") from exc

            if source_path not in buffers:
                buffers[source_path] = source_path.read_text(encoding="utf-8")
            content = patch_path.read_text(encoding="utf-8")
            patched, anchor_line = apply_patch_text(buffers[source_path], patch, content)
            buffers[source_path] = patched

            output_path = module_patched_dir / module.id / patch.target_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(patched, encoding="utf-8", newline="\n")
            outputs_by_source[source_path] = output_path

            source_file = _path_for_index(host_root, source_path)
            applied.append(
                AppliedModulePatch(
                    module_id=module.id,
                    patch_id=patch.id,
                    target_file=patch.target_file,
                    source_file=source_file,
                    output_file=str(output_path.relative_to(host.build.build_dir)),
                    mode=patch.mode,
                    anchor=patch.anchor,
                    anchor_line=anchor_line,
                    occurrence=patch.occurrence,
                    risk=patch.risk,
                )
            )

    return applied, outputs_by_source


def _apply_patches(host: HostConfig, graph: ResolvedGraph, patched_dir: Path) -> list[AppliedPatch]:
    applied: list[AppliedPatch] = []
    buffers: dict[str, str] = {}
    for module in graph.ordered_modules():
        for patch in module.patches:
            source_path = (host.root / patch.target_file).resolve()
            patch_path = (module.root / patch.file).resolve()
            if not source_path.exists():
                raise BuildError(f"{module.id}:{patch.id}: target file does not exist: {patch.target_file}")
            if not patch_path.exists():
                raise BuildError(f"{module.id}:{patch.id}: patch file does not exist: {patch.file}")
            try:
                source_path.relative_to(host.root.resolve())
            except ValueError as exc:
                raise BuildError(f"{module.id}:{patch.id}: target escapes host root") from exc
            try:
                patch_path.relative_to(module.root.resolve())
            except ValueError as exc:
                raise BuildError(f"{module.id}:{patch.id}: patch file escapes module root") from exc

            if patch.target_file not in buffers:
                buffers[patch.target_file] = source_path.read_text(encoding="utf-8")
            content = patch_path.read_text(encoding="utf-8")
            patched, anchor_line = apply_patch_text(buffers[patch.target_file], patch, content)
            buffers[patch.target_file] = patched

            output_path = patched_dir / patch.target_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(patched, encoding="utf-8", newline="\n")
            applied.append(
                AppliedPatch(
                    module_id=module.id,
                    patch_id=patch.id,
                    target_file=patch.target_file,
                    output_file=str(output_path.relative_to(patched_dir.parent)),
                    mode=patch.mode,
                    anchor=patch.anchor,
                    anchor_line=anchor_line,
                    occurrence=patch.occurrence,
                    risk=patch.risk,
                )
            )
    return applied


def _build_index(
    host: HostConfig,
    graph: ResolvedGraph,
    dm_files: list[tuple[ModuleManifest, Path]],
    test_files: list[tuple[ModuleManifest, Path]],
    tgui_files: list[tuple[ModuleManifest, Path]],
    applied_patches: list[AppliedPatch],
    applied_module_patches: list[AppliedModulePatch],
    include_file: Path,
    tests_file: Path,
    config_file: Path,
    tgui_cli_file: Path | None,
) -> dict[str, Any]:
    files: dict[str, list[dict[str, Any]]] = {}

    for module in graph.ordered_modules():
        for hook in module.hooks:
            if hook.target_file:
                files.setdefault(hook.target_file, []).append(
                    {
                        "kind": "hook",
                        "module": module.id,
                        "id": hook.id,
                        "target": hook.target,
                        "mode": hook.mode,
                        "source_file": hook.file,
                        "description": hook.description,
                    }
                )

    for patch in applied_module_patches:
        files.setdefault(patch.source_file, []).append(
            {
                "kind": "module_patch",
                "module": patch.module_id,
                "id": patch.patch_id,
                "target_file": patch.target_file,
                "mode": patch.mode,
                "anchor": patch.anchor,
                "anchor_line": patch.anchor_line,
                "output_file": patch.output_file,
                "risk": patch.risk,
            }
        )

    for patch in applied_patches:
        files.setdefault(patch.target_file, []).append(
            {
                "kind": "patch",
                "module": patch.module_id,
                "id": patch.patch_id,
                "mode": patch.mode,
                "anchor": patch.anchor,
                "anchor_line": patch.anchor_line,
                "output_file": patch.output_file,
                "risk": patch.risk,
            }
        )

    module_entries: dict[str, Any] = {}
    for module in graph.ordered_modules():
        module_entries[module.id] = {
            "name": module.name,
            "version": module.version,
            "module_api": module.module_api,
            "root": _path_for_index(host.root, module.root),
            "manifest": _path_for_index(host.root, module.manifest_path),
            "source": {
                "repo": module.source.repo,
                "default_branch": module.source.default_branch,
            },
            "dm_files": [_path_for_index(host.root, path) for mod, path in dm_files if mod.id == module.id],
            "test_files": [_path_for_index(host.root, path) for mod, path in test_files if mod.id == module.id],
            "tgui_files": [_path_for_index(host.root, path) for mod, path in tgui_files if mod.id == module.id],
            "hooks": [hook.__dict__ for hook in module.hooks],
            "patches": [patch.__dict__ for patch in module.patches],
            "local_module_patches": [
                patch.__dict__ for patch in applied_module_patches if patch.module_id == module.id
            ],
        }

    return {
        "index_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host_root": str(host.root),
        "host_config": str(host.path),
        "build_dir": _path_for_index(host.root, host.build.build_dir),
        "target_dme": host.build.target_dme,
        "materialize_mode": host.build.materialize_mode,
        "generated": {
            "include_file": _path_for_index(host.root, include_file),
            "tests_file": _path_for_index(host.root, tests_file),
            "config_file": _path_for_index(host.root, config_file),
            "tgui_cli_file": _path_for_index(host.root, tgui_cli_file) if tgui_cli_file else None,
        },
        "load_order": graph.load_order,
        "edges": [edge.__dict__ for edge in graph.edges],
        "warnings": graph.warnings,
        "modules": module_entries,
        "files": files,
        "lockfile_preview": build_lockfile(host, graph),
    }


def _path_for_index(host_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(host_root.resolve()).as_posix()
    except ValueError:
        return str(path)
