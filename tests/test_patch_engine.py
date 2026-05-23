from __future__ import annotations

import unittest
from pathlib import Path

from dynamic_ss13_modules.manifest.models import PatchSpec
from dynamic_ss13_modules.patches.engine import apply_patch_text


class PatchEngineTests(unittest.TestCase):
    def test_line_insert_after_keeps_legacy_line_anchor_behavior(self) -> None:
        patched, anchor_line = apply_patch_text(
            "one\nanchor()\nthree\n",
            patch("insert_after", "anchor()"),
            "\tinserted()\n",
        )

        self.assertEqual(patched, "one\nanchor()\n\tinserted()\nthree\n")
        self.assertEqual(anchor_line, 2)

    def test_multiline_replace_replaces_exact_anchor_block(self) -> None:
        patched, anchor_line = apply_patch_text(
            "one\nif(TRUE)\n\told_a()\n\told_b()\nthree\n",
            patch("replace", "if(TRUE)\n\told_a()\n\told_b()\n"),
            "if(TRUE)\n\tnew_a()\n\tnew_b()\n",
        )

        self.assertEqual(patched, "one\nif(TRUE)\n\tnew_a()\n\tnew_b()\nthree\n")
        self.assertEqual(anchor_line, 2)

    def test_empty_replace_deletes_line_anchor(self) -> None:
        patched, anchor_line = apply_patch_text(
            "one\n\tdelete_me()\nthree\n",
            patch("replace", "delete_me()"),
            "",
        )

        self.assertEqual(patched, "one\nthree\n")
        self.assertEqual(anchor_line, 2)

    def test_multiline_anchor_occurrence_selects_later_block(self) -> None:
        source = (
            "if(TRUE)\n"
            "\tthing = 1\n"
            "if(TRUE)\n"
            "\tthing = 1\n"
        )
        patched, anchor_line = apply_patch_text(
            source,
            patch("replace", "if(TRUE)\n\tthing = 1\n", occurrence=2),
            "if(TRUE)\n\tthing = 2\n",
        )

        self.assertEqual(
            patched,
            "if(TRUE)\n"
            "\tthing = 1\n"
            "if(TRUE)\n"
            "\tthing = 2\n",
        )
        self.assertEqual(anchor_line, 3)

    def test_replace_between_uses_start_and_end_line_anchors(self) -> None:
        patched, anchor_line = apply_patch_text(
            "before()\n\told_a()\n\told_b()\nafter()\n",
            patch("replace_between", "before()", end_anchor="after()"),
            "\tnew_a()\n",
        )

        self.assertEqual(patched, "before()\n\tnew_a()\nafter()\n")
        self.assertEqual(anchor_line, 1)


def patch(
    mode: str,
    anchor: str,
    occurrence: int = 1,
    end_anchor: str | None = None,
) -> PatchSpec:
    return PatchSpec(
        id="test-patch",
        target_file="code/example.dm",
        mode=mode,
        anchor=anchor,
        file="patches/test.dm",
        end_anchor=end_anchor,
        occurrence=occurrence,
    )


if __name__ == "__main__":
    unittest.main()
