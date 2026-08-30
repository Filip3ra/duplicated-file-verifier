from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from duplicate_verifier.actions import send_marked_to_trash
from duplicate_verifier.constants import DEFAULT_HAMMING_THRESHOLD, METHOD_EXACT, METHOD_VISUAL, PHASH_BITS
from duplicate_verifier.estimate import format_bytes, format_duration
from duplicate_verifier.models import AnalysisResult, DuplicateGroup, GroupKind, ImageFile, ScanStats
from duplicate_verifier.pipeline import analyze
from duplicate_verifier.plan import save_plan
from duplicate_verifier.scanner import scan_files


def methods_from_toggles(*, exact: bool, visual: bool) -> tuple[str, ...]:
    selected: list[str] = []
    if exact:
        selected.append(METHOD_EXACT)
    if visual:
        selected.append(METHOD_VISUAL)
    return tuple(selected)


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

        self._build()
        self._sync_threshold_state()

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
            options, text="Só imagens", variable=self.scope_var, value="images"
        ).grid(row=0, column=1, sticky=tk.W, padx=6)
        ttk.Radiobutton(
            options,
            text="Todos os arquivos (PDF, DOCX, etc. — só no SHA-256)",
            variable=self.scope_var,
            value="all",
        ).grid(row=0, column=2, sticky=tk.W, padx=6)

        ttk.Label(options, text="Métodos:").grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Checkbutton(
            options,
            text="Cópias exatas (SHA-256)",
            variable=self.exact_var,
        ).grid(row=1, column=1, sticky=tk.W, padx=6, pady=(8, 0))
        visual = ttk.Checkbutton(
            options,
            text="Cópias visuais (pHash, só imagens)",
            variable=self.visual_var,
            command=self._sync_threshold_state,
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
            text="0 = hashes iguais; padrão 8; maior = mais permissivo",
        ).grid(row=2, column=2, sticky=tk.W, padx=6, pady=(8, 0))

        buttons = ttk.Frame(self, padding=(10, 0))
        buttons.pack(fill=tk.X)
        self.analyze_btn = ttk.Button(buttons, text="Analisar", command=self._start_analysis)
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.trash_btn = ttk.Button(
            buttons, text="Enviar cópias à lixeira", command=self._confirm_trash, state=tk.DISABLED
        )
        self.trash_btn.pack(side=tk.LEFT)
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

    def _sync_threshold_state(self) -> None:
        state = tk.NORMAL if self.visual_var.get() else tk.DISABLED
        self.threshold_spin.configure(state=state)

    def _choose_folder(self) -> None:
        current = self.folder_var.get().strip()
        chosen = filedialog.askdirectory(initialdir=current or None, title="Pasta para analisar")
        if chosen:
            self.folder_var.set(chosen)

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

        self._busy = True
        self.analyze_btn.configure(state=tk.DISABLED)
        self.trash_btn.configure(state=tk.DISABLED)
        self.progress.start(12)
        self.status_var.set("Analisando… a janela pode levar um tempo em pastas grandes.")
        self.summary.configure(text="")
        self._clear_table()

        def work() -> None:
            try:
                stats = scan_files(root, all_files=all_files)
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
                f"{marked} arquivo(s) marcados. Duplo clique abre a pasta do arquivo."
            )

    def _finish_busy(self) -> None:
        self._busy = False
        self.progress.stop()
        self.analyze_btn.configure(state=tk.NORMAL)

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
        folder = path.parent if path.exists() else self._stats.root
        try:
            if sys.platform == "win32":
                os.startfile(folder)  # noqa: S606
            elif sys.platform == "darwin":
                os.system(f'open "{folder}"')  # noqa: S605, S607
            else:
                os.system(f'xdg-open "{folder}"')  # noqa: S605, S607
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
        result = send_marked_to_trash(to_delete)
        extra = "\n".join(result.messages[:8])
        if result.messages[8:]:
            extra += f"\n… (+{len(result.messages) - 8})"
        messagebox.showinfo(
            "Lixeira",
            f"Enviados: {result.deleted}\nIgnorados: {result.skipped}\nFalhas: {result.failures}"
            + (f"\n\n{extra}" if extra else ""),
        )
        if result.deleted:
            self.trash_btn.configure(state=tk.DISABLED)
            self.status_var.set("Cópias enviadas à lixeira. Rode Analisar de novo se quiser conferir.")
            self._result = None


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
