from __future__ import annotations

from pathlib import Path

from duplicate_verifier.estimate import estimate_seconds, format_bytes, format_duration
from duplicate_verifier.grouping import cluster_hashes
from duplicate_verifier.hashing import hamming_distance
from duplicate_verifier.models import ImageFile
from duplicate_verifier.quality import pick_keep
from duplicate_verifier.scanner import scan_images


def test_format_duration_and_bytes() -> None:
    assert format_duration(0.2) == "menos de 1 s"
    assert format_duration(12) == "12 s"
    assert format_duration(80) == "1 min 20 s"
    assert format_bytes(500) == "500 B"
    assert format_bytes(2048).endswith("KB")


def test_estimate_is_lower_without_phash() -> None:
    full = estimate_seconds(100, 50 * 1024 * 1024, exact_only=False)
    exact = estimate_seconds(100, 50 * 1024 * 1024, exact_only=True)
    assert full > exact > 0


def test_pick_keep_prefers_higher_resolution() -> None:
    low = ImageFile(path=Path("small.jpg"), size_bytes=800_000, width=800, height=600, format="JPEG")
    high = ImageFile(path=Path("big.png"), size_bytes=400_000, width=1920, height=1080, format="PNG")
    keep, delete = pick_keep([low, high])
    assert keep is high
    assert delete == [low]


def test_pick_keep_prefers_larger_file_when_resolution_ties() -> None:
    compressed = ImageFile(
        path=Path("a.jpg"), size_bytes=100_000, width=1000, height=1000, format="JPEG"
    )
    original = ImageFile(
        path=Path("b.jpg"), size_bytes=400_000, width=1000, height=1000, format="JPEG"
    )
    keep, delete = pick_keep([compressed, original])
    assert keep is original
    assert delete == [compressed]


def test_cluster_identical_and_near_hashes() -> None:
    hashes = [0, 0, 1, 0xFFFFFFFFFFFFFFFF]
    clustered = cluster_hashes(hashes, threshold=1)
    by_index = {i: next(group for group in clustered if i in group) for i in range(4)}
    assert set(by_index[0]) == {0, 1, 2}
    assert by_index[3] == [3]


def test_hamming_distance() -> None:
    assert hamming_distance(0b1010, 0b1000) == 1
    assert hamming_distance(0, 0) == 0


def test_scanner_finds_nested_images(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "photo.jpg").write_bytes(b"not-a-real-image-but-has-size")
    (tmp_path / "notes.txt").write_text("ignore")
    (tmp_path / ".hidden.png").write_bytes(b"secret")
    stats = scan_images(tmp_path)
    assert stats.total_files == 1
    assert stats.files[0].path.name == "photo.jpg"
