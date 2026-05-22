from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dynamic_ss13_modules.errors import BuildError
from dynamic_ss13_modules.manifest.models import ModuleManifest, PatchSpec


@dataclass(frozen=True)
class AppliedPatch:
    module_id: str
    patch_id: str
    target_file: str
    output_file: str
    mode: str
    anchor: str
    anchor_line: int
    occurrence: int
    risk: str


def apply_patch_text(source: str, patch: PatchSpec, content: str) -> tuple[str, int]:
    matches = _find_anchor_lines(source, patch.anchor)
    if len(matches) < patch.occurrence:
        raise BuildError(
            f"{patch.id}: anchor {patch.anchor!r} occurrence {patch.occurrence} not found"
        )
    line_index = matches[patch.occurrence - 1]
    lines = source.splitlines(keepends=True)
    patch_lines = _ensure_trailing_newline(content).splitlines(keepends=True)

    if patch.mode == "insert_before":
        output = lines[:line_index] + patch_lines + lines[line_index:]
    elif patch.mode == "insert_after":
        output = lines[: line_index + 1] + patch_lines + lines[line_index + 1 :]
    elif patch.mode == "replace":
        output = lines[:line_index] + patch_lines + lines[line_index + 1 :]
    else:
        raise BuildError(f"{patch.id}: unsupported patch mode {patch.mode}")
    return "".join(output), line_index + 1


def apply_patch_to_file(
    host_root: Path,
    output_root: Path,
    module: ModuleManifest,
    patch: PatchSpec,
) -> AppliedPatch:
    source_path = (host_root / patch.target_file).resolve()
    patch_path = (module.root / patch.file).resolve()
    if not source_path.exists():
        raise BuildError(f"{module.id}:{patch.id}: target file does not exist: {patch.target_file}")
    if not patch_path.exists():
        raise BuildError(f"{module.id}:{patch.id}: patch file does not exist: {patch.file}")

    try:
        source_path.relative_to(host_root.resolve())
    except ValueError as exc:
        raise BuildError(f"{module.id}:{patch.id}: target escapes host root") from exc
    try:
        patch_path.relative_to(module.root.resolve())
    except ValueError as exc:
        raise BuildError(f"{module.id}:{patch.id}: patch file escapes module root") from exc

    source = source_path.read_text(encoding="utf-8")
    content = patch_path.read_text(encoding="utf-8")
    patched, anchor_line = apply_patch_text(source, patch, content)

    output_path = output_root / patch.target_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(patched, encoding="utf-8", newline="\n")
    return AppliedPatch(
        module_id=module.id,
        patch_id=patch.id,
        target_file=patch.target_file,
        output_file=str(output_path.relative_to(output_root.parent)),
        mode=patch.mode,
        anchor=patch.anchor,
        anchor_line=anchor_line,
        occurrence=patch.occurrence,
        risk=patch.risk,
    )


def _find_anchor_lines(source: str, anchor: str) -> list[int]:
    matches: list[int] = []
    for index, line in enumerate(source.splitlines(keepends=True)):
        if anchor in line:
            matches.append(index)
    return matches


def _ensure_trailing_newline(value: str) -> str:
    if value.endswith("\n"):
        return value
    return value + "\n"

