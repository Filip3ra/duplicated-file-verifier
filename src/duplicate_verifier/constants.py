IMAGE_EXTENSIONS = frozenset(
    {
        ".bmp",
        ".gif",
        ".jfif",
        ".jpe",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
)

# Lossless / less compressed formats win ties after resolution and file size.
FORMAT_RANK = {
    "PNG": 5,
    "TIFF": 5,
    "BMP": 4,
    "WEBP": 3,
    "JPEG": 2,
    "GIF": 1,
}

# Conservative throughput for time estimates (HDD / large photos).
SHA256_BYTES_PER_SEC = 120 * 1024 * 1024
PHASH_IMAGES_PER_SEC = 35.0

DEFAULT_HAMMING_THRESHOLD = 8
PHASH_SIZE = 8
