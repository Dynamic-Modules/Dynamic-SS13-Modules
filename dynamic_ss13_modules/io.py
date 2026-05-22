from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from .errors import ValidationError


def read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ValidationError(f"{path}: invalid TOML: {exc}") from exc
    except OSError as exc:
        raise ValidationError(f"{path}: could not read file: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected a TOML table at document root")
    return data


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{path}: invalid JSON: {exc}") from exc
    except OSError as exc:
        raise ValidationError(f"{path}: could not read file: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{path}: expected a JSON object at document root")
    return data


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result

