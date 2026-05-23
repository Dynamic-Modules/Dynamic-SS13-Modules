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

    def test_local_module_patch_materializes_and_rewrites_include(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "host_tgstation"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "host"
            shutil.copytree(source, root)
            patch_dir = root / "config" / "dynamic_modules" / "patches" / "trip-system"
            patch_dir.mkdir(parents=True)
            (patch_dir / "patches.toml").write_text(
                "\n".join(
                    [
                        "[[patches]]",
                        'module = "trip-system"',
                        'id = "server-trip-extra-state"',
                        'target_file = "code/trip_system.dm"',
                        'mode = "insert_after"',
                        'anchor = "var/trip_chance = 5"',
                        'file = "extra_state.dm"',
                        'risk = "server_local"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (patch_dir / "extra_state.dm").write_text(
                "\tvar/server_override = TRUE\n",
                encoding="utf-8",
            )

            host = load_host_config(root)
            graph = resolve_modules(discover_manifests(host))
            result = prepare_build(host, graph, write_lock=False)
            include_text = result.include_path.read_text(encoding="utf-8")
            patched = root / ".dynamic_modules_build" / "module_patches" / "trip-system" / "code" / "trip_system.dm"
            index = json.loads(result.index_path.read_text(encoding="utf-8"))

            self.assertTrue(patched.exists())
            self.assertIn("var/server_override = TRUE", patched.read_text(encoding="utf-8"))
            self.assertIn(
                '#include "../module_patches/trip-system/code/trip_system.dm"',
                include_text,
            )
            self.assertNotIn(
                '#include "../../dynamic_modules/installed/trip-system/code/trip_system.dm"',
                include_text,
            )

            source_key = "dynamic_modules/installed/trip-system/code/trip_system.dm"
            interactions = index["files"][source_key]
            self.assertTrue(any(item["kind"] == "module_patch" for item in interactions))
            self.assertEqual(
                index["modules"]["trip-system"]["dm_files"],
                [".dynamic_modules_build/module_patches/trip-system/code/trip_system.dm"],
            )

    def test_tgui_files_are_indexed_and_dynamic_tgui_wrapper_is_generated(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "host_tgstation"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "host"
            shutil.copytree(source, root)
            dynamic_tgui = root / "dynamic_modules" / "installed" / "dynamic-tgui"
            (dynamic_tgui / "tools").mkdir(parents=True)
            (dynamic_tgui / "tools" / "cli.ts").write_text("export {};\n", encoding="utf-8")
            (dynamic_tgui / "prepare_plugin.py").write_text(
                "\n".join(
                    [
                        "import json",
                        "import os",
                        "from pathlib import Path",
                        "",
                        "context = json.loads(Path(os.environ['DYNAMIC_MODULES_PREPARE_CONTEXT']).read_text(encoding='utf-8'))",
                        "host_root = Path(os.environ['DYNAMIC_MODULES_HOST_ROOT'])",
                        "build_dir = Path(os.environ['DYNAMIC_MODULES_BUILD_DIR'])",
                        "wrapper = build_dir / 'tgui' / 'cli.ts'",
                        "module_root = host_root / context['modules']['dynamic-tgui']['root']",
                        "wrapper.parent.mkdir(parents=True, exist_ok=True)",
                        "module_cli = os.path.relpath(module_root / 'tools' / 'cli.ts', wrapper.parent).replace(os.sep, '/')",
                        "wrapper.write_text('\\n'.join([",
                        "    '#!/usr/bin/env bun',",
                        "    '// test wrapper',",
                        "    f'await import({module_cli!r});',",
                        "    '',",
                        "]), encoding='utf-8', newline='\\n')",
                        "output = {",
                        "    'generated': {'tgui_cli_file': wrapper.relative_to(host_root).as_posix()},",
                        "    'files': {",
                        "        'tgui/package.json': [",
                        "            {'kind': 'prepare_plugin', 'module': 'dynamic-tgui', 'id': 'dynamic-tgui-cli-wrapper'}",
                        "        ]",
                        "    },",
                        "}",
                        "Path(os.environ['DYNAMIC_MODULES_PREPARE_OUTPUT']).write_text(json.dumps(output), encoding='utf-8')",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (dynamic_tgui / "dynamic-tgui.module.toml").write_text(
                "\n".join(
                    [
                        'id = "dynamic-tgui"',
                        'name = "Dynamic TGUI"',
                        'version = "1.0.0"',
                        'module_api = "1"',
                        "",
                        "[[prepare_plugins]]",
                        'id = "dynamic-tgui-cli-wrapper"',
                        'command = "python3"',
                        'args = ["prepare_plugin.py"]',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            tgui_module = root / "dynamic_modules" / "installed" / "trip-system" / "tgui"
            tgui_module.mkdir()
            (tgui_module / "trip_panel.tgui.ts").write_text(
                "export const modularTgui = true;\n", encoding="utf-8"
            )
            manifest_path = root / "dynamic_modules" / "installed" / "trip-system" / "trip-system.module.toml"
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8")
                .replace('test_files = ["tests/**/*.dm"]', 'test_files = ["tests/**/*.dm"]\ntgui = ["tgui/**/*.tgui.ts"]'),
                encoding="utf-8",
            )

            host = load_host_config(root)
            graph = resolve_modules(discover_manifests(host))
            result = prepare_build(host, graph, write_lock=False)
            index = json.loads(result.index_path.read_text(encoding="utf-8"))

            self.assertEqual(
                index["modules"]["trip-system"]["tgui_files"],
                ["dynamic_modules/installed/trip-system/tgui/trip_panel.tgui.ts"],
            )
            self.assertEqual(
                index["generated"]["tgui_cli_file"],
                ".dynamic_modules_build/tgui/cli.ts",
            )
            self.assertEqual(len(result.plugin_output_paths), 1)
            self.assertTrue(result.plugin_context_path.exists())
            tgui_cli_path = root / index["generated"]["tgui_cli_file"]
            self.assertTrue(tgui_cli_path.exists())
            self.assertIn(
                "../../dynamic_modules/installed/dynamic-tgui/tools/cli.ts",
                tgui_cli_path.read_text(encoding="utf-8"),
            )
            self.assertEqual(
                index["prepare_plugins"][0]["id"],
                "dynamic-tgui-cli-wrapper",
            )
            self.assertTrue(
                any(item["kind"] == "prepare_plugin" for item in index["files"]["tgui/package.json"])
            )


if __name__ == "__main__":
    unittest.main()
