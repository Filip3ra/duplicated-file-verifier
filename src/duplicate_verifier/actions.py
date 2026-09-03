from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from send2trash import send2trash

from duplicate_verifier.models import ImageFile
from duplicate_verifier.plan import clear_plan


@dataclass
class TrashResult:
    deleted: int = 0
    skipped: int = 0
    failures: int = 0
    messages: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failures == 0


def send_marked_to_trash(
    to_delete: list[ImageFile],
    *,
    clear_saved_plan: bool = True,
    on_progress: Callable[[int, int], None] | None = None,
) -> TrashResult:
    """Move marked files to the OS trash. Does not ask for confirmation."""
    result = TrashResult()
    if not to_delete:
        return result

    total = len(to_delete)
    for processed, item in enumerate(to_delete, start=1):
        target = item.path
        if not target.is_file():
            result.skipped += 1
            result.messages.append(f"Já não existe, ignorado: {target}")
        else:
            try:
                current_size = target.stat().st_size
            except OSError as exc:
                result.failures += 1
                result.messages.append(f"Falha ao ler {target}: {exc}")
            else:
                if item.size_bytes and current_size != item.size_bytes:
                    result.skipped += 1
                    result.messages.append(f"Tamanho mudou desde a análise, ignorado: {target}")
                else:
                    try:
                        send2trash(str(target))
                        result.deleted += 1
                    except Exception as exc:  # noqa: BLE001
                        result.failures += 1
                        result.messages.append(f"Falha ao enviar {target} à lixeira: {exc}")
        if on_progress is not None:
            on_progress(processed, total)

    if clear_saved_plan and result.failures == 0:
        clear_plan()
    return result
