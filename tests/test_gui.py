from pathlib import Path

from duplicate_verifier.actions import send_marked_to_trash
from duplicate_verifier.gui import methods_from_toggles, package_assets_dir, selected_extension_labels
from duplicate_verifier.models import ImageFile


def test_selected_extension_labels() -> None:
    class Toggle:
        def __init__(self, value: bool) -> None:
            self._value = value

        def get(self) -> bool:
            return self._value

    chosen = selected_extension_labels(
        {".pdf": Toggle(True), ".png": Toggle(False), ".docx": Toggle(True)}  # type: ignore[arg-type]
    )
    assert chosen == frozenset({".pdf", ".docx"})


def test_trash_progress_callback(tmp_path: Path, monkeypatch) -> None:
    seen: list[tuple[int, int]] = []
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "b.txt").write_text("y")

    def fake_send2trash(path: str) -> None:
        Path(path).unlink()

    monkeypatch.setattr("duplicate_verifier.actions.send2trash", fake_send2trash)
    files = [
        ImageFile(path=tmp_path / "a.txt", size_bytes=1),
        ImageFile(path=tmp_path / "b.txt", size_bytes=1),
    ]
    result = send_marked_to_trash(files, on_progress=lambda done, total: seen.append((done, total)))
    assert result.deleted == 2
    assert seen == [(1, 2), (2, 2)]


def test_package_assets_dir_contains_icon() -> None:
    assets = package_assets_dir()
    assert (assets / "dupcheck-icon-png.ico").is_file()
    assert (assets / "dupcheck-icon-png.png").is_file()


def test_windows_packaging_scripts_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "installer" / "dupcheck.spec").is_file()
    assert (root / "installer" / "dupcheck.iss").is_file()
    assert (root / "installer" / "build_windows.py").is_file()

