import os
import shutil
import unittest
import uuid
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

# organise.py reads required configuration when imported. Tests replace the
# directory settings per test, while keeping the documented date formats.
os.environ["FOLDER_ORIG"] = "unused-test-source"
os.environ["FOLDER_DEST"] = "unused-test-destination"
os.environ["FOLDER_ERROR"] = "unused-test-errors"
os.environ["DATE_PATTERNS"] = "%Y%m%d%H%M,%Y%m%d,%y%m%d"

import organise


class OrganiseTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent / f".test-work-{uuid.uuid4().hex}"
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.source = self.root / "source"
        self.destination = self.root / "destination"
        self.errors = self.root / "errors"
        self.source.mkdir()

        organise.FOLDER_ORIG = str(self.source)
        organise.FOLDER_DEST = str(self.destination)
        organise.FOLDER_ERROR = str(self.errors)

    @staticmethod
    def _create_jpeg(
        path: Path, exif_date: str | None = None, color: str = "white"
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (2, 2), color=color)
        if exif_date is None:
            image.save(path)
            return

        exif = Image.Exif()
        exif[36867] = exif_date  # DateTimeOriginal
        image.save(path, exif=exif)

    def test_organise_routes_exif_patterns_and_missing_dates(self):
        files = {
            "exif_capture.jpg": "2021:02:03 04:05:06",
            "camera_202306071435.jpg": None,
            "holiday_20240229.jpg": None,
            "scan_991231.jpg": None,
            "no_date.jpg": None,
        }
        for filename, exif_date in files.items():
            self._create_jpeg(self.source / filename, exif_date)

        first_run_log = StringIO()
        with redirect_stdout(first_run_log):
            organise.organise()

        self.assertEqual(first_run_log.getvalue().count("new]"), 5)

        expected_destination_files = {
            Path("2021/02/2021-02-03/exif_capture.jpg"),
            Path("2023/06/2023-06-07/camera_202306071435.jpg"),
            Path("2024/02/2024-02-29/holiday_20240229.jpg"),
            Path("1999/12/1999-12-31/scan_991231.jpg"),
        }
        actual_destination_files = {
            path.relative_to(self.destination)
            for path in self.destination.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual_destination_files, expected_destination_files)

        actual_error_files = {
            path.relative_to(self.errors)
            for path in self.errors.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual_error_files, {Path("no_date.jpg")})

        # The utility copies images; successfully processed source files remain.
        self.assertEqual(
            {path.name for path in self.source.iterdir()},
            set(files),
        )

        second_run_log = StringIO()
        with redirect_stdout(second_run_log):
            organise.organise()
        self.assertEqual(second_run_log.getvalue().count("not copied"), 5)

    def test_safe_copy_deduplicates_identical_files_and_suffixes_differences(self):
        identical_source = self.root / "identical-source" / "photo.jpg"
        identical_target = self.root / "identical-target" / "photo.jpg"
        self._create_jpeg(identical_source)
        identical_target.parent.mkdir()
        shutil.copy2(identical_source, identical_target)

        with patch("organise.shutil.copy2") as copy:
            result, action = organise._safe_copy(
                identical_source, identical_target.parent
            )

        self.assertEqual(result, identical_target)
        self.assertEqual(action, organise.CopyAction.NOT_COPIED)
        copy.assert_not_called()
        self.assertEqual(list(identical_target.parent.iterdir()), [identical_target])

        different_source = self.root / "different-source" / "photo.jpg"
        different_target = self.root / "different-target" / "photo.jpg"
        self._create_jpeg(different_source, color="red")
        self._create_jpeg(different_target, color="blue")

        suffixed_target, action = organise._safe_copy(
            different_source, different_target.parent
        )
        self.assertEqual(suffixed_target.name, "photo_1.jpg")
        self.assertEqual(action, organise.CopyAction.NEW_COPY)
        self.assertEqual(suffixed_target.read_bytes(), different_source.read_bytes())

        repeated_target, action = organise._safe_copy(
            different_source, different_target.parent
        )
        self.assertEqual(repeated_target, suffixed_target)
        self.assertEqual(action, organise.CopyAction.NOT_COPIED)
        self.assertFalse((different_target.parent / "photo_2.jpg").exists())


if __name__ == "__main__":
    unittest.main()
