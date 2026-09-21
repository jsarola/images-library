# AGENTS.md

This file provides guidance to Agentic Code when working with code in this repository.

## Project

`images-library` is a Python utility that organizes images into a date-based directory tree: `YYYY/MM/YYYY-MM-DD/`.

## Runtime and tooling

- Python 3.14 or newer is required (`requires-python = ">=3.14"`).
- Poetry manages the environment and locked dependencies. This is an application-style project with `package-mode = false`.
- Install dependencies with `poetry install`.
- Run the utility with `poetry run python organise.py`.
- Run the unit tests with `poetry run python -m unittest discover -s tests -v`.
- At minimum, run the unit tests and `poetry run python -m compileall organise.py tests` after code changes.
- Keep `poetry.lock` committed. When dependencies change, update both `pyproject.toml` and the lock file.

## Configuration

Copy `.env.example` to the Git-ignored `.env` file before running the utility. All settings are required:

- `FOLDER_ORIG`: source directory searched recursively for supported images.
- `FOLDER_DEST`: root for successfully dated images, organized as `YYYY/MM/YYYY-MM-DD/`.
- `FOLDER_ERROR`: directory for images with no valid EXIF or filename date.
- `DATE_PATTERNS`: ordered, comma-separated `datetime.strptime` formats used to scan filenames. Keep the most specific formats first. Supported directives are `%Y`, `%y`, `%m`, `%d`, `%H`, `%M`, and `%S`.

Never commit `.env` or local image directories. Update `.env.example` and this section whenever configuration changes.

## Implementation notes

- `organise.py` is the current entry point.
- Date resolution order is EXIF (`DateTimeOriginal`, `DateTimeDigitized`, `DateTime`), then the configured filename patterns.
- Supported extensions are defined by `IMAGE_EXTENSIONS` in `organise.py`.
- Files are copied, never moved or deleted. `_safe_copy` skips byte-identical existing files and adds numeric suffixes for differing name collisions while preserving metadata.
- Preserve compatibility with Python 3.14 and use standard-library functionality where practical.

## License

GNU Affero General Public License v3 (AGPL-3.0). Any changes must be shared under the same terms.
