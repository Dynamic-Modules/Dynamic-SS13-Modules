from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dynamic_ss13_modules.errors import ValidationError


def _string_list(raw: Any, field_name: str, path: Path) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValidationError(f"{path}: {field_name} must be a list of strings")
    return list(raw)


def _table(raw: Any, field_name: str, path: Path) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValidationError(f"{path}: {field_name} must be a table")
    return raw


@dataclass(frozen=True)
class SourceSpec:
    repo: str | None = None
    default_branch: str = "main"

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "SourceSpec":
        repo = raw.get("repo")
        if repo is not None and not isinstance(repo, str):
            raise ValidationError("source.repo must be a string")
        branch = raw.get("default_branch", "main")
        if not isinstance(branch, str):
            raise ValidationError("source.default_branch must be a string")
        return cls(repo=repo, default_branch=branch)


@dataclass(frozen=True)
class CompatSpec:
    target: str = "tgstation"
    minimum_dynamic_modules: str | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "CompatSpec":
        target = raw.get("target", "tgstation")
        minimum = raw.get("minimum_dynamic_modules")
        if not isinstance(target, str):
            raise ValidationError("compat.target must be a string")
        if minimum is not None and not isinstance(minimum, str):
            raise ValidationError("compat.minimum_dynamic_modules must be a string")
        return cls(target=target, minimum_dynamic_modules=minimum)


@dataclass(frozen=True)
class LoadSpec:
    requires: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    load_after: list[str] = field(default_factory=list)
    load_before: list[str] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], path: Path) -> "LoadSpec":
        return cls(
            requires=_string_list(raw.get("requires"), "load.requires", path),
            optional=_string_list(raw.get("optional"), "load.optional", path),
            conflicts=_string_list(raw.get("conflicts"), "load.conflicts", path),
            load_after=_string_list(raw.get("load_after"), "load.load_after", path),
            load_before=_string_list(raw.get("load_before"), "load.load_before", path),
        )


@dataclass(frozen=True)
class BuildSpec:
    dm_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    tgui: list[str] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: dict[str, Any], path: Path) -> "BuildSpec":
        return cls(
            dm_files=_string_list(raw.get("dm_files"), "build.dm_files", path),
            test_files=_string_list(raw.get("test_files"), "build.test_files", path),
            assets=_string_list(raw.get("assets"), "build.assets", path),
            tgui=_string_list(raw.get("tgui"), "build.tgui", path),
        )


@dataclass(frozen=True)
class PreparePluginSpec:
    id: str
    command: str
    args: list[str] = field(default_factory=list)
    description: str | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any], path: Path) -> "PreparePluginSpec":
        if not isinstance(raw, dict):
            raise ValidationError(f"{path}: prepare_plugins entries must be tables")
        for key in ("id", "command"):
            if not isinstance(raw.get(key), str) or not raw[key].strip():
                raise ValidationError(f"{path}: prepare_plugin.{key} must be a non-empty string")
        args = _string_list(raw.get("args"), "prepare_plugin.args", path)
        description = raw.get("description")
        if description is not None and not isinstance(description, str):
            raise ValidationError(f"{path}: prepare_plugin.description must be a string")
        return cls(
            id=raw["id"],
            command=raw["command"],
            args=args,
            description=description,
        )


@dataclass(frozen=True)
class ConfigSpec:
    schema: str | None = None
    defaults: str | None = None
    version: int = 1

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "ConfigSpec":
        schema = raw.get("schema")
        defaults = raw.get("defaults")
        version = raw.get("version", 1)
        if schema is not None and not isinstance(schema, str):
            raise ValidationError("config.schema must be a string")
        if defaults is not None and not isinstance(defaults, str):
            raise ValidationError("config.defaults must be a string")
        if not isinstance(version, int):
            raise ValidationError("config.version must be an integer")
        return cls(schema=schema, defaults=defaults, version=version)


@dataclass(frozen=True)
class HookSpec:
    id: str
    target: str
    mode: str
    file: str | None = None
    target_file: str | None = None
    description: str | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any], path: Path) -> "HookSpec":
        for key in ("id", "target", "mode"):
            if not isinstance(raw.get(key), str):
                raise ValidationError(f"{path}: hook.{key} must be a string")
        file = raw.get("file")
        target_file = raw.get("target_file")
        description = raw.get("description")
        if file is not None and not isinstance(file, str):
            raise ValidationError(f"{path}: hook.file must be a string")
        if target_file is not None and not isinstance(target_file, str):
            raise ValidationError(f"{path}: hook.target_file must be a string")
        if description is not None and not isinstance(description, str):
            raise ValidationError(f"{path}: hook.description must be a string")
        return cls(
            id=raw["id"],
            target=raw["target"],
            mode=raw["mode"],
            file=file,
            target_file=target_file,
            description=description,
        )


