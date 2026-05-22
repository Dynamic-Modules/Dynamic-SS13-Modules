from __future__ import annotations

import os
from pathlib import Path


def normalize_rel(path: str | Path) -> str:
    return Path(path).as_posix()


def rel_to(base: Path, target: Path) -> str:
    return Path(target).resolve().relative_to(base.resolve()).as_posix()


def safe_resolve_under(root: Path, value: str | Path) -> Path:
    root = root.resolve()
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{candidate} escapes {root}") from exc
    return candidate


def include_path(from_file: Path, target: Path) -> str:
    base = Path(from_file).resolve().parent
    return Path(os.path.relpath(Path(target).resolve(), base)).as_posix()
