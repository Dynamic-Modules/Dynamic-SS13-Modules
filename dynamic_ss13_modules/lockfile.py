from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from dynamic_ss13_modules.git.commands import git_commit, git_remote_url
from dynamic_ss13_modules.io import read_json, write_json
from dynamic_ss13_modules.manifest.models import HostConfig, ModuleManifest
from dynamic_ss13_modules.resolver.graph import ResolvedGraph

LOCKFILE_VERSION = 1


def manifest_hash(manifest: ModuleManifest) -> str:
    data = manifest.manifest_path.read_bytes()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def build_lockfile(host: HostConfig, graph: ResolvedGraph) -> dict[str, Any]:
    modules: dict[str, Any] = {}
    for module in graph.ordered_modules():
        commit = git_commit(module.root) or "local-uncommitted"
        repo = module.source.repo or git_remote_url(module.root) or "local"
        modules[module.id] = {
            "name": module.name,
            "version": module.version,
            "module_api": module.module_api,
            "repo": repo,
            "commit": commit,
            "manifest": str(module.manifest_path.relative_to(host.root))
            if _is_relative_to(module.manifest_path, host.root)
            else str(module.manifest_path),
            "manifest_hash": manifest_hash(module),
            "dependencies": [
                edge.before for edge in graph.edges if edge.after == module.id and edge.reason.startswith("requires")
            ],
        }
    return {
        "lockfile_version": LOCKFILE_VERSION,
        "modules": modules,
    }


def read_lockfile(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return read_json(path)


def write_lockfile(host: HostConfig, graph: ResolvedGraph) -> dict[str, Any]:
    data = build_lockfile(host, graph)
    write_json(host.lockfile, data)
    return data


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