@dataclass(frozen=True)
class PatchSpec:
    id: str
    target_file: str
    mode: str
    anchor: str
    file: str
    end_anchor: str | None = None
    occurrence: int = 1
    risk: str = "escape_hatch"
    description: str | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any], path: Path) -> "PatchSpec":
        for key in ("id", "target_file", "mode", "anchor", "file"):
            if not isinstance(raw.get(key), str):
                raise ValidationError(f"{path}: patch.{key} must be a string")
        occurrence = raw.get("occurrence", 1)
        if not isinstance(occurrence, int) or occurrence < 1:
            raise ValidationError(f"{path}: patch.occurrence must be a positive integer")
        risk = raw.get("risk", "escape_hatch")
        if not isinstance(risk, str):
            raise ValidationError(f"{path}: patch.risk must be a string")
        description = raw.get("description")
        if description is not None and not isinstance(description, str):
            raise ValidationError(f"{path}: patch.description must be a string")
        end_anchor = raw.get("end_anchor")
        if end_anchor is not None and not isinstance(end_anchor, str):
            raise ValidationError(f"{path}: patch.end_anchor must be a string")
        mode = raw["mode"]
        if mode not in {"insert_before", "insert_after", "replace", "replace_between"}:
            raise ValidationError(
                f"{path}: patch.mode must be insert_before, insert_after, replace, "
                "or replace_between"
            )
        if mode == "replace_between" and not end_anchor:
            raise ValidationError(f"{path}: patch.end_anchor is required for replace_between")
        return cls(
            id=raw["id"],
            target_file=raw["target_file"],
            mode=mode,
            anchor=raw["anchor"],
            file=raw["file"],
            end_anchor=end_anchor,
            occurrence=occurrence,
            risk=risk,
            description=description,
        )


@dataclass(frozen=True)
class ModuleManifest:
    id: str
    name: str
    version: str
    module_api: str
    description: str
    root: Path
    manifest_path: Path
    source: SourceSpec
    compat: CompatSpec
    load: LoadSpec
    build: BuildSpec
    config: ConfigSpec
    prepare_plugins: list[PreparePluginSpec]
    hooks: list[HookSpec]
    patches: list[PatchSpec]
    raw: dict[str, Any]

    @classmethod
    def from_raw(
        cls, raw: dict[str, Any], manifest_path: Path, root: Path
    ) -> "ModuleManifest":
        for key in ("id", "name", "version", "module_api"):
            if not isinstance(raw.get(key), str) or not raw[key].strip():
                raise ValidationError(f"{manifest_path}: {key} must be a non-empty string")
        description = raw.get("description", "")
        if not isinstance(description, str):
            raise ValidationError(f"{manifest_path}: description must be a string")
        source = SourceSpec.from_raw(_table(raw.get("source"), "source", manifest_path))
        compat = CompatSpec.from_raw(_table(raw.get("compat"), "compat", manifest_path))
        load = LoadSpec.from_raw(_table(raw.get("load"), "load", manifest_path), manifest_path)
        build = BuildSpec.from_raw(_table(raw.get("build"), "build", manifest_path), manifest_path)
        config = ConfigSpec.from_raw(_table(raw.get("config"), "config", manifest_path))
        prepare_plugins_raw = raw.get("prepare_plugins", [])
        hooks_raw = raw.get("hooks", [])
        patches_raw = raw.get("patches", [])
        if not isinstance(prepare_plugins_raw, list):
            raise ValidationError(f"{manifest_path}: prepare_plugins must be an array of tables")
        if not isinstance(hooks_raw, list):
            raise ValidationError(f"{manifest_path}: hooks must be an array of tables")
        if not isinstance(patches_raw, list):
            raise ValidationError(f"{manifest_path}: patches must be an array of tables")
        prepare_plugins = [
            PreparePluginSpec.from_raw(item, manifest_path) for item in prepare_plugins_raw
        ]
        hooks = [HookSpec.from_raw(item, manifest_path) for item in hooks_raw]
        patches = [PatchSpec.from_raw(item, manifest_path) for item in patches_raw]
        return cls(
            id=raw["id"],
            name=raw["name"],
            version=raw["version"],
            module_api=raw["module_api"],
            description=description,
            root=root,
            manifest_path=manifest_path,
            source=source,
            compat=compat,
            load=load,
            build=build,
            config=config,
            prepare_plugins=prepare_plugins,
            hooks=hooks,
            patches=patches,
            raw=raw,
        )


@dataclass(frozen=True)
class RegistrySpec:
    name: str
    url: str | None = None
    path: str | None = None
    trusted: bool = False


@dataclass(frozen=True)
class UpdatePolicy:
    minimum_commit_age_hours: int = 24
    direct_push: bool = False
    branch: str | None = None
    commit_message: str = "Update Dynamic SS13 modules"


@dataclass(frozen=True)
class HostBuildSpec:
    build_dir: Path
    target_dme: str | None = None
    materialize_mode: str = "overlay"


@dataclass(frozen=True)
class HostConfig:
    root: Path
    path: Path
    module_roots: list[Path]
    config_dir: Path
    lockfile: Path
    registries: list[RegistrySpec]
    update: UpdatePolicy
    build: HostBuildSpec
