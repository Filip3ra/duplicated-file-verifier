from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def save_image(path: Path, image: Image.Image, quality: int | None = None) -> None:
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        image.convert("RGB").save(path, quality=quality or 95)
    else:
        image.save(path)


def scene_keep(size: int) -> Image.Image:
    image = Image.new("RGB", (size, size), (255, 240, 200))
    draw = ImageDraw.Draw(image)
    draw.ellipse((size * 0.05, size * 0.05, size * 0.55, size * 0.55), fill=(220, 30, 30))
    draw.rectangle((size * 0.6, size * 0.6, size * 0.95, size * 0.95), fill=(30, 30, 200))
    draw.line((0, size, size, 0), fill=(0, 0, 0), width=max(2, size // 40))
    return image


def scene_other(size: int) -> Image.Image:
    image = Image.new("RGB", (size, size), (10, 10, 10))
    draw = ImageDraw.Draw(image)
    step = max(4, size // 12)
    for x in range(0, size, step):
        draw.rectangle((x, 0, x + step // 2, size), fill=(240, 240, 240))
    draw.polygon([(size // 2, 10), (10, size - 10), (size - 10, size - 10)], fill=(0, 180, 80))
    return image
