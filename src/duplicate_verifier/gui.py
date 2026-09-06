from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from duplicate_verifier.actions import send_marked_to_trash
from duplicate_verifier.constants import (
    DEFAULT_HAMMING_THRESHOLD,
    METHOD_EXACT,
    METHOD_VISUAL,
    PHASH_BITS,
    is_image_path,
)
from duplicate_verifier.estimate import estimate_seconds, format_bytes, format_duration
from duplicate_verifier.models import AnalysisResult, DuplicateGroup, GroupKind, ImageFile, ScanStats
from duplicate_verifier.pipeline import analyze
from duplicate_verifier.plan import save_plan
from duplicate_verifier.scanner import filter_files_by_extensions, scan_files


def selected_extension_labels(ext_vars: dict[str, tk.BooleanVar]) -> frozenset[str]:
    return frozenset(ext for ext, var in ext_vars.items() if var.get())


def methods_from_toggles(*, exact: bool, visual: bool) -> tuple[str, ...]:
    selected: list[str] = []
    if exact:
        selected.append(METHOD_EXACT)
    if visual:
        selected.append(METHOD_VISUAL)
    return tuple(selected)


def windows_explorer_select_args(path: Path) -> list[str]:
    """Build Explorer argv so a drive like ``E:\\file`` is not treated as relative.

    ``explorer /select,E:\\folder\\file.jpg`` as one argument is parsed as a
    path under the user Documents folder. ``/select,`` must be its own argv.
    """
    return ["explorer.exe", "/select,", os.path.normpath(path)]


def reveal_in_file_manager(path: Path) -> None:
    """Open the file manager with ``path`` selected, when the OS supports it."""
    target = path.expanduser().resolve()
    if sys.platform == "win32":
        if target.exists():
            subprocess.Popen(windows_explorer_select_args(target))
            return
        folder = target.parent if target.parent.exists() else target
        os.startfile(os.path.normpath(folder))  # noqa: S606
        return
    if sys.platform == "darwin":
        if target.exists():
            subprocess.Popen(["open", "-R", str(target)])
        else:
            subprocess.Popen(["open", str(target.parent)])
        return
    folder = target.parent if target.is_file() else target
    subprocess.Popen(["xdg-open", str(folder)])


def run_app(initial_directory: str | Path | None = None) -> int:
    app = DupcheckApp(initial_directory=initial_directory)
    app.mainloop()
    return 0


def run_app_main() -> None:
    raise SystemExit(run_app())


