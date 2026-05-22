from __future__ import annotations

import shutil
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()

