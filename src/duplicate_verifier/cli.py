from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from send2trash import send2trash

from duplicate_verifier import __version__
from duplicate_verifier.constants import DEFAULT_HAMMING_THRESHOLD, IMAGE_EXTENSIONS
from duplicate_verifier.estimate import estimate_seconds, format_bytes, format_duration
from duplicate_verifier.models import AnalysisResult, DuplicateGroup, GroupKind, ImageFile, ScanStats
from duplicate_verifier.pipeline import analyze, default_workers
from duplicate_verifier.plan import clear_plan, load_plan, planned_files, save_plan
from duplicate_verifier.scanner import scan_images

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)
    use_color = _should_color(args.no_color)

    if args.directory is None:
        if args.delete:
            return _apply_saved_plan(yes=args.yes, use_color=use_color)
        print("Informe o diretório a analisar. Exemplo: dupcheck \"C:\\Fotos\"", file=sys.stderr)
        return 2

    root = Path(args.directory).expanduser()
    if not root.exists() or not root.is_dir():
        print(f"Diretório inválido: {root}", file=sys.stderr)
        return 1

    stats = scan_images(
        root,
        follow_symlinks=args.follow_symlinks,
        include_hidden=args.include_hidden,
    )
    _print_inventory(stats, exact_only=args.exact_only, use_color=use_color)

    if stats.total_files == 0:
        print("Nenhuma imagem encontrada.")
        save_plan(root, AnalysisResult(groups=[], failed=[], unique_contents=0, elapsed_seconds=0))
        return 0

    if not args.yes and not _confirm("Continuar com a análise?", default_yes=True):
        print("Cancelado.")
        return 0

    try:
        result = analyze(
            stats.files,
            threshold=args.threshold,
            exact_only=args.exact_only,
            workers=args.workers,
            progress=not args.quiet,
        )
    except KeyboardInterrupt:
        print("\nCancelado.", file=sys.stderr)
        return 130

    _print_report(stats, result, use_color=use_color)
    save_plan(stats.root, result)

    to_delete = [item for group in result.groups for item in group.delete]
    if not args.delete:
        _print_plan_hint(len(to_delete))
        return 0

    return _trash_files(to_delete, yes=args.yes)


def _apply_saved_plan(*, yes: bool, use_color: bool) -> int:
    plan = load_plan()
    if plan is None:
        print(
            "Nenhum plano salvo. Analise uma pasta primeiro, por exemplo:\n"
            "  dupcheck \"C:\\Fotos\"",
            file=sys.stderr,
        )
        return 1

    files = planned_files(plan)
    root = plan.get("root", "?")
    print()
    print(f"Última análise: {root}")
    if not files:
        print("O plano não tem arquivos marcados para a lixeira.")
        return 0

    print(f"Arquivos marcados: {len(files)} ({format_bytes(sum(item.size_bytes for item in files))})")
    for item in files:
        print(f"  {RED + 'DELETAR' + RESET if use_color else 'DELETAR'}  {item.path}")
    print()
    return _trash_files(files, yes=yes)


def _trash_files(to_delete: list[ImageFile], *, yes: bool) -> int:
    if not to_delete:
        print("Nenhum arquivo para enviar à lixeira.")
        return 0

    print(
        f"Serão enviados à lixeira {len(to_delete)} arquivo(s) "
        f"({format_bytes(sum(item.size_bytes for item in to_delete))})."
    )
    if not yes and not _confirm("Enviar as cópias para a lixeira?", default_yes=False):
        print("Nenhum arquivo foi movido.")
        return 0

    failures = 0
    skipped = 0
    for item in to_delete:
        target = item.path
        if not target.is_file():
            print(f"Já não existe, ignorado: {target}")
            skipped += 1
            continue
        try:
            current_size = target.stat().st_size
        except OSError as exc:
            print(f"Falha ao ler {target}: {exc}", file=sys.stderr)
            failures += 1
            continue
        if item.size_bytes and current_size != item.size_bytes:
            print(f"Tamanho mudou desde a análise, ignorado: {target}")
            skipped += 1
            continue
        try:
            send2trash(str(target))
        except Exception as exc:  # noqa: BLE001 - I/O and trash backend errors
            print(f"Falha ao enviar {target} à lixeira: {exc}", file=sys.stderr)
            failures += 1

    deleted = len(to_delete) - failures - skipped
    print(f"Enviados à lixeira: {deleted}. Ignorados: {skipped}. Falhas: {failures}.")
    if failures == 0:
        clear_plan()
    return 1 if failures else 0


