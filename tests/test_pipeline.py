from __future__ import annotations

from pathlib import Path

from tests.helpers import save_image, scene_keep, scene_other

from duplicate_verifier.pipeline import analyze
from duplicate_verifier.scanner import scan_images


def test_pipeline_keeps_higher_quality_visual_duplicate(tmp_path: Path) -> None:
    original = tmp_path / "original.png"
    compressed = tmp_path / "copy.jpg"
    other = tmp_path / "other.png"
    save_image(original, scene_keep(320))
    save_image(compressed, scene_keep(160), quality=30)
    save_image(other, scene_other(320))

    stats = scan_images(tmp_path)
    result = analyze(stats.files, workers=1, progress=False)

    assert len(result.groups) == 1
    group = result.groups[0]
    assert group.keep.path.name == "original.png"
    assert [item.path.name for item in group.delete] == ["copy.jpg"]


def test_pipeline_detects_byte_identical_copies(tmp_path: Path) -> None:
    source = tmp_path / "a.png"
    clone = tmp_path / "sub" / "a copy.png"
    clone.parent.mkdir()
    save_image(source, scene_keep(80))
    clone.write_bytes(source.read_bytes())

    stats = scan_images(tmp_path)
    result = analyze(stats.files, workers=1, progress=False, exact_only=True)

    assert len(result.groups) == 1
    names = {item.path.name for item in result.groups[0].files}
    assert names == {"a.png", "a copy.png"}
