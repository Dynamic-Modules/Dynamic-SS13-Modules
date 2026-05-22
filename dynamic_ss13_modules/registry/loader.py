from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

from dynamic_ss13_modules.errors import ValidationError
from dynamic_ss13_modules.io import read_json
from dynamic_ss13_modules.manifest.models import HostConfig, RegistrySpec


def load_registry(host: HostConfig, registry: RegistrySpec) -> dict[str, Any]:
    if not registry.trusted:
        raise ValidationError(f"registry {registry.name} is not trusted in host config")
    if registry.path:
        return read_json((host.root / registry.path).resolve())
    if registry.url:
        with urllib.request.urlopen(registry.url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            raise ValidationError(f"registry {registry.name} returned non-object JSON")
        return data
    raise ValidationError(f"registry {registry.name} has neither path nor url")


def load_registries(host: HostConfig) -> dict[str, dict[str, Any]]:
    return {registry.name: load_registry(host, registry) for registry in host.registries}

