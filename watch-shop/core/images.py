"""Image helpers: upload optimisation and on-demand responsive thumbnails."""
import logging
import os
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIDE = 2400


def _has_alpha(image):
    return image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)


def optimize_upload(field_file, max_side=MAX_UPLOAD_SIDE, quality=88):
    """Downscale huge uploads and re-encode them as WebP before they are stored.

    Call it from a model's ``save()``; it only touches freshly uploaded files.
    """
    if not field_file or getattr(field_file, "_committed", True):
        return
    try:
        field_file.seek(0)
        image = Image.open(field_file)
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError, ValueError):
        return
    if getattr(image, "is_animated", False):
        return  # keep animated GIF/WebP banners untouched

    image.thumbnail((max_side, max_side), Image.LANCZOS)
    image = image.convert("RGBA" if _has_alpha(image) else "RGB")
    buffer = BytesIO()
    image.save(buffer, format="WEBP", quality=quality, method=5)
    base = os.path.splitext(os.path.basename(field_file.name))[0]
    field_file.save(f"{base}.webp", ContentFile(buffer.getvalue()), save=False)


def thumbnail_url(field_file, width, quality=82):
    """URL of a WebP copy of ``field_file`` at most ``width`` pixels wide.

    Thumbnails are generated lazily into ``MEDIA_ROOT/cache/<width>/`` the
    first time they are requested and reused afterwards.
    """
    if not field_file:
        return ""
    try:
        width = int(width)
        name = field_file.name
        storage = field_file.storage
        thumb_name = f"cache/{width}/{os.path.splitext(name)[0]}.webp"
        if not storage.exists(thumb_name):
            with storage.open(name, "rb") as handle:
                image = Image.open(handle)
                image = ImageOps.exif_transpose(image)
                if getattr(image, "is_animated", False):
                    return field_file.url
                if image.width > width:
                    height = max(1, round(image.height * width / image.width))
                    image = image.resize((width, height), Image.LANCZOS)
                image = image.convert("RGBA" if _has_alpha(image) else "RGB")
                buffer = BytesIO()
                image.save(buffer, format="WEBP", quality=quality, method=4)
            thumb_name = storage.save(thumb_name, ContentFile(buffer.getvalue()))
        return storage.url(thumb_name)
    except (FileNotFoundError, UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning("Could not create thumbnail for %s: %s", field_file, exc)
        try:
            return field_file.url
        except ValueError:
            return ""
