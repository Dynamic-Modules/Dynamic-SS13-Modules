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
    matches = _find_anchor_spans(source, patch.anchor)
    if len(matches) < patch.occurrence:
        raise BuildError(
            f"{patch.id}: anchor {patch.anchor!r} occurrence {patch.occurrence} not found"
        )
    span = matches[patch.occurrence - 1]

    if patch.mode == "insert_before":
        output = source[: span.start] + _line_mode_content(content, patch.anchor) + source[span.start :]
    elif patch.mode == "insert_after":
        output = source[: span.end] + _line_mode_content(content, patch.anchor) + source[span.end :]
    elif patch.mode == "replace":
        output = source[: span.start] + _line_mode_content(content, patch.anchor) + source[span.end :]
    elif patch.mode == "replace_between":
        end_span = _find_first_anchor_span_after(source, patch.end_anchor or "", span.end)
        if end_span is None:
            raise BuildError(f"{patch.id}: end_anchor {patch.end_anchor!r} not found after anchor")
        output = source[: span.end] + content + source[end_span.start :]
    else:
        raise BuildError(f"{patch.id}: unsupported patch mode {patch.mode}")
    return output, span.line


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


@dataclass(frozen=True)
class AnchorSpan:
    start: int
    end: int
    line: int


def _find_anchor_spans(source: str, anchor: str) -> list[AnchorSpan]:
    if "\n" in anchor:
        return _find_block_anchor_spans(source, anchor)
    return _find_line_anchor_spans(source, anchor)


def _find_line_anchor_spans(source: str, anchor: str) -> list[AnchorSpan]:
    matches: list[AnchorSpan] = []
    offset = 0
    for line_number, line in enumerate(source.splitlines(keepends=True), start=1):
        line_end = offset + len(line)
        if anchor in line:
            matches.append(AnchorSpan(start=offset, end=line_end, line=line_number))
        offset = line_end
    return matches


def _find_block_anchor_spans(source: str, anchor: str) -> list[AnchorSpan]:
    matches: list[AnchorSpan] = []
    index = source.find(anchor)
    while index != -1:
        matches.append(
            AnchorSpan(
                start=index,
                end=index + len(anchor),
                line=source.count("\n", 0, index) + 1,
            )
        )
        index = source.find(anchor, index + max(1, len(anchor)))
    return matches


def _find_first_anchor_span_after(source: str, anchor: str, offset: int) -> AnchorSpan | None:
    for span in _find_anchor_spans(source, anchor):
        if span.start >= offset:
            return span
    return None


def _line_mode_content(content: str, anchor: str) -> str:
    if content == "" or "\n" in anchor or content.endswith("\n"):
        return content
    return content + "\n"
