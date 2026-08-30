from __future__ import annotations

import hashlib

import imagehash
from PIL import Image, ImageOps

from duplicate_verifier.constants import PHASH_SIZE


def sha256_file(path: str, chunk_size: int = 1024 * 1024) -> tuple[str, str | None]:
    """Return (hex_digest, error). Error is set when the file cannot be read."""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        return "", str(exc)
    return digest.hexdigest(), None


def perceptual_fingerprint(path: str) -> dict[str, object]:
    """Decode one image and return pHash plus basic quality metadata."""
    result: dict[str, object] = {
        "path": path,
        "phash": None,
        "width": None,
        "height": None,
        "format": None,
        "error": None,
    }
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image) or image
            result["width"] = image.width
            result["height"] = image.height
            result["format"] = image.format
            phash = imagehash.phash(image, hash_size=PHASH_SIZE)
            result["phash"] = int(str(phash), 16)
    except Exception as exc:  # noqa: BLE001 - corrupt/unsupported images are expected
        result["error"] = str(exc)
    return result


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()
