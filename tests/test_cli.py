from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import save_image, scene_keep, scene_other

from duplicate_verifier.cli import main
from duplicate_verifier.plan import load_plan


@pytest.fixture(autouse=True)
def isolate_plan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUPCHECK_PLAN", str(tmp_path / "last-plan.json"))


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
    assert "Plano salvo" in out
    assert "dupcheck --delete" in out
    assert "Total recuperável:" in out
    assert "Cópias visuais" in out
    assert (tmp_path / "copy.jpg").exists()
    plan = load_plan()
    assert plan is not None
    assert len(plan["files"]) == 1


def test_cli_delete_sends_copies_to_trash(tmp_path: Path, capsys, monkeypatch) -> None:
    sent: list[str] = []

    def fake_send2trash(path: str) -> None:
        sent.append(path)
        Path(path).unlink()

    monkeypatch.setattr("duplicate_verifier.actions.send2trash", fake_send2trash)
    save_image(tmp_path / "original.png", scene_keep(320))
    save_image(tmp_path / "copy.jpg", scene_keep(160), quality=30)
    save_image(tmp_path / "other.png", scene_other(320))

    code = main(
        [str(tmp_path), "--delete", "-y", "--no-color", "--quiet", "--workers", "1"]
    )
    out = capsys.readouterr().out

    assert code == 0
    assert "Enviados à lixeira: 1" in out
    assert any(path.endswith("copy.jpg") for path in sent)
    assert (tmp_path / "original.png").exists()
    assert (tmp_path / "other.png").exists()
    assert not (tmp_path / "copy.jpg").exists()


def test_cli_delete_applies_last_plan_without_rescan(tmp_path: Path, capsys, monkeypatch) -> None:
    sent: list[str] = []

    def fake_send2trash(path: str) -> None:
        sent.append(path)
        Path(path).unlink()

    monkeypatch.setattr("duplicate_verifier.actions.send2trash", fake_send2trash)
    save_image(tmp_path / "original.png", scene_keep(320))
    save_image(tmp_path / "copy.jpg", scene_keep(160), quality=30)
    save_image(tmp_path / "other.png", scene_other(320))

    assert main([str(tmp_path), "-y", "--no-color", "--quiet", "--workers", "1"]) == 0
    capsys.readouterr()
    assert (tmp_path / "copy.jpg").exists()

    code = main(["--delete", "-y", "--no-color"])
    out = capsys.readouterr().out

    assert code == 0
    assert "Última análise:" in out
    assert "Enviados à lixeira: 1" in out
    assert any(path.endswith("copy.jpg") for path in sent)
    assert (tmp_path / "original.png").exists()
    assert not (tmp_path / "copy.jpg").exists()
    assert load_plan() is None


def test_cli_method_exact_skips_visual_match(tmp_path: Path, capsys) -> None:
    save_image(tmp_path / "original.png", scene_keep(320))
    save_image(tmp_path / "copy.jpg", scene_keep(160), quality=30)
    code = main(
        [
            str(tmp_path),
            "--method",
            "exact",
            "-y",
            "--no-color",
            "--quiet",
            "--workers",
            "1",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Nenhuma duplicata encontrada" in out
    assert "Cópias exatas" in out
    assert "Cópias visuais" not in out


def test_cli_all_files_finds_duplicate_pdf(tmp_path: Path, capsys) -> None:
    (tmp_path / "a.pdf").write_bytes(b"%PDF-same")
    (tmp_path / "b.pdf").write_bytes(b"%PDF-same")
    (tmp_path / "c.pdf").write_bytes(b"%PDF-other")
    code = main(
        [
            str(tmp_path),
            "--method",
            "exact",
            "--all-files",
            "-y",
            "--no-color",
            "--quiet",
            "--workers",
            "1",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Arquivos encontrados: 3" in out
    assert "a.pdf" in out
    assert "b.pdf" in out
    assert "Cópias exatas" in out
