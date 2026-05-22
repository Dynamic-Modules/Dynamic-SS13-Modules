from __future__ import annotations

import subprocess
from pathlib import Path

from dynamic_ss13_modules.errors import GitError


def run_git(root: Path, args: list[str], check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if check and completed.returncode != 0:
        raise GitError(
            f"git -C {root} {' '.join(args)} failed:\n{completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def git_commit(root: Path) -> str | None:
    try:
        return run_git(root, ["rev-parse", "HEAD"])
    except GitError:
        return None


def git_remote_url(root: Path) -> str | None:
    try:
        return run_git(root, ["config", "--get", "remote.origin.url"])
    except GitError:
        return None


def git_is_dirty(root: Path) -> bool:
    try:
        return bool(run_git(root, ["status", "--porcelain"]))
    except GitError:
        return False

