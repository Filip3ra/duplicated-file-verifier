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
    keep: ImageFile
    delete: list[ImageFile] = field(default_factory=list)
    max_hamming: int = 0

    @property
    def files(self) -> list[ImageFile]:
        return [self.keep, *self.delete]

    @property
    def reclaimable_bytes(self) -> int:
        return sum(item.size_bytes for item in self.delete)


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
