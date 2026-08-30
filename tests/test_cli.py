from __future__ import annotations

from pathlib import Path

from tests.helpers import save_image, scene_keep, scene_other

from duplicate_verifier.cli import main


def test_cli_dry_run_reports_visual_duplicate(tmp_path: Path, capsys) -> None:
    save_image(tmp_path / "original.png", scene_keep(320))
    save_image(tmp_path / "copy.jpg", scene_keep(160), quality=30)
    save_image(tmp_path / "other.png", scene_other(320))

    code = main([str(tmp_path), "-y", "--no-color", "--quiet", "--workers", "1"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Imagens encontradas: 3" in out
    assert "Tempo estimado de execução:" in out
    assert "MANTER" in out
    assert "DELETAR" in out
    assert "original.png" in out
    assert "copy.jpg" in out
    assert "Modo simulação" in out
    assert (tmp_path / "copy.jpg").exists()
