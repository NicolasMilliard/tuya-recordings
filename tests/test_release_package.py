from zipfile import ZipFile

from tools.build_release_zip import build_archive


def test_hacs_release_archive_has_integration_files_at_zip_root(tmp_path):
    archive_path = tmp_path / "tuya_recordings.zip"

    build_archive(archive_path)

    with ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "manifest.json" in names
    assert "__init__.py" in names
    assert any(name.startswith("frontend/") for name in names)
    assert not any(name.startswith("custom_components/") for name in names)
    assert not any("__pycache__/" in name or name.endswith(".pyc") for name in names)
