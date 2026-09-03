from pathlib import Path

from duplicate_verifier.actions import send_marked_to_trash
from duplicate_verifier.gui import methods_from_toggles
from duplicate_verifier.models import ImageFile


def test_methods_from_toggles() -> None:
    assert methods_from_toggles(exact=True, visual=True) == ("exact", "visual")
    assert methods_from_toggles(exact=True, visual=False) == ("exact",)
    assert methods_from_toggles(exact=False, visual=True) == ("visual",)
    assert methods_from_toggles(exact=False, visual=False) == ()


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
