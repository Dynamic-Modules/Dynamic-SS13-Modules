from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from dynamic_ss13_modules.cli import main


class ModuleOpsTests(unittest.TestCase):
    def test_module_add_and_remove_use_registry_submodule_and_prepare(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module_repo = root / "example-module-repo"
            host = root / "host"
            module_commit = _write_module_repo(module_repo)
            _write_host_repo(host, module_repo)

            add_result = _run_cli(["--root", str(host), "module", "add", "example-module"])

            self.assertEqual(add_result, 0)
            module_path = host / "dynamic_modules" / "installed" / "example-module"
            self.assertTrue((module_path / "example-module.module.toml").exists())
            self.assertIn(
                "dynamic_modules/installed/example-module",
                (host / ".gitmodules").read_text(encoding="utf-8"),
            )

            lockfile = json.loads((host / "dynamic_modules.lock.json").read_text(encoding="utf-8"))
            self.assertEqual(lockfile["modules"]["example-module"]["commit"], module_commit)

            include_text = (
                host
                / ".dynamic_modules_build"
                / "generated"
                / "_dynamic_modules_includes.dm"
            ).read_text(encoding="utf-8")
            self.assertIn(
                '#include "../../dynamic_modules/installed/example-module/code/example.dm"',
                include_text,
            )

            remove_result = _run_cli(["--root", str(host), "module", "remove", "example-module"])

            self.assertEqual(remove_result, 0)
            self.assertFalse(module_path.exists())
            lockfile = json.loads((host / "dynamic_modules.lock.json").read_text(encoding="utf-8"))
            self.assertEqual(lockfile["modules"], {})
            include_text = (
                host
                / ".dynamic_modules_build"
                / "generated"
                / "_dynamic_modules_includes.dm"
            ).read_text(encoding="utf-8")
            self.assertNotIn("example-module", include_text)


def _write_host_repo(host: Path, module_repo: Path) -> None:
    host.mkdir(parents=True)
    (host / "dynamic_modules" / "installed").mkdir(parents=True)
    (host / "config" / "dynamic_modules").mkdir(parents=True)
    (host / "registries").mkdir(parents=True)
    (host / "dynamic_modules.toml").write_text(
        "\n".join(
            [
                'module_roots = ["dynamic_modules/installed"]',
                'config_dir = "config/dynamic_modules"',
                'lockfile = "dynamic_modules.lock.json"',
                "",
                "[build]",
                'dir = ".dynamic_modules_build"',
                'materialize_mode = "overlay"',
                "",
                "[[registries]]",
                'name = "local"',
                'path = "registries/modules.json"',
                "trusted = true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (host / "registries" / "modules.json").write_text(
        json.dumps(
            {
                "modules": {
                    "example-module": {
                        "repo": str(module_repo),
                        "default_branch": "main",
                    }
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _init_repo(host)
    _configure_git_identity(host)
    _git(host, "add", ".")
    _git(host, "commit", "-m", "Initialize host")


def _write_module_repo(module_repo: Path) -> str:
    module_repo.mkdir(parents=True)
    (module_repo / "code").mkdir()
    (module_repo / "tests").mkdir()
    (module_repo / "config").mkdir()
    (module_repo / "example-module.module.toml").write_text(
        "\n".join(
            [
                'id = "example-module"',
                'name = "Example Module"',
                'version = "1.0.0"',
                'module_api = "1"',
                "",
                "[source]",
                f'repo = "{module_repo.as_posix()}"',
                'default_branch = "main"',
                "",
                "[build]",
                'dm_files = ["code/*.dm"]',
                'test_files = ["tests/*.dm"]',
                "",
                "[config]",
                'defaults = "config/default.toml"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (module_repo / "code" / "example.dm").write_text(
        "/datum/example_module\n\tvar/name = \"example\"\n",
        encoding="utf-8",
    )
    (module_repo / "tests" / "example_unit.dm").write_text(
        "/datum/unit_test/example_module/Run()\n\treturn\n",
        encoding="utf-8",
    )
    (module_repo / "config" / "default.toml").write_text(
        'enabled = true\n',
        encoding="utf-8",
    )
    _init_repo(module_repo)
    _configure_git_identity(module_repo)
    _git(module_repo, "add", ".")
    _git(module_repo, "commit", "-m", "Initial example module")
    return _git(module_repo, "rev-parse", "HEAD").strip()


def _configure_git_identity(repo: Path) -> None:
    _git(repo, "config", "user.name", "Dynamic Modules Test")
    _git(repo, "config", "user.email", "dynamic-modules@example.invalid")


def _init_repo(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")


def _run_cli(args: list[str]) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return main(args)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout


if __name__ == "__main__":
    unittest.main()
