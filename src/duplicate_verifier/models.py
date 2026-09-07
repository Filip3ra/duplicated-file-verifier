from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class GroupKind(str, Enum):
    EXACT = "exact"
    VISUAL = "visual"


@dataclass
class ImageFile:
    path: Path
    size_bytes: int
    sha256: str | None = None
    phash: int | None = None
    width: int | None = None
    height: int | None = None
    format: str | None = None
    error: str | None = None

    @property
    def pixels(self) -> int:
        if self.width is None or self.height is None:
            return 0
        return self.width * self.height


@dataclass
class DuplicateGroup:
    kind: GroupKind
    keep: list[ImageFile]
    delete: list[ImageFile] = field(default_factory=list)
    max_hamming: int = 0

    @property
    def files(self) -> list[ImageFile]:
        return [*self.keep, *self.delete]

    @property
    def reclaimable_bytes(self) -> int:
        if not self.keep:
            return 0
        return sum(item.size_bytes for item in self.delete)

    def files_to_trash(self) -> list[ImageFile]:
        """Files to send to trash. Empty when the group has no keep (skipped)."""
        if not self.keep:
            return []
        return list(self.delete)

    def set_file_kept(self, image: ImageFile, *, keep: bool) -> None:
        """Move ``image`` between keep and delete. An empty keep skips the group."""
        remaining_keep = [item for item in self.keep if item.path != image.path]
        remaining_delete = [item for item in self.delete if item.path != image.path]
        if keep:
            self.keep = [*remaining_keep, image]
            self.delete = remaining_delete
        else:
            self.keep = remaining_keep
            self.delete = [*remaining_delete, image]


@dataclass
class ScanStats:
    root: Path
    files: list[ImageFile]
    extension_counts: dict[str, int]
    skipped_dirs: int = 0
    permission_errors: int = 0

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_bytes(self) -> int:
        return sum(item.size_bytes for item in self.files)


@dataclass
class AnalysisResult:
    groups: list[DuplicateGroup]
    failed: list[ImageFile]
    unique_contents: int
    elapsed_seconds: float
    methods: tuple[str, ...] = ("exact", "visual")
    threshold: int = 1

    def reclaimable_bytes(self, kind: GroupKind | None = None) -> int:
        groups = self.groups if kind is None else [g for g in self.groups if g.kind is kind]
        return sum(group.reclaimable_bytes for group in groups)

    def reclaimable_count(self, kind: GroupKind | None = None) -> int:
        groups = self.groups if kind is None else [g for g in self.groups if g.kind is kind]
        return sum(len(group.files_to_trash()) for group in groups)
