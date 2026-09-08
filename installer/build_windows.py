"""Build the Windows onedir bundle and, when Inno Setup is available, the installer."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "installer" / "dupcheck.spec"
ISS = ROOT / "installer" / "dupcheck.iss"
VERSION_FILE = ROOT / "src" / "duplicate_verifier" / "__init__.py"
BUNDLE_DIR = ROOT / "dist" / "dupcheck"
GUI_EXE = BUNDLE_DIR / "dupcheck.exe"
CLI_EXE = BUNDLE_DIR / "dupcheck-cli.exe"

ISCC_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
    Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe",
)


def app_version() -> str:
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise SystemExit(f"Não achei __version__ em {VERSION_FILE}")
    return match.group(1)


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def find_iscc() -> Path | None:
    found = shutil.which("ISCC") or shutil.which("ISCC.exe")
    if found:
        return Path(found)
    for candidate in ISCC_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def ensure_pyinstaller() -> Path:
    exe = Path(sys.executable).parent / "pyinstaller.exe"
    if exe.is_file():
        return exe
    run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"])
    if exe.is_file():
        return exe
    return Path(sys.executable)


def build_bundle(*, clean: bool) -> None:
    pyinstaller = ensure_pyinstaller()
    cmd = [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm"]
    if clean:
        cmd.append("--clean")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True, env=env)
    if not GUI_EXE.is_file() or not CLI_EXE.is_file():
        raise SystemExit(f"PyInstaller não gerou os executáveis em {BUNDLE_DIR}")
    print(f"Pasta do app: {BUNDLE_DIR}")
    verify_bundle()


def verify_bundle() -> None:
    """Fail the build if the frozen CLI cannot import bundled dependencies."""
    result = subprocess.run(
        [str(CLI_EXE), "--version"],
        cwd=BUNDLE_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise SystemExit(
            "O exe congelado falhou no --version (dependência em falta?):\n" + output
        )
    print(output.strip() or "dupcheck-cli --version ok")


def build_installer(version: str) -> Path:
    iscc = find_iscc()
    if iscc is None:
        print(
            "Inno Setup não encontrado. O bundle em dist/dupcheck já está pronto.\n"
            "Para gerar o instalador:\n"
            "  winget install JRSoftware.InnoSetup\n"
            "Depois rode de novo: python installer/build_windows.py --skip-bundle"
        )
        raise SystemExit(2)
    output = ROOT / "dist" / f"dupcheck-setup-{version}.exe"
    run(
        [
            str(iscc),
            f"/DMyAppVersion={version}",
            str(ISS),
        ]
    )
    if not output.is_file():
        raise SystemExit(f"ISCC terminou mas não achei {output}")
    print(f"Instalador: {output}")
    return output


def main(argv: list[str] | None = None) -> int:
    if sys.platform != "win32":
        print("Este build é só para Windows.", file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description="Gera dupcheck.exe e o instalador Inno Setup.")
    parser.add_argument("--skip-installer", action="store_true", help="Só roda o PyInstaller")
    parser.add_argument("--skip-bundle", action="store_true", help="Só compila o Inno Setup (dist/dupcheck já existe)")
    parser.add_argument("--no-clean", action="store_true", help="Não passa --clean ao PyInstaller")
    args = parser.parse_args(argv)
    version = app_version()
    print(f"Versão: {version}")
    if not args.skip_bundle:
        build_bundle(clean=not args.no_clean)
    elif not GUI_EXE.is_file() or not CLI_EXE.is_file():
        raise SystemExit(f"Falta o bundle em {BUNDLE_DIR}. Rode sem --skip-bundle.")
    if args.skip_installer:
        return 0
    try:
        build_installer(version)
    except SystemExit as exc:
        if exc.code == 2:
            return 2
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
