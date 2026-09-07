from __future__ import annotations

from pathlib import Path

from duplicate_verifier.models import AnalysisResult, DuplicateGroup, GroupKind, ImageFile
from duplicate_verifier.plan import load_plan, planned_files, save_plan


def test_save_and_load_plan(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DUPCHECK_PLAN", str(tmp_path / "plan.json"))
    keep = ImageFile(path=tmp_path / "keep.png", size_bytes=10)
    dump = ImageFile(path=tmp_path / "dump.jpg", size_bytes=4)
    result = AnalysisResult(
        groups=[DuplicateGroup(kind=GroupKind.VISUAL, keep=[keep], delete=[dump])],
        failed=[],
        unique_contents=2,
        elapsed_seconds=0.1,
    )
    save_plan(tmp_path, result)
    plan = load_plan()
    assert plan is not None
    files = planned_files(plan)
    assert len(files) == 1
    assert files[0].path.name == "dump.jpg"
    assert files[0].size_bytes == 4
