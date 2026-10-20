"""Build and validate the flat HACS release archive for Tuya Recordings."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "tuya_recordings"
REQUIRED_ROOT_PATHS = ("manifest.json", "__init__.py", "frontend/")


def validate_archive(path: Path) -> None:
    """Reject nested or incomplete HACS archives before publication."""
    with ZipFile(path) as archive:
        names = set(archive.namelist())

    missing = [
        required
        for required in REQUIRED_ROOT_PATHS
        if (
            required not in names
            if not required.endswith("/")
            else not any(name.startswith(required) for name in names)
        )
    ]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Release archive is missing root paths: {joined}")

    nested = sorted(
        name for name in names if name.startswith("custom_components/")
    )
    if nested:
        raise ValueError(
            "Release archive must contain integration files at its root, not "
            "under custom_components/"
        )


def build_archive(output: Path) -> None:
    """Write an installable HACS archive with integration contents at ZIP root."""
    if not (INTEGRATION / "manifest.json").is_file():
        raise FileNotFoundError(f"Integration source is missing: {INTEGRATION}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted(INTEGRATION.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                archive.write(path, path.relative_to(INTEGRATION).as_posix())

    validate_archive(output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the flat HACS Tuya Recordings release archive."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "tuya_recordings.zip",
        help="ZIP file to create",
    )
    args = parser.parse_args()
    build_archive(args.output)


if __name__ == "__main__":
    main()
