import os
import uuid

from django import forms
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import HttpResponse, HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog.models import Article
from apps.catalog.models import Brand, Category, Product

from .models import Banner, Branch, Page, SiteSettings
from .utils.images import process_image

EDITOR_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
EDITOR_IMAGE_MAX_SIZE = 5 * 1024 * 1024


def home(request):
    products = Product.objects.active().for_listing()
    context = {
        "hero_banners": Banner.objects.live().filter(position=Banner.Position.HERO),
        "promo_banners": Banner.objects.live().filter(position=Banner.Position.PROMO)[:2],
        "categories": Category.objects.filter(is_active=True, parent__isnull=True),
        "discounted_products": products.discounted().order_by("-created_at")[:12],
        "featured_products": products.filter(is_featured=True)[:12],
        "new_products": products.order_by("-created_at")[:10],
        "best_sellers": products.filter(sold_count__gt=0).order_by("-sold_count")[:12],
        "brands": Brand.objects.filter(is_active=True)[:24],
        "latest_articles": Article.objects.published().select_related("category")[:3],
    }
    return render(request, "core/home.html", context)


def contact(request):
    branches = list(Branch.objects.filter(is_active=True))
    context = {
        "branches": branches,
        "map_data": [branch.as_map_data() for branch in branches],
        "map_tile_url": settings.MAP_TILE_URL,
        "map_tile_attribution": settings.MAP_TILE_ATTRIBUTION,
    }
    return render(request, "core/contact.html", context)


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_active=True)
    return render(request, "core/page_detail.html", {"page": page})


def favicon(request):
    site = SiteSettings.load()
    url = site.favicon.url if site.favicon else static("img/favicon.svg")
    return HttpResponsePermanentRedirect(url)


def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("django.contrib.sitemaps.views.sitemap"))
    lines = [
        "User-agent: *",
        "Disallow: /account/",
        "Disallow: /cart/",
        "Disallow: /checkout/",
        "Disallow: /payment/",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain; charset=utf-8")


class EditorImageForm(forms.Form):
    image = forms.ImageField()


@require_POST
def editor_upload(request):
    """Image upload endpoint used by the admin rich text editor (staff only)."""
    user = request.user
    if not (user.is_authenticated and user.is_active and user.is_staff):
        return JsonResponse({"error": "دسترسی غیرمجاز است."}, status=403)

    form = EditorImageForm(files=request.FILES)
    if not form.is_valid():
        return JsonResponse({"error": "فایل انتخاب‌شده یک تصویر معتبر نیست."}, status=400)

    upload = form.cleaned_data["image"]
    extension = os.path.splitext(upload.name)[1].lower()
    if extension not in EDITOR_IMAGE_EXTENSIONS:
        return JsonResponse({"error": "فقط تصاویر JPG، PNG، WEBP و GIF مجاز هستند."}, status=400)
    if upload.size > EDITOR_IMAGE_MAX_SIZE:
        return JsonResponse({"error": "حجم تصویر نباید بیشتر از ۵ مگابایت باشد."}, status=400)

    content = process_image(upload) or upload
    path = default_storage.save(f"editor/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{extension}", content)
    return JsonResponse({"url": default_storage.url(path)})
