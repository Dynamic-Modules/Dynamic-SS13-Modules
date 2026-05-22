from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dynamic_ss13_modules.errors import DynamicModulesError, GitError
from dynamic_ss13_modules.git.commands import run_git
from dynamic_ss13_modules.manifest.models import HostConfig
from dynamic_ss13_modules.registry import load_registries
from dynamic_ss13_modules.resolver.graph import ResolvedGraph


@dataclass(frozen=True)
class ModuleSource:
    module_id: str
    repo: str
    branch: str | None = None
    commit: str | None = None
    registry: str | None = None


def source_from_registry(host: HostConfig, module_id: str) -> ModuleSource:
    registries = load_registries(host)
    for registry_name, registry in registries.items():
        modules = registry.get("modules", {})
        if not isinstance(modules, dict):
            continue
        entry = modules.get(module_id)
        if not isinstance(entry, dict):
            continue
        repo = entry.get("repo")
        if not isinstance(repo, str) or not repo:
            raise DynamicModulesError(f"registry {registry_name} entry {module_id} has no repo")
        branch = _optional_string(entry, "branch") or _optional_string(entry, "default_branch")
        commit = _optional_string(entry, "commit")
        return ModuleSource(
            module_id=module_id,
            repo=repo,
            branch=branch,
            commit=commit,
            registry=registry_name,
        )
    raise DynamicModulesError(f"module {module_id} was not found in trusted registries")


def install_module(
    host: HostConfig,
    module_id: str,
    repo: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    path: str | None = None,
) -> Path:
    source = (
        ModuleSource(module_id=module_id, repo=repo, branch=branch, commit=commit)
        if repo
        else source_from_registry(host, module_id)
    )
    if branch:
        source = ModuleSource(module_id, source.repo, branch, source.commit, source.registry)
    if commit:
        source = ModuleSource(module_id, source.repo, source.branch, commit, source.registry)

    install_path = _install_path(host, module_id, path)
    if install_path.exists():
        raise DynamicModulesError(f"module destination already exists: {install_path}")
    install_path.parent.mkdir(parents=True, exist_ok=True)

    args = ["-c", "protocol.file.allow=always", "submodule", "add"]
    if source.branch:
        args.extend(["-b", source.branch])
    args.extend([source.repo, _rel(host.root, install_path)])
    run_git(host.root, args)
    if source.commit:
        run_git(install_path, ["checkout", source.commit])
        run_git(host.root, ["add", _rel(host.root, install_path)])
    return install_path


def remove_module(host: HostConfig, graph: ResolvedGraph, module_id: str, path: str | None = None) -> Path:
    module_path = (host.root / path).resolve() if path else _path_for_installed_module(host, graph, module_id)
    if not module_path.exists():
        raise DynamicModulesError(f"module path does not exist: {module_path}")
    rel_path = _rel(host.root, module_path)

    try:
        run_git(host.root, ["submodule", "deinit", "-f", "--", rel_path])
    except GitError:
        pass

    try:
        run_git(host.root, ["rm", "-f", "--", rel_path])
    except GitError:
        shutil.rmtree(module_path, ignore_errors=True)
        run_git(host.root, ["add", "-u", "--", rel_path])

    git_module_path = host.root / ".git" / "modules" / rel_path
    shutil.rmtree(git_module_path, ignore_errors=True)
    return module_path


def _install_path(host: HostConfig, module_id: str, path: str | None) -> Path:
    if path:
        return (host.root / path).resolve()
    return (_default_install_root(host) / module_id).resolve()


def _default_install_root(host: HostConfig) -> Path:
    for root in host.module_roots:
        if root.name == "installed":
            return root
    for root in host.module_roots:
        if root.name == "dynamic_modules":
            return root / "installed"
    return host.module_roots[0] if host.module_roots else host.root / "dynamic_modules" / "installed"


def _path_for_installed_module(host: HostConfig, graph: ResolvedGraph, module_id: str) -> Path:
    module = graph.modules.get(module_id)
    if module:
        return module.root.resolve()
    return (_default_install_root(host) / module_id).resolve()


def _optional_string(entry: dict[str, Any], key: str) -> str | None:
    value = entry.get(key)
    return value if isinstance(value, str) and value else None


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)
