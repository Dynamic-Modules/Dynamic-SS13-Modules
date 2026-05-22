from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from dynamic_ss13_modules.errors import GitError
from dynamic_ss13_modules.git.commands import run_git
from dynamic_ss13_modules.manifest.models import HostConfig
from dynamic_ss13_modules.resolver.graph import ResolvedGraph


@dataclass(frozen=True)
class UpdateCandidate:
    module_id: str
    current: str
    candidate: str
    branch: str
    changed: bool


def find_update_candidates(host: HostConfig, graph: ResolvedGraph) -> list[UpdateCandidate]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=host.update.minimum_commit_age_hours)
    before = cutoff.isoformat(timespec="seconds")
    candidates: list[UpdateCandidate] = []
    for module in graph.ordered_modules():
        if not module.source.repo:
            continue
        branch = module.source.default_branch
        current = run_git(module.root, ["rev-parse", "HEAD"])
        run_git(module.root, ["fetch", "origin", branch])
        candidate = run_git(
            module.root,
            ["rev-list", "--first-parent", "-n", "1", f"--before={before}", f"origin/{branch}"],
        )
        if not candidate:
            raise GitError(f"{module.id}: no update candidate found before {before}")
        candidates.append(
            UpdateCandidate(
                module_id=module.id,
                current=current,
                candidate=candidate,
                branch=branch,
                changed=current != candidate,
            )
        )
    return candidates


def apply_update_candidates(graph: ResolvedGraph, candidates: list[UpdateCandidate]) -> None:
    modules = graph.modules
    for candidate in candidates:
        if not candidate.changed:
            continue
        module = modules[candidate.module_id]
        run_git(module.root, ["checkout", candidate.candidate])


def commit_host_update(host: HostConfig, message: str, push: bool) -> str:
    paths = [_rel(host.root, host.lockfile)]
    paths.extend(_rel(host.root, root) for root in host.module_roots if root.exists())
    run_git(host.root, ["add", *paths])
    commit = run_git(host.root, ["commit", "-m", message])
    if push:
        run_git(host.root, ["push"])
    return commit


def _rel(root, path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)
