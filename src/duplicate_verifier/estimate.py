from __future__ import annotations

from duplicate_verifier.constants import PHASH_IMAGES_PER_SEC, SHA256_BYTES_PER_SEC


def estimate_seconds(
    file_count: int,
    total_bytes: int,
    *,
    include_visual: bool = True,
    visual_count: int | None = None,
) -> float:
    """Rough wall-clock estimate for hashing + optional perceptual analysis."""
    if file_count <= 0:
        return 0.0
    sha_seconds = total_bytes / SHA256_BYTES_PER_SEC
    hash_targets = visual_count if visual_count is not None else file_count
    phash_seconds = hash_targets / PHASH_IMAGES_PER_SEC if include_visual else 0.0
    overhead = 0.4
    return sha_seconds + phash_seconds + overhead


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return "menos de 1 s"
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    if secs and not hours:
        parts.append(f"{secs} s")
    elif not parts:
        parts.append("1 s")
    return " ".join(parts)


def format_bytes(size: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"
