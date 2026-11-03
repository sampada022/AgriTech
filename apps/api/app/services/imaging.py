"""Upload validation (TRD 8.5): decode with Pillow, cap size and pixels, strip EXIF."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

import cv2
import numpy as np
from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from app.errors import ApiError

# Pillow's own decompression-bomb guard sits below our caps, so ours is the one that applies.
Image.MAX_IMAGE_PIXELS = None

PHOTO_MAX_EDGE = 1280
BLURRY_PHOTO_VARIANCE = 15.0


@dataclass
class DecodedImage:
    rgb: np.ndarray
    width: int
    height: int
    format: str


def read_upload(upload: UploadFile, max_mb: int) -> bytes:
    limit = max_mb * 1024 * 1024
    data = upload.file.read(limit + 1)
    if len(data) > limit:
        raise ApiError(
            413,
            "file_too_large",
            f"This file is larger than the {max_mb} MB limit.",
            "Export a smaller image and upload it again.",
        )
    if not data:
        raise ApiError(422, "empty_file", "The uploaded file is empty.", "Choose the image again.")
    return data


def to_rgb(image: Image.Image) -> np.ndarray:
    """RGB array with transparent pixels forced to black, which the engine reads as no-data.

    Orthomosaic tools mark empty margins with alpha. Dropping alpha alone would keep whatever
    colour happens to sit under those pixels.
    """
    if image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info:
        rgba = np.asarray(image.convert("RGBA"))
        rgb = rgba[..., :3].copy()
        rgb[rgba[..., 3] == 0] = 0
        return rgb
    return np.asarray(image.convert("RGB"))


def decode_image(data: bytes, allowed: set[str], max_pixels: int) -> DecodedImage:
    """Open by content, not extension. Applies EXIF orientation, then forgets EXIF."""
    invalid = ApiError(
        422,
        "invalid_image",
        "This file is not a readable image.",
        f"Upload a {' or '.join(sorted(allowed))} file.",
    )
    try:
        image = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise invalid from exc
    if image.format not in allowed:
        raise invalid
    width, height = image.size
    if width * height > max_pixels:
        raise ApiError(
            413,
            "image_too_large",
            f"This image has {width * height / 1e6:.0f} MP, above the "
            f"{max_pixels / 1e6:.0f} MP limit.",
            "Downscale the image and upload it again.",
        )
    try:
        image.load()
        rgb = to_rgb(ImageOps.exif_transpose(image))
    except (OSError, ValueError, SyntaxError) as exc:
        raise invalid from exc
    return DecodedImage(rgb=rgb, width=rgb.shape[1], height=rgb.shape[0], format=image.format)


def encode_jpeg(rgb: np.ndarray, quality: int = 95, full_chroma: bool = False) -> bytes:
    """Re-encode from raw pixels, which leaves all metadata behind, including GPS tags.

    Field images use full_chroma. The canopy mask works from colour, and default 4:2:0 subsampling
    smears it. Real early wheat read 43.5% canopy from the original file, 51.3% at 4:2:0 and 46.5%
    at 4:4:4, so this narrows the gap without closing it. See KNOWN_ISSUES.md.
    """
    buffer = io.BytesIO()
    Image.fromarray(rgb).save(
        buffer, "JPEG", quality=quality, subsampling=0 if full_chroma else -1
    )
    return buffer.getvalue()


def load_rgb(path) -> np.ndarray:
    return to_rgb(Image.open(path))


def prepare_leaf_photo(data: bytes, max_pixels: int) -> tuple[bytes, str, bool]:
    """Returns clean JPEG bytes, a content hash and whether the photo looks blurry.

    The phone already downsizes before upload. The server enforces it too, because the client is
    not the place to rely on for what reaches a paid API.
    """
    decoded = decode_image(data, {"JPEG", "PNG", "WEBP"}, max_pixels)
    rgb = decoded.rgb
    longest = max(decoded.width, decoded.height)
    if longest > PHOTO_MAX_EDGE:
        scale = PHOTO_MAX_EDGE / longest
        rgb = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    blurry = float(cv2.Laplacian(gray, cv2.CV_32F).var()) < BLURRY_PHOTO_VARIANCE
    clean = encode_jpeg(rgb, 88)
    return clean, hashlib.sha256(clean).hexdigest(), blurry
