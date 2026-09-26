"""Pre-generate the WebP thumbnails used by the templates.

Thumbnails are otherwise created lazily on the first page view; run this
after importing products (or from a cron job) so no visitor waits for them.

    python manage.py warm_thumbnails
"""
from django.core.management.base import BaseCommand

from catalog.models import ProductImage
from core.images import thumbnail_url
from core.models import Banner

PRODUCT_WIDTHS = (160, 240, 480, 720, 1080, 1400)
BANNER_WIDTHS = (900, 1600, 1920)


class Command(BaseCommand):
    help = "Generates the responsive WebP thumbnails for product and banner images."

    def handle(self, *args, **options):
        count = 0
        for image in ProductImage.objects.all().iterator():
            for width in PRODUCT_WIDTHS:
                thumbnail_url(image.image, width)
                count += 1
        for banner in Banner.objects.all():
            for field in (banner.image, banner.image_mobile):
                if field:
                    for width in BANNER_WIDTHS:
                        thumbnail_url(field, width)
                        count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} thumbnails ready."))