class DupcheckApp(tk.Tk):
    def __init__(self, initial_directory: str | Path | None = None) -> None:
        super().__init__()
        self.title("dupcheck — verificador de duplicatas")
        self.minsize(920, 560)
        self.geometry("1000x640")

        self._busy = False
        self._stats: ScanStats | None = None
        self._result: AnalysisResult | None = None

        self.folder_var = tk.StringVar(value=str(initial_directory or ""))
        self.scope_var = tk.StringVar(value="images")
        self.exact_var = tk.BooleanVar(value=True)
        self.visual_var = tk.BooleanVar(value=True)
        self.threshold_var = tk.IntVar(value=DEFAULT_HAMMING_THRESHOLD)
        self.status_var = tk.StringVar(value="Escolha uma pasta e clique em Analisar.")
        self._preview_stats: ScanStats | None = None
        self._preview_seq = 0
        self.preview_var = tk.StringVar(value="Selecione uma pasta para ver o total de arquivos e o tempo estimado.")
        self.trash_count_var = tk.StringVar(value="")
        self._ext_vars: dict[str, tk.BooleanVar] = {}

        self._build()
        self._sync_threshold_state()
        if self.folder_var.get().strip():
            self._start_preview()

    def _build(self) -> None:
        pad = {"padx": 8, "pady": 4}
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Pasta:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(top, textvariable=self.folder_var).grid(row=0, column=1, sticky=tk.EW, **pad)
        ttk.Button(top, text="Procurar…", command=self._choose_folder).grid(row=0, column=2, **pad)
        top.columnconfigure(1, weight=1)

        options = ttk.LabelFrame(self, text="Opções (iguais ao terminal)", padding=10)
        options.pack(fill=tk.X, padx=10, pady=(0, 6))

        ttk.Label(options, text="Escopo:").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(
            options, text="Só imagens", variable=self.scope_var, value="images", command=self._start_preview
        ).grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Radiobutton(
            options,
            text="Todos os arquivos (PDF, DOCX, etc. — só no SHA-256)",
            variable=self.scope_var,
            value="all",
            command=self._start_preview,
        ).grid(row=0, column=2, sticky=tk.W, padx=6)

        ttk.Label(options, text="Métodos:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Checkbutton(
            options,
            text="Cópias exatas (SHA-256)",
            variable=self.exact_var,
            command=self._refresh_preview_estimate,
        ).grid(row=1, column=1, sticky=tk.W, padx=6, pady=(8, 0))
        visual = ttk.Checkbutton(
            options,
            text="Cópias visuais (pHash, só imagens)",
            variable=self.visual_var,
            command=self._on_visual_toggle,
        )
        visual.grid(row=1, column=2, sticky=tk.W, padx=6, pady=(8, 0))

        ttk.Label(options, text="Distância visual:").grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        self.threshold_spin = ttk.Spinbox(
            options,
            from_=0,
            to=PHASH_BITS,
            textvariable=self.threshold_var,
            width=6,
        )
        self.threshold_spin.grid(row=2, column=1, sticky=tk.W, padx=6, pady=(8, 0))
        ttk.Label(
            options,
            text="0 = imagens iguais;  1 = imagens muito parecidas;  2 = imagens um pouco parecidas",
        ).grid(row=2, column=2, sticky=tk.W, padx=6, pady=(8, 0))

        ttk.Label(options, text="Extensões:").grid(row=3, column=0, sticky=tk.W, pady=(8, 0))
        self.ext_menu_btn = ttk.Menubutton(options, text="Selecione uma pasta", state=tk.DISABLED)
        self.ext_menu = tk.Menu(self.ext_menu_btn, tearoff=0)
        self.ext_menu_btn["menu"] = self.ext_menu
        self.ext_menu_btn.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=6, pady=(8, 0))

        buttons = ttk.Frame(self, padding=(10, 0))
        buttons.pack(fill=tk.X)
        self.analyze_btn = ttk.Button(buttons, text="Analisar", command=self._start_analysis)
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.trash_btn = ttk.Button(
            buttons, text="Enviar cópias à lixeira", command=self._confirm_trash, state=tk.DISABLED
        )
        self.trash_btn.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(buttons, textvariable=self.preview_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(buttons, textvariable=self.trash_count_var).pack(side=tk.RIGHT, padx=(8, 0))
        self.progress = ttk.Progressbar(buttons, mode="indeterminate", length=180)
        self.progress.pack(side=tk.RIGHT)

        self.summary = ttk.Label(self, text="", padding=(10, 6), justify=tk.LEFT)
        self.summary.pack(fill=tk.X)

        table_frame = ttk.Frame(self, padding=(10, 0, 10, 4))
        table_frame.pack(fill=tk.BOTH, expand=True)
        columns = ("grupo", "acao", "arquivo", "tipo", "detalhe", "tamanho")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "grupo": "Grupo",
            "acao": "Ação",
            "arquivo": "Arquivo",
            "tipo": "Tipo",
            "detalhe": "Detalhe",
            "tamanho": "Tamanho",
        }
        widths = {"grupo": 70, "acao": 80, "arquivo": 480, "tipo": 90, "detalhe": 110, "tamanho": 90}
        for key, title in headings.items():
            self.tree.heading(key, text=title)
            self.tree.column(key, width=widths[key], stretch=key == "arquivo")
        scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.tag_configure("keep", foreground="#0a7a28")
        self.tree.tag_configure("delete", foreground="#b42318")
        self.tree.bind("<Double-1>", self._open_selected)

        ttk.Label(self, textvariable=self.status_var, padding=(10, 6)).pack(fill=tk.X)

    def _on_visual_toggle(self) -> None:
        self._sync_threshold_state()
        self._refresh_preview_estimate()

    def _sync_threshold_state(self) -> None:
        state = tk.NORMAL if self.visual_var.get() else tk.DISABLED
        self.threshold_spin.configure(state=state)

    def _choose_folder(self) -> None:
        current = self.folder_var.get().strip()
        chosen = filedialog.askdirectory(initialdir=current or None, title="Pasta para analisar")
        if chosen:
            self.folder_var.set(chosen)
            self._start_preview()

    def _start_preview(self) -> None:
        if self._busy:
            return
        folder = self.folder_var.get().strip()
        if not folder:
            self._preview_stats = None
            self._rebuild_extension_menu({})
            self.preview_var.set("Selecione uma pasta para ver o total de arquivos e o tempo estimado.")
            return
        root = Path(folder)
        if not root.is_dir():
            self._preview_stats = None
            self._rebuild_extension_menu({})
            self.preview_var.set("Pasta inválida.")
            return
        all_files = self.scope_var.get() == "all"
        self._preview_seq += 1
        seq = self._preview_seq
        self.preview_var.set("Contando arquivos…")

        def work() -> None:
            try:
                stats = scan_files(root, all_files=all_files)
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda error=exc, token=seq: self._on_preview_error(token, error))
                return
            self.after(0, lambda token=seq: self._on_preview_done(token, stats))

        threading.Thread(target=work, daemon=True).start()

    def _on_preview_error(self, token: int, error: Exception) -> None:
        if token != self._preview_seq:
            return
        self.preview_var.set(f"Não foi possível listar a pasta: {error}")

    def _on_preview_done(self, token: int, stats: ScanStats) -> None:
        if token != self._preview_seq:
            return
        self._preview_stats = stats
        self._rebuild_extension_menu(stats.extension_counts)
        self._refresh_preview_estimate()

    def _rebuild_extension_menu(self, counts: dict[str, int]) -> None:
        previous = {ext: var.get() for ext, var in self._ext_vars.items()}
        self.ext_menu.delete(0, tk.END)
        self._ext_vars = {}
        if not counts:
            self.ext_menu.add_command(label="Nenhuma extensão encontrada", state=tk.DISABLED)
            self.ext_menu_btn.configure(text="Nenhuma extensão", state=tk.DISABLED)
            return
        self.ext_menu.add_command(label="Marcar todas", command=self._select_all_extensions)
        self.ext_menu.add_command(label="Desmarcar todas", command=self._clear_all_extensions)
        self.ext_menu.add_separator()
        for ext, count in sorted(counts.items(), key=lambda item: item[0].lower()):
            var = tk.BooleanVar(value=previous.get(ext, True))
            self._ext_vars[ext] = var
            self.ext_menu.add_checkbutton(
                label=f"{ext}  ({count})",
                variable=var,
                command=self._on_extension_toggle,
            )
        self.ext_menu_btn.configure(state=tk.NORMAL)
        self._update_ext_button_label()

    def _select_all_extensions(self) -> None:
        for var in self._ext_vars.values():
            var.set(True)
        self._on_extension_toggle()

    def _clear_all_extensions(self) -> None:
        for var in self._ext_vars.values():
            var.set(False)
        self._on_extension_toggle()

    def _on_extension_toggle(self) -> None:
        self._update_ext_button_label()
        self._refresh_preview_estimate()

    def _update_ext_button_label(self) -> None:
        total = len(self._ext_vars)
        if total == 0:
            self.ext_menu_btn.configure(text="Nenhuma extensão")
            return
        selected = selected_extension_labels(self._ext_vars)
        if len(selected) == total:
            self.ext_menu_btn.configure(text=f"Todas ({total})")
            return
        if not selected:
            self.ext_menu_btn.configure(text="Nenhuma selecionada")
            return
        preview = ", ".join(sorted(selected)[:4])
        extra = "" if len(selected) <= 4 else f" +{len(selected) - 4}"
        self.ext_menu_btn.configure(text=f"{preview}{extra}  ({len(selected)}/{total})")

    def _selected_files_for_preview(self) -> list[ImageFile]:
        stats = self._preview_stats
        if stats is None:
            return []
        allowed = selected_extension_labels(self._ext_vars)
        if not self._ext_vars:
            return list(stats.files)
        return filter_files_by_extensions(stats.files, allowed)

    def _refresh_preview_estimate(self) -> None:
        stats = self._preview_stats
        if stats is None:
            return
        files = self._selected_files_for_preview()
        total_bytes = sum(item.size_bytes for item in files)
        methods = methods_from_toggles(exact=self.exact_var.get(), visual=self.visual_var.get())
        include_visual = METHOD_VISUAL in methods
        image_count = sum(1 for item in files if is_image_path(item.path))
        estimated = estimate_seconds(
            len(files),
            total_bytes,
            include_visual=include_visual,
            visual_count=image_count if include_visual else 0,
        )
        noun = "arquivo(s)" if self.scope_var.get() == "all" else "imagem(ns)"
        self.preview_var.set(
            f"{len(files)} {noun}  |  {format_bytes(total_bytes)}  |  "
            f"tempo estimado: {format_duration(estimated)}"
        )

    def _start_analysis(self) -> None:
        if self._busy:
            return
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Pasta", "Escolha o diretório que deseja analisar.")
            return
        root = Path(folder)
        if not root.is_dir():
            messagebox.showerror("Pasta inválida", f"Não é um diretório:\n{root}")
            return
        methods = methods_from_toggles(exact=self.exact_var.get(), visual=self.visual_var.get())
        if not methods:
            messagebox.showwarning("Métodos", "Marque pelo menos um método: exatas e/ou visuais.")
            return
        try:
            threshold = int(self.threshold_var.get())
        except (tk.TclError, ValueError):
            threshold = DEFAULT_HAMMING_THRESHOLD
        threshold = max(0, min(PHASH_BITS, threshold))
        all_files = self.scope_var.get() == "all"
        allowed = selected_extension_labels(self._ext_vars)
        if self._ext_vars and not allowed:
            messagebox.showwarning("Extensões", "Marque pelo menos uma extensão para analisar.")
            return

        self._busy = True
        self.analyze_btn.configure(state=tk.DISABLED)
        self.trash_btn.configure(state=tk.DISABLED)
        self.trash_count_var.set("")
        self.progress.start(12)
        self.status_var.set("Analisando… a janela pode levar um tempo em pastas grandes.")
        self.summary.configure(text="")
        self._clear_table()

        def work() -> None:
            try:
                stats = scan_files(
                    root,
                    all_files=all_files,
                    allowed_extensions=allowed or None,
                )
                result = analyze(
                    stats.files,
                    threshold=threshold,
                    methods=methods,
                    workers=1,
                    progress=False,
                )
                save_plan(stats.root, result)
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda error=exc: self._on_analysis_error(error))
                return
            self.after(0, lambda: self._on_analysis_done(stats, result))

        threading.Thread(target=work, daemon=True).start()

    def _on_analysis_error(self, error: Exception) -> None:
        self._finish_busy()
        self.status_var.set("A análise falhou.")
        messagebox.showerror("Erro na análise", str(error))

    def _on_analysis_done(self, stats: ScanStats, result: AnalysisResult) -> None:
        self._stats = stats
        self._result = result
        self._preview_stats = stats
        self._refresh_preview_estimate()
        self._finish_busy()
        self._fill_table(stats, result)
        summary = _summary_text(stats, result)
        self.summary.configure(text=summary)
        marked = result.reclaimable_count()
        self.trash_btn.configure(state=tk.NORMAL if marked else tk.DISABLED)
        if stats.total_files == 0:
            self.status_var.set("Nenhum arquivo encontrado nesse escopo.")
        elif marked == 0:
            self.status_var.set(
                f"Concluído em {format_duration(result.elapsed_seconds)}. Nenhuma duplicata."
            )
        else:
            self.status_var.set(
                f"Concluído em {format_duration(result.elapsed_seconds)}. "
                f"{marked} arquivo(s) marcados. Duplo clique abre a pasta com o arquivo selecionado."
            )

    def _finish_busy(self, *, clear_trash_count: bool = True) -> None:
        self._busy = False
        self.progress.stop()
        self.analyze_btn.configure(state=tk.NORMAL)
        if clear_trash_count:
            self.trash_count_var.set("")

    def _clear_table(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _fill_table(self, stats: ScanStats, result: AnalysisResult) -> None:
        self._clear_table()
        for index, group in enumerate(result.groups, start=1):
            kind = "exata" if group.kind is GroupKind.EXACT else "visual"
            self._insert_row(index, group.keep, action="MANTER", kind=kind, tag="keep", root=stats.root)
            for item in group.delete:
                self._insert_row(index, item, action="DELETAR", kind=kind, tag="delete", root=stats.root)

    def _insert_row(
        self,
        group_index: int,
        image: ImageFile,
        *,
        action: str,
        kind: str,
        tag: str,
        root: Path,
    ) -> None:
        try:
            rel = str(image.path.relative_to(root))
        except ValueError:
            rel = str(image.path)
        if image.width and image.height:
            detail = f"{image.width}x{image.height}"
        else:
            detail = image.path.suffix.lower() or "arquivo"
        self.tree.insert(
            "",
            tk.END,
            values=(group_index, action, rel, kind, detail, format_bytes(image.size_bytes)),
            tags=(tag,),
        )

    def _open_selected(self, _event: tk.Event | None = None) -> None:
        selected = self.tree.selection()
        if not selected or not self._stats:
            return
        rel = self.tree.item(selected[0], "values")[2]
        path = self._stats.root / rel
        try:
            reveal_in_file_manager(path)
        except OSError as exc:
            messagebox.showerror("Abrir pasta", str(exc))

    def _confirm_trash(self) -> None:
        if self._busy or not self._result:
            return
        to_delete = [item for group in self._result.groups for item in group.delete]
        if not to_delete:
            messagebox.showinfo("Lixeira", "Não há arquivos marcados.")
            return
        total = format_bytes(sum(item.size_bytes for item in to_delete))
        if not messagebox.askyesno(
            "Enviar à lixeira",
            f"Enviar {len(to_delete)} arquivo(s) ({total}) para a lixeira?\n"
            "Dá para restaurar pela Lixeira do Windows.",
        ):
            return

        self._busy = True
        self.analyze_btn.configure(state=tk.DISABLED)
        self.trash_btn.configure(state=tk.DISABLED)
        self.progress.start(12)
        total_files = len(to_delete)
        self.trash_count_var.set(f"0/{total_files}")
        self.status_var.set(f"Enviando à lixeira: 0/{total_files}")

        def work() -> None:
            def on_progress(done: int, total_count: int) -> None:
                self.after(0, lambda d=done, t=total_count: self._on_trash_progress(d, t))

            trash_result = send_marked_to_trash(to_delete, on_progress=on_progress)
            self.after(0, lambda: self._on_trash_done(trash_result, total_files))

        threading.Thread(target=work, daemon=True).start()

    def _on_trash_progress(self, done: int, total: int) -> None:
        self.trash_count_var.set(f"{done}/{total}")
        self.status_var.set(f"Enviando à lixeira: {done}/{total}")

    def _on_trash_done(self, result, total_files: int) -> None:
        self._finish_busy(clear_trash_count=False)
        self.trash_count_var.set(f"{result.deleted}/{total_files}")
        extra = "\n".join(result.messages[:8])
        if result.messages[8:]:
            extra += f"\n… (+{len(result.messages) - 8})"
        messagebox.showinfo(
            "Lixeira",
            f"Enviados: {result.deleted}/{total_files}\nIgnorados: {result.skipped}\nFalhas: {result.failures}"
            + (f"\n\n{extra}" if extra else ""),
        )
        if result.deleted:
            self.trash_btn.configure(state=tk.DISABLED)
            self.status_var.set(
                f"Lixeira: {result.deleted}/{total_files} enviados. "
                "Rode Analisar de novo se quiser conferir."
            )
            self._result = None
        else:
            marked = self._result.reclaimable_count() if self._result else 0
            self.trash_btn.configure(state=tk.NORMAL if marked else tk.DISABLED)
            self.status_var.set("Nenhum arquivo foi para a lixeira.")


def _summary_text(stats: ScanStats, result: AnalysisResult) -> str:
    lines = [
        f"Analisado: {format_bytes(stats.total_bytes)} ({stats.total_files} arquivo(s))",
        f"Exatas: {format_bytes(result.reclaimable_bytes(GroupKind.EXACT))} "
        f"({result.reclaimable_count(GroupKind.EXACT)} arquivo(s))",
        f"Visuais: {format_bytes(result.reclaimable_bytes(GroupKind.VISUAL))} "
        f"({result.reclaimable_count(GroupKind.VISUAL)} arquivo(s))",
        f"Total na lixeira: {format_bytes(result.reclaimable_bytes())} "
        f"({result.reclaimable_count()} arquivo(s))",
    ]
    return "   |   ".join(lines)
