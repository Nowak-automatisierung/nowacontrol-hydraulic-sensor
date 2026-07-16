"""Regression tests for repository-portable quirk README links."""

from __future__ import annotations

import re
import shutil
import stat
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TARGET_NAME = "nowacontrol_hydraulic_sensor_v1.py"
ALLOWED_TARGET = f"./{TARGET_NAME}"
README_PATHS = (
    Path("homeassistant/zha_quirks/README.md"),
    Path("custom_components/nowacontrol_hydraulic_sensor/quirks/README.md"),
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def _assert_portable_quirk_link(test_case: unittest.TestCase, readme: Path) -> None:
    """Assert that *readme* has one local, case-correct, regular-file link."""

    contents = readme.read_text(encoding="utf-8")
    targets = MARKDOWN_LINK.findall(contents)
    test_case.assertEqual(targets, [ALLOWED_TARGET])

    target = targets[0]
    banned_fragments = (
        "C:\\Users\\",
        "C:/Users/",
        "/C:/Users/",
        "/Users/",
        "file://",
        "m" + "nowak",
        str(REPOSITORY_ROOT),
        REPOSITORY_ROOT.as_posix(),
        str(REPOSITORY_ROOT).replace("/", "\\"),
    )
    for fragment in banned_fragments:
        test_case.assertNotIn(fragment, target)

    posix_target = PurePosixPath(target)
    windows_target = PureWindowsPath(target)
    test_case.assertFalse(posix_target.is_absolute())
    test_case.assertFalse(windows_target.is_absolute())
    test_case.assertFalse(windows_target.drive)
    test_case.assertNotIn("..", posix_target.parts)
    test_case.assertNotIn("..", windows_target.parts)
    test_case.assertNotIn("../", target)
    test_case.assertNotIn("..\\", target)

    readme_directory = readme.parent
    linked_path = readme_directory / posix_target
    test_case.assertFalse(linked_path.is_symlink())
    test_case.assertTrue(linked_path.exists())
    test_case.assertTrue(stat.S_ISREG(linked_path.lstat().st_mode))
    test_case.assertEqual(linked_path.name, TARGET_NAME)
    test_case.assertIn(TARGET_NAME, {entry.name for entry in readme_directory.iterdir()})
    test_case.assertEqual(linked_path.resolve(strict=True).parent, readme_directory.resolve(strict=True))


class RepositoryPortabilityTests(unittest.TestCase):
    def test_quirk_readme_links_are_repository_relative(self) -> None:
        for relative_readme in README_PATHS:
            with self.subTest(readme=relative_readme):
                _assert_portable_quirk_link(self, REPOSITORY_ROOT / relative_readme)

    def test_validation_is_independent_of_checkout_location(self) -> None:
        layouts = (
            Path("home-alice/work/nowacontrol-hydraulic-sensor"),
            Path("unrelated-parent/deeper/repo-under-test"),
            Path("export-without-git"),
        )
        with tempfile.TemporaryDirectory(prefix="hyd-portability-") as temporary_directory:
            temporary_root = Path(temporary_directory)
            for layout in layouts:
                for relative_readme in README_PATHS:
                    with self.subTest(layout=layout, readme=relative_readme):
                        source_readme = REPOSITORY_ROOT / relative_readme
                        copied_readme = temporary_root / layout / relative_readme
                        copied_readme.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source_readme, copied_readme)
                        shutil.copyfile(
                            source_readme.parent / TARGET_NAME,
                            copied_readme.parent / TARGET_NAME,
                        )
                        _assert_portable_quirk_link(self, copied_readme)


if __name__ == "__main__":
    unittest.main()
