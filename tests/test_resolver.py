from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dynamic_ss13_modules.errors import ResolveError
from dynamic_ss13_modules.manifest import discover_manifests, load_host_config
from dynamic_ss13_modules.resolver import resolve_modules


class ResolverTests(unittest.TestCase):
    def test_dependencies_determine_load_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_host(root)
            _write_module(root, "base", "1.0.0")
            _write_module(root, "feature", "1.0.0", requires=["base >= 1.0.0"])

            graph = resolve_modules(discover_manifests(load_host_config(root)))

            self.assertEqual(graph.load_order, ["base", "feature"])

    def test_missing_requirement_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_host(root)
            _write_module(root, "feature", "1.0.0", requires=["base >= 1.0.0"])

            with self.assertRaises(ResolveError):
                resolve_modules(discover_manifests(load_host_config(root)))

    def test_load_hint_cycle_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_host(root)
            _write_module(root, "a", "1.0.0", load_after=["b"])
            _write_module(root, "b", "1.0.0", load_after=["a"])

            with self.assertRaises(ResolveError):
                resolve_modules(discover_manifests(load_host_config(root)))


def _write_host(root: Path) -> None:
    (root / "dynamic_modules").mkdir(parents=True)
    (root / "dynamic_modules.toml").write_text(
        'module_roots = ["dynamic_modules"]\n',
        encoding="utf-8",
    )


def _write_module(
    root: Path,
    module_id: str,
    version: str,
    requires: list[str] | None = None,
    load_after: list[str] | None = None,
) -> None:
    module_root = root / "dynamic_modules" / module_id
    module_root.mkdir(parents=True)
    lines = [
        f'id = "{module_id}"',
        f'name = "{module_id}"',
        f'version = "{version}"',
        'module_api = "1"',
        "",
        "[load]",
    ]
    if requires:
        lines.append("requires = [" + ", ".join(f'"{item}"' for item in requires) + "]")
    if load_after:
        lines.append("load_after = [" + ", ".join(f'"{item}"' for item in load_after) + "]")
    (module_root / f"{module_id}.module.toml").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()

