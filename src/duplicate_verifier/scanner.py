from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from duplicate_verifier.constants import IMAGE_EXTENSIONS, SKIP_DIRECTORY_NAMES
from duplicate_verifier.models import ImageFile, ScanStats


def scan_images(
    root: Path,
    *,
    follow_symlinks: bool = False,
    include_hidden: bool = False,
    extensions: frozenset[str] = IMAGE_EXTENSIONS,
) -> ScanStats:
    """Walk ``root`` recursively and collect image files (metadata only)."""
    return scan_files(
        root,
        follow_symlinks=follow_symlinks,
        include_hidden=include_hidden,
        all_files=False,
        extensions=extensions,
    )


def scan_files(
    root: Path,
    *,
    follow_symlinks: bool = False,
    include_hidden: bool = False,
    all_files: bool = False,
    extensions: frozenset[str] = IMAGE_EXTENSIONS,
) -> ScanStats:
    """Walk ``root`` recursively and collect files (metadata only)."""
    root = root.resolve()
    files: list[ImageFile] = []
    counts: Counter[str] = Counter()
    skipped_dirs = 0
    permission_errors = 0
    stack = [root]

    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    name = entry.name
                    try:
                        if entry.is_symlink() and not follow_symlinks:
                            continue
                        is_dir = entry.is_dir(follow_symlinks=follow_symlinks)
                    except OSError:
                        permission_errors += 1
                        continue
                    if name in SKIP_DIRECTORY_NAMES and is_dir:
                        skipped_dirs += 1
                        continue
                    if not include_hidden and name.startswith("."):
                        skipped_dirs += int(is_dir)
                        continue
                    if is_dir:
                        stack.append(Path(entry.path))
                        continue
                    try:
                        if not entry.is_file(follow_symlinks=follow_symlinks):
                            continue
                    except OSError:
                        permission_errors += 1
                        continue

                    suffix = Path(name).suffix.lower()
                    if not all_files and suffix not in extensions:
                        continue
                    try:
                        size = entry.stat(follow_symlinks=follow_symlinks).st_size
                    except OSError:
                        permission_errors += 1
                        continue
                    if size <= 0:
                        continue
                    files.append(ImageFile(path=Path(entry.path), size_bytes=size))
                    counts[suffix or "(sem extensão)"] += 1
        except OSError:
            permission_errors += 1

    files.sort(key=lambda item: str(item.path).lower())
    return ScanStats(
        root=root,
        files=files,
        extension_counts=dict(sorted(counts.items())),
        skipped_dirs=skipped_dirs,
        permission_errors=permission_errors,
    )
