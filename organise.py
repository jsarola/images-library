import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image, UnidentifiedImageError

load_dotenv()

FOLDER_ORIG = os.environ["FOLDER_ORIG"]
FOLDER_DEST = os.environ["FOLDER_DEST"]

# EXIF tag IDs for capture date, in priority order
_EXIF_DATE_TAGS = (36867, 36868, 306)  # DateTimeOriginal, DateTimeDigitized, DateTime
_EXIF_DATE_FMT = "%Y:%m:%d %H:%M:%S"

# Patterns tried in order (longest first). Anchored with (?<!\d)/(?!\d) to avoid
# matching a partial run of digits inside a longer numeric sequence.
_FILENAME_DATE_PATTERNS = [
    (re.compile(r"(?<!\d)(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)"), "%Y%m%d%H%M"),  # YYYYMMDDHHmm
    (re.compile(r"(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)"),                "%Y%m%d"),       # YYYYMMDD
    (re.compile(r"(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)"),                "%y%m%d"),       # YYMMDD
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".webp", ".bmp", ".gif"}


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
                return datetime.strptime("".join(m.groups()), fmt)
            except ValueError:
                continue  # digits matched but not a valid calendar date
    return None


def get_image_date(path: Path) -> datetime | None:
    """Return capture date from EXIF, then filename pattern, then None."""
    return _exif_date(path) or _filename_date(path)


def dest_dir(base: Path, dt: datetime) -> Path:
    return base / f"{dt.year:04d}" / f"{dt.month:02d}" / dt.strftime("%Y-%m-%d")


def _safe_copy(img_path: Path, target_dir: Path) -> Path:
    """Copy img_path into target_dir, adding a counter suffix on name collision."""
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / img_path.name
    if target.exists():
        stem, suffix = img_path.stem, img_path.suffix
        counter = 1
        while target.exists():
            target = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    shutil.copy2(img_path, target)
    return target


def organise():
    src = Path(FOLDER_ORIG)
    dst = Path(FOLDER_DEST)

    images = [p for p in src.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    print(f"Found {len(images)} image(s) in {src}")

    for img_path in images:
        dt = get_image_date(img_path)
        if dt is None:
            target_dir = dst / "NODATE"
            target = _safe_copy(img_path, target_dir)
            print(f"  {img_path.name} -> NODATE/{target.name}  [no date found]")
        else:
            target = _safe_copy(img_path, dest_dir(dst, dt))
            print(f"  {img_path.name} -> {target.relative_to(dst)}")

    print("Done.")


if __name__ == "__main__":
    organise()
