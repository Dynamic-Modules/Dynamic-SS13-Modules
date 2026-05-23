from __future__ import annotations

from pathlib import Path
from typing import Any

from dynamic_ss13_modules.errors import BuildError
from dynamic_ss13_modules.io import read_json


def load_index(build_dir: Path) -> dict[str, Any]:
    index_path = build_dir / "index.json"
    if not index_path.exists():
        raise BuildError(f"missing {index_path}; run dynamic-modules prepare first")
    return read_json(index_path)


def explain_file(index: dict[str, Any], file_value: str) -> list[str]:
    host_root = Path(index["host_root"]).resolve()
    requested = Path(file_value)
    if requested.is_absolute():
        try:
            key = requested.resolve().relative_to(host_root).as_posix()
        except ValueError:
            key = requested.as_posix()
    else:
        key = requested.as_posix()

    interactions = index.get("files", {}).get(key, [])
    if not interactions:
        return [f"No Dynamic Modules interactions recorded for {key}."]

    lines = [f"Dynamic Modules interactions for {key}:"]
    for item in interactions:
        kind = item.get("kind")
        module = item.get("module")
        item_id = item.get("id")
        if kind == "patch":
            lines.append(
                f"- patch {module}:{item_id} at line {item.get('anchor_line')} "
                f"({item.get('mode')} anchor {item.get('anchor')!r})"
            )
            lines.append(f"  materialized output: {item.get('output_file')}")
        elif kind == "module_patch":
            lines.append(
                f"- local module patch {module}:{item_id} at line {item.get('anchor_line')} "
                f"({item.get('mode')} anchor {item.get('anchor')!r})"
            )
            lines.append(f"  materialized module source: {item.get('output_file')}")
        elif kind == "hook":
            lines.append(
                f"- hook {module}:{item_id} targets {item.get('target')} "
                f"via {item.get('mode')}"
            )
            if item.get("source_file"):
                lines.append(f"  source: {item.get('source_file')}")
        else:
            lines.append(f"- {kind} {module}:{item_id}")
    return lines


def module_summary(index: dict[str, Any]) -> list[str]:
    lines = ["Dynamic Modules load order:"]
    modules = index.get("modules", {})
    for index_number, module_id in enumerate(index.get("load_order", []), start=1):
        module = modules.get(module_id, {})
        lines.append(f"{index_number}. {module_id} {module.get('version', '')} - {module.get('name', '')}")
    return lines
