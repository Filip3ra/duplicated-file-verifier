from __future__ import annotations

from pathlib import Path

from tests.helpers import save_image, scene_keep, scene_other

from duplicate_verifier.models import GroupKind
from duplicate_verifier.pipeline import analyze
from duplicate_verifier.scanner import scan_files, scan_images


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


def test_pipeline_splits_exact_and_visual_when_both_methods(tmp_path: Path) -> None:
    original = tmp_path / "original.png"
    clone = tmp_path / "original copy.png"
    compressed = tmp_path / "copy.jpg"
    other = tmp_path / "other.png"
    save_image(original, scene_keep(320))
    clone.write_bytes(original.read_bytes())
    save_image(compressed, scene_keep(160), quality=30)
    save_image(other, scene_other(320))

    stats = scan_images(tmp_path)
    result = analyze(stats.files, workers=1, progress=False, methods=["exact", "visual"])

    kinds = {group.kind for group in result.groups}
    assert GroupKind.EXACT in kinds
    assert GroupKind.VISUAL in kinds
    exact_names = {
        item.path.name
        for group in result.groups
        if group.kind is GroupKind.EXACT
        for item in group.delete
    }
    visual_names = {
        item.path.name
        for group in result.groups
        if group.kind is GroupKind.VISUAL
        for item in group.delete
    }
    assert exact_names == {"original copy.png"}
    assert visual_names == {"copy.jpg"}
    assert result.reclaimable_bytes(GroupKind.EXACT) == clone.stat().st_size
    assert result.reclaimable_bytes(GroupKind.VISUAL) == compressed.stat().st_size


def test_pipeline_exact_method_ignores_resized_jpeg(tmp_path: Path) -> None:
    save_image(tmp_path / "original.png", scene_keep(320))
    save_image(tmp_path / "copy.jpg", scene_keep(160), quality=30)
    stats = scan_images(tmp_path)
    result = analyze(stats.files, workers=1, progress=False, methods=["exact"])
    assert result.groups == []


def test_pipeline_visual_method_ignores_unique_byte_copies(tmp_path: Path) -> None:
    source = tmp_path / "a.png"
    clone = tmp_path / "a copy.png"
    save_image(source, scene_keep(80))
    clone.write_bytes(source.read_bytes())
    stats = scan_images(tmp_path)
    result = analyze(stats.files, workers=1, progress=False, methods=["visual"])
    assert result.groups == []


def test_pipeline_exact_detects_duplicate_documents(tmp_path: Path) -> None:
    original = tmp_path / "relatorio.pdf"
    clone = tmp_path / "copia.pdf"
    original.write_bytes(b"%PDF-1.4 duplicate-doc-bytes")
    clone.write_bytes(original.read_bytes())
    (tmp_path / "outro.pdf").write_bytes(b"%PDF-1.4 other-doc")
    stats = scan_files(tmp_path, all_files=True)
    result = analyze(stats.files, workers=1, progress=False, methods=["exact"])
    assert len(result.groups) == 1
    names = {item.path.name for item in result.groups[0].files}
    assert names == {"relatorio.pdf", "copia.pdf"}
