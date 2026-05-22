from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from dynamic_ss13_modules.build import prepare_build
from dynamic_ss13_modules.manifest import discover_manifests, load_host_config
from dynamic_ss13_modules.resolver import resolve_modules


class PrepareTests(unittest.TestCase):
    def test_prepare_generates_index_includes_config_and_patch_overlay(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "host_tgstation"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "host"
            shutil.copytree(source, root)
            host = load_host_config(root)
            graph = resolve_modules(discover_manifests(host))

            result = prepare_build(host, graph, write_lock=True)

            self.assertTrue(result.index_path.exists())
            self.assertTrue(result.include_path.exists())
            self.assertTrue(result.tests_path.exists())
            self.assertTrue(result.config_path.exists())
            self.assertTrue(host.lockfile.exists())

            index = json.loads(result.index_path.read_text(encoding="utf-8"))
            self.assertEqual(index["load_order"], ["trip-system"])
            self.assertIn(
                "code/modules/mob/living/carbon/human/human_movement.dm",
                index["files"],
            )
            interactions = index["files"]["code/modules/mob/living/carbon/human/human_movement.dm"]
            self.assertTrue(any(item["kind"] == "patch" for item in interactions))
            self.assertTrue(any(item["kind"] == "hook" for item in interactions))

            config = json.loads(result.config_path.read_text(encoding="utf-8"))
            self.assertEqual(config["trip-system"]["values"]["trip_chance"], 7)

            patched = root / ".dynamic_modules_build" / "patched" / "code/modules/mob/living/carbon/human/human_movement.dm"
            self.assertIn(
                "dynamic_module_trip_system_movement_hook(src)",
                patched.read_text(encoding="utf-8"),
            )

    def test_include_manifest_uses_relative_paths(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "host_tgstation"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "host"
            shutil.copytree(source, root)
            host = load_host_config(root)
            graph = resolve_modules(discover_manifests(host))

            result = prepare_build(host, graph, write_lock=False)
            include_text = result.include_path.read_text(encoding="utf-8")

            self.assertIn('#include "../../dynamic_modules/installed/trip-system/code/trip_system.dm"', include_text)

    def test_multiple_patches_to_same_file_compose_in_load_order(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "host_tgstation"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "host"
            shutil.copytree(source, root)
            addon = root / "dynamic_modules" / "installed" / "trip-addon"
            (addon / "patches").mkdir(parents=True)
            (addon / "trip-addon.module.toml").write_text(
                "\n".join(
                    [
                        'id = "trip-addon"',
                        'name = "Trip Addon"',
                        'version = "1.0.0"',
                        'module_api = "1"',
                        "",
                        "[load]",
                        'requires = ["trip-system >= 1.0.0"]',
                        "",
                        "[[patches]]",
                        'id = "second-trip-hook"',
                        'target_file = "code/modules/mob/living/carbon/human/human_movement.dm"',
                        'mode = "insert_after"',
                        'anchor = "dynamic_module_trip_system_movement_hook(src)"',
                        'file = "patches/second.dm"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (addon / "patches" / "second.dm").write_text(
                "\tdynamic_module_trip_addon_hook(src)\n",
                encoding="utf-8",
            )

            host = load_host_config(root)
            graph = resolve_modules(discover_manifests(host))
            result = prepare_build(host, graph, write_lock=False)
            index = json.loads(result.index_path.read_text(encoding="utf-8"))

            self.assertEqual(index["load_order"], ["trip-system", "trip-addon"])
            patched = root / ".dynamic_modules_build" / "patched" / "code/modules/mob/living/carbon/human/human_movement.dm"
            patched_text = patched.read_text(encoding="utf-8")
            self.assertIn("dynamic_module_trip_system_movement_hook(src)", patched_text)
            self.assertIn("dynamic_module_trip_addon_hook(src)", patched_text)


if __name__ == "__main__":
    unittest.main()
