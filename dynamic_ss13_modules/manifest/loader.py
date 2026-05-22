from __future__ import annotations

from pathlib import Path
from typing import Any

from dynamic_ss13_modules.errors import ValidationError
from dynamic_ss13_modules.io import read_toml
from dynamic_ss13_modules.manifest.models import (
    HostBuildSpec,
    HostConfig,
    ModuleManifest,
    RegistrySpec,
    UpdatePolicy,
)


DEFAULT_HOST_CONFIG = "dynamic_modules.toml"


def load_host_config(root: Path, config_path: Path | None = None) -> HostConfig:
    root = root.resolve()
    path = (config_path or root / DEFAULT_HOST_CONFIG).resolve()
    raw: dict[str, Any] = {}
    if path.exists():
        raw = read_toml(path)

    module_roots_raw = raw.get("module_roots", ["dynamic_modules"])
    if not isinstance(module_roots_raw, list) or not all(
        isinstance(item, str) for item in module_roots_raw
    ):
        raise ValidationError(f"{path}: module_roots must be a list of strings")

    config_dir_raw = raw.get("config_dir", "config/dynamic_modules")
    lockfile_raw = raw.get("lockfile", "dynamic_modules.lock.json")
    if not isinstance(config_dir_raw, str):
        raise ValidationError(f"{path}: config_dir must be a string")
    if not isinstance(lockfile_raw, str):
        raise ValidationError(f"{path}: lockfile must be a string")

    build_raw = raw.get("build", {})
    if not isinstance(build_raw, dict):
        raise ValidationError(f"{path}: build must be a table")
    build_dir_raw = build_raw.get("dir", ".dynamic_modules_build")
    target_dme = build_raw.get("target_dme")
    materialize_mode = build_raw.get("materialize_mode", "overlay")
    if not isinstance(build_dir_raw, str):
        raise ValidationError(f"{path}: build.dir must be a string")
    if target_dme is not None and not isinstance(target_dme, str):
        raise ValidationError(f"{path}: build.target_dme must be a string")
    if materialize_mode not in {"overlay", "full-copy"}:
        raise ValidationError(f"{path}: build.materialize_mode must be overlay or full-copy")

    registries = _load_registries(raw.get("registries", []), path)
    update = _load_update(raw.get("update", {}), path)

    return HostConfig(
        root=root,
        path=path,
        module_roots=[(root / item).resolve() for item in module_roots_raw],
        config_dir=(root / config_dir_raw).resolve(),
        lockfile=(root / lockfile_raw).resolve(),
        registries=registries,
        update=update,
        build=HostBuildSpec(
            build_dir=(root / build_dir_raw).resolve(),
            target_dme=target_dme,
            materialize_mode=materialize_mode,
        ),
    )


def _load_registries(raw: Any, path: Path) -> list[RegistrySpec]:
    if not isinstance(raw, list):
        raise ValidationError(f"{path}: registries must be an array of tables")
    result: list[RegistrySpec] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValidationError(f"{path}: each registry must be a table")
        name = item.get("name")
        url = item.get("url")
        local_path = item.get("path")
        trusted = item.get("trusted", False)
        if not isinstance(name, str) or not name:
            raise ValidationError(f"{path}: registry.name must be a non-empty string")
        if url is not None and not isinstance(url, str):
            raise ValidationError(f"{path}: registry.url must be a string")
        if local_path is not None and not isinstance(local_path, str):
            raise ValidationError(f"{path}: registry.path must be a string")
        if not isinstance(trusted, bool):
            raise ValidationError(f"{path}: registry.trusted must be a boolean")
        result.append(RegistrySpec(name=name, url=url, path=local_path, trusted=trusted))
    return result


def _load_update(raw: Any, path: Path) -> UpdatePolicy:
    if not isinstance(raw, dict):
        raise ValidationError(f"{path}: update must be a table")
    minimum_age = raw.get("minimum_commit_age_hours", 24)
    direct_push = raw.get("direct_push", False)
    branch = raw.get("branch")
    commit_message = raw.get("commit_message", "Update Dynamic SS13 modules")
    if not isinstance(minimum_age, int) or minimum_age < 0:
        raise ValidationError(f"{path}: update.minimum_commit_age_hours must be a non-negative integer")
    if not isinstance(direct_push, bool):
        raise ValidationError(f"{path}: update.direct_push must be a boolean")
    if branch is not None and not isinstance(branch, str):
        raise ValidationError(f"{path}: update.branch must be a string")
    if not isinstance(commit_message, str):
        raise ValidationError(f"{path}: update.commit_message must be a string")
    return UpdatePolicy(
        minimum_commit_age_hours=minimum_age,
        direct_push=direct_push,
        branch=branch,
        commit_message=commit_message,
    )


def discover_manifest_paths(host: HostConfig) -> list[Path]:
    paths: list[Path] = []
    for root in host.module_roots:
        if not root.exists():
            continue
        paths.extend(sorted(root.rglob("*.module.toml")))
    return sorted(paths)


def load_manifest(path: Path) -> ModuleManifest:
    raw = read_toml(path)
    return ModuleManifest.from_raw(raw, path.resolve(), path.resolve().parent)


def discover_manifests(host: HostConfig) -> list[ModuleManifest]:
    return [load_manifest(path) for path in discover_manifest_paths(host)]

