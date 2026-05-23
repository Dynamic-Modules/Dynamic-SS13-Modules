from __future__ import annotations

import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from dynamic_ss13_modules.cli import main


class CliTests(unittest.TestCase):
    def test_prepare_command_succeeds_for_example_host(self) -> None:
        source = Path(__file__).resolve().parents[1] / "examples" / "host_tgstation"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "host"
            shutil.copytree(source, root)

            result = main(["--root", str(root), "prepare"])

            self.assertEqual(result, 0)
            self.assertTrue((root / ".dynamic_modules_build" / "index.json").exists())

    def test_version_flag_reports_package_version(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            with self.assertRaises(SystemExit) as raised:
                main(["--version"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("dynamic-modules 1.0.0", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
