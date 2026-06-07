# images-library

Organises images from a source folder into a date-based directory tree:

```
FOLDER_DEST/
└── YYYY/
    └── MM/
        └── YYYY-MM-DD/
            └── image.jpg
```

## Requirements

- Python 3.14+
- [Poetry](https://python-poetry.org/)

Install dependencies:

```bash
poetry install
```

## Configuration

Copy `.env.example` and fill in your paths:

```bash
cp .env.example .env
```

`.env` variables:

| Variable | Description |
|---|---|
| `FOLDER_ORIG` | Source folder containing the images to organise |
| `FOLDER_DEST` | Destination root where the date tree will be created |

## Usage

```bash
poetry run python organise.py
```

## How dates are resolved

For each image the date is determined in this order:

1. **EXIF metadata** — reads `DateTimeOriginal`, then `DateTimeDigitized`, then `DateTime`.
2. **Filename pattern** — scans the filename for a date sequence, tried longest-first:
   - `YYYYMMDDHHmm` (e.g. `IMG_202306071435.jpg`)
   - `YYYYMMDD` (e.g. `photo_20230607.jpg`)
   - `YYMMDD` (e.g. `pic_230607.jpg` — two-digit year: 00–68 → 2000–2068, 69–99 → 1969–1999)
3. **No date found** — file is copied to `FOLDER_DEST/NODATE/`.

Name collisions are resolved by appending a counter (`image_1.jpg`, `image_2.jpg`, …). Source files are never deleted.

## Supported formats

`.jpg` `.jpeg` `.png` `.tif` `.tiff` `.heic` `.webp` `.bmp` `.gif`

## License

GNU Affero General Public License v3 (AGPL-3.0) — see [LICENSE](LICENSE).
