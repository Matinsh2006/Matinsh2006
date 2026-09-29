"""Resize and compress uploaded images so pages stay fast on mobile networks."""
import os
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}
# JPEGs below this size are stored as-is when they don't need resizing.
RECOMPRESS_THRESHOLD = 400 * 1024


def process_image(fileobj, max_dimension=None, quality=85):
    """
    Return a ``ContentFile`` with the optimized image, or ``None`` when the
    original should be kept (unsupported format, already small, unreadable).
    """
    max_dimension = max_dimension or settings.IMAGE_MAX_DIMENSION
    try:
        fileobj.seek(0)
        image = Image.open(fileobj)
        image_format = (image.format or "").upper()
        if image_format not in SUPPORTED_FORMATS:
            return None
        size = getattr(fileobj, "size", None) or 0
        needs_resize = max(image.size) > max_dimension
        if not needs_resize and (image_format != "JPEG" or size <= RECOMPRESS_THRESHOLD):
            return None

        image = ImageOps.exif_transpose(image)
        if needs_resize:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        buffer = BytesIO()
        if image_format == "JPEG":
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            image.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
        elif image_format == "PNG":
            image.save(buffer, format="PNG", optimize=True)
        else:
            image.save(buffer, format="WEBP", quality=quality, method=6)
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    finally:
        try:
            fileobj.seek(0)
        except (OSError, ValueError, AttributeError):
            pass
    return ContentFile(buffer.getvalue())


def optimize_image_field(field_file, max_dimension=None):
    """Optimize a *newly assigned* ImageField file in place (call before save)."""
    if not field_file or getattr(field_file, "_committed", True):
        return
    optimized = process_image(field_file.file, max_dimension=max_dimension)
    if optimized is not None:
        field_file.save(os.path.basename(field_file.name), optimized, save=False)
