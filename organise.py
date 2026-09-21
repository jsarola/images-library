import filecmp
import os
import re
import shutil
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError

load_dotenv()

FOLDER_ORIG = os.environ["FOLDER_ORIG"]
FOLDER_DEST = os.environ["FOLDER_DEST"]
FOLDER_ERROR = os.environ["FOLDER_ERROR"]
DATE_PATTERNS = tuple(
    pattern.strip() for pattern in os.environ["DATE_PATTERNS"].split(",") if pattern.strip()
)

# EXIF tag IDs for capture date, in priority order
_EXIF_DATE_TAGS = (36867, 36868, 306)  # DateTimeOriginal, DateTimeDigitized, DateTime
_EXIF_DATE_FMT = "%Y:%m:%d %H:%M:%S"

_DATE_DIRECTIVES = {
    "%Y": r"\d{4}",
    "%y": r"\d{2}",
    "%m": r"\d{2}",
    "%d": r"\d{2}",
    "%H": r"\d{2}",
    "%M": r"\d{2}",
    "%S": r"\d{2}",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp", ".bmp", ".gif"}


class CopyAction(StrEnum):
    NEW = "new"
    NOT_COPIED = "not copied"
    NEW_COPY = "new copy"


def _date_regex(date_format: str) -> re.Pattern[str]:
    """Build a filename regex from a supported ``datetime.strptime`` format."""
    parts: list[str] = []
    index = 0
    while index < len(date_format):
        if date_format[index] == "%":
            directive = date_format[index : index + 2]
            try:
                parts.append(_DATE_DIRECTIVES[directive])
            except KeyError as exc:
                raise ValueError(
                    f"Unsupported DATE_PATTERNS directive {directive!r} in {date_format!r}"
                ) from exc
            index += 2
        else:
            parts.append(re.escape(date_format[index]))
            index += 1
    return re.compile(r"(?<!\d)" + "".join(parts) + r"(?!\d)")


_FILENAME_DATE_PATTERNS = tuple(
    (_date_regex(date_format), date_format) for date_format in DATE_PATTERNS
)


def _exif_date(path: Path) -> datetime | None:
    try:
        with Image.open(path) as img:
            exif = img._getexif()
            if exif:
                for tag in _EXIF_DATE_TAGS:
                    raw = exif.get(tag)
                    if raw:
                        return datetime.strptime(raw, _EXIF_DATE_FMT)
    except (UnidentifiedImageError, AttributeError, ValueError):
        pass
    return None


def _filename_date(path: Path) -> datetime | None:
    for pattern, fmt in _FILENAME_DATE_PATTERNS:
        m = pattern.search(path.stem)
        if m:
            try:
                return datetime.strptime(m.group(0), fmt)
            except ValueError:
                continue  # digits matched but not a valid calendar date
    return None


def get_image_date(path: Path) -> datetime | None:
    """Return capture date from EXIF, then filename pattern, then None."""
    return _exif_date(path) or _filename_date(path)


def dest_dir(base: Path, dt: datetime) -> Path:
    return base / f"{dt.year:04d}" / f"{dt.month:02d}" / dt.strftime("%Y-%m-%d")


def _safe_copy(img_path: Path, target_dir: Path) -> tuple[Path, CopyAction]:
    """Copy an image unless an identical candidate already exists."""
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / img_path.name
    name_collision = target.exists()
    stem, suffix = img_path.stem, img_path.suffix
    counter = 1
    while target.exists():
        if filecmp.cmp(img_path, target, shallow=False):
            return target, CopyAction.NOT_COPIED
        target = target_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    shutil.copy2(img_path, target)
    action = CopyAction.NEW_COPY if name_collision else CopyAction.NEW
    return target, action


def organise():
    src = Path(FOLDER_ORIG)
    dst = Path(FOLDER_DEST)
    error_dir = Path(FOLDER_ERROR)

    images = [p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    print(f"Found {len(images)} image(s) in {src}")

    for img_path in images:
        dt = get_image_date(img_path)
        if dt is None:
            target, action = _safe_copy(img_path, error_dir)
            print(f"  {img_path.name} -> {target}  [no date found; {action}]")
        else:
            target, action = _safe_copy(img_path, dest_dir(dst, dt))
            print(f"  {img_path.name} -> {target.relative_to(dst)}  [{action}]")

    print("Done.")


if __name__ == "__main__":
    organise()