def _print_plan_hint(marked: int) -> None:
    print(f"Plano salvo ({marked} arquivo(s) marcado(s) para a lixeira).")
    print("Nenhum arquivo foi movido.")
    print("Para enviar as cópias à lixeira sem analisar de novo:")
    print("  dupcheck --delete")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dupcheck",
        description=(
            "Encontra imagens duplicadas (idênticas ou visualmente iguais) "
            "em um diretório e nas subpastas. Por padrão apenas simula a remoção "
            "e grava um plano. Depois use dupcheck --delete para enviar à lixeira."
        ),
    )
    parser.add_argument(
        "directory",
        nargs="?",
        help="Diretório raiz a ser analisado (omitido com --delete para usar o último plano)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Envia à lixeira as cópias do último plano (ou analisa e apaga se houver diretório)",
    )
    parser.add_argument(
        "--exact-only",
        action="store_true",
        help="Compara só o conteúdo byte a byte (SHA-256), sem hash perceptual",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_HAMMING_THRESHOLD,
        metavar="N",
        help=(
            "Distância de Hamming máxima para considerar duas imagens iguais "
            f"(padrão: {DEFAULT_HAMMING_THRESHOLD}; maior = mais permissivo)"
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=default_workers(),
        help="Processos paralelos para hashing (padrão: até 8 núcleos)",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Não pergunta confirmação (análise e, se --delete, remoção)",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Inclui arquivos e pastas que começam com ponto",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Segue atalhos/symlinks (desligado por padrão)",
    )
    parser.add_argument("--quiet", action="store_true", help="Oculta barras de progresso")
    parser.add_argument("--no-color", action="store_true", help="Desliga cores no terminal")
    parser.add_argument("--version", action="version", version=f"dupcheck {__version__}")
    return parser


def _print_inventory(stats: ScanStats, *, exact_only: bool, use_color: bool) -> None:
    estimated = estimate_seconds(stats.total_files, stats.total_bytes, exact_only=exact_only)
    dim = DIM if use_color else ""
    reset = RESET if use_color else ""

    print()
    print(f"Diretório: {stats.root}")
    print(f"Imagens encontradas: {stats.total_files}")
    print(f"Tamanho total: {format_bytes(stats.total_bytes)}")
    if stats.extension_counts:
        parts = [
            f"{ext} ({count})"
            for ext, count in sorted(stats.extension_counts.items(), key=lambda item: -item[1])
        ]
        print(f"Extensões: {', '.join(parts)}")
    if stats.permission_errors:
        print(f"Avisos: {stats.permission_errors} itens sem permissão de leitura")
    print()
    print(f"Tempo estimado de execução: {format_duration(estimated)}")
    print(f"{dim}  (estimativa conservadora; o tempo real aparece ao final){reset}")
    print()
    known = ", ".join(sorted(IMAGE_EXTENSIONS))
    print(f"{dim}Formatos nesta versão: {known}{reset}")
    print()


def _print_report(stats: ScanStats, result: AnalysisResult, *, use_color: bool) -> None:
    redundant = sum(len(group.delete) for group in result.groups)
    reclaimable = sum(group.reclaimable_bytes for group in result.groups)
    print()
    print(
        f"Análise concluída em {format_duration(result.elapsed_seconds)} "
        f"({result.unique_contents} conteúdo(s) único(s) por hash)."
    )
    print(
        f"{len(result.groups)} grupo(s) de duplicatas | "
        f"{redundant} arquivo(s) redundante(s) | "
        f"{format_bytes(reclaimable)} recuperáveis"
    )
    print()

    if not result.groups:
        print("Nenhuma duplicata encontrada.")
    else:
        for index, group in enumerate(result.groups, start=1):
            _print_group(index, group, stats.root, use_color=use_color)
            print()

    if result.failed:
        print(f"Arquivos ignorados ({len(result.failed)}):")
        for image in result.failed:
            reason = image.error or "não foi possível processar"
            print(f"  - {_rel(image.path, stats.root)}: {reason}")
        print()


def _print_group(index: int, group: DuplicateGroup, root: Path, *, use_color: bool) -> None:
    if group.kind is GroupKind.EXACT:
        title = "duplicatas exatas (mesmo conteúdo)"
    else:
        title = f"duplicatas visuais (distância perceptual até {group.max_hamming})"
    print(f"Grupo {index} — {title}")
    _print_file_line(group.keep, root, keep=True, use_color=use_color)
    for item in group.delete:
        _print_file_line(item, root, keep=False, use_color=use_color)


def _print_file_line(image, root: Path, *, keep: bool, use_color: bool) -> None:
    label = "MANTER " if keep else "DELETAR"
    if use_color:
        label = f"{GREEN}MANTER {RESET}" if keep else f"{RED}DELETAR{RESET}"
    dims = f"{image.width}x{image.height}" if image.width and image.height else "?x?"
    print(
        f"  {label}  {_rel(image.path, root):<60}  "
        f"{dims:>12}  {format_bytes(image.size_bytes):>10}"
    )


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError, ValueError):
            pass


def _confirm(question: str, *, default_yes: bool) -> bool:
    hint = "[S/n]" if default_yes else "[s/N]"
    try:
        answer = input(f"{question} {hint} ").strip().lower()
    except EOFError:
        return default_yes
    if not answer:
        return default_yes
    return answer in {"s", "sim", "y", "yes"}


def _should_color(no_color: bool) -> bool:
    if no_color or os_name_is_dumb():
        return False
    return sys.stdout.isatty()


def os_name_is_dumb() -> bool:
    return os.environ.get("NO_COLOR") is not None or os.environ.get("TERM") == "dumb"


if __name__ == "__main__":
    sys.exit(main())
