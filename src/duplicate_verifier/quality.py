from __future__ import annotations

from duplicate_verifier.constants import FORMAT_RANK
from duplicate_verifier.models import ImageFile


def quality_key(image: ImageFile) -> tuple:
    """Lower tuple = better candidate to keep.

    1. More pixels (resolution)
    2. Larger file (usually less compression)
    3. Lossless-friendly format
    4. Shorter path, then lexicographic (stable tie-break)
    """
    fmt = FORMAT_RANK.get((image.format or "").upper(), 0)
    path = str(image.path)
    return (
        -image.pixels,
        -image.size_bytes,
        -fmt,
        len(path),
        path.lower(),
    )


def pick_keep(files: list[ImageFile]) -> tuple[ImageFile, list[ImageFile]]:
    ranked = sorted(files, key=quality_key)
    return ranked[0], ranked[1:]
