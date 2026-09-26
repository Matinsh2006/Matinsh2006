import json

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from catalog.models import Brand, Category, Product, ProductImage

from .forms import ContactForm
from .models import Banner, Page, SiteSettings, StoreLocation


def _category_cards():
    """Watch types with their gender sub-categories and a cover image."""
    roots = Category.objects.active().roots().with_children().order_by("order", "name")
    cards = []
    for category in roots:
        category.product_count = Product.objects.active().in_category(category).count()
        cover = category.image or None
        if not cover:
            image = (
                ProductImage.objects.filter(
                    Q(product__category__parent=category) | Q(product__category=category),
                    product__is_active=True,
                )
                .order_by("product__created_at", "order")
                .first()
            )
            cover = image.image if image else None
        cards.append({"category": category, "cover": cover, "children": list(category.children.all())})
    return cards


def home(request):
    settings_obj = SiteSettings.load()
    featured = list(Product.objects.active().filter(is_featured=True).with_related()[:8])
    if len(featured) < 4:
        featured += list(
            Product.objects.active()
            .exclude(pk__in=[p.pk for p in featured])
            .with_related()[: 8 - len(featured)]
        )
    hero_product = settings_obj.hero_product if settings_obj.hero_product_id else None
    if hero_product and not hero_product.is_active:
        hero_product = None
    stores = list(StoreLocation.objects.filter(is_active=True))
    context = {
        "featured_products": featured,
        "new_arrivals": list(Product.objects.active().with_related().order_by("-created_at")[:10]),
        "category_cards": _category_cards(),
        "home_banners": list(Banner.objects.live().filter(placement=Banner.Placement.HOME)[:3]),
        "brands": list(Brand.objects.filter(is_active=True)),
        "stores": stores,
        "stores_json": json.dumps(
            [
                {
                    "name": store.name,
                    "address": store.address,
                    "lat": float(store.latitude),
                    "lng": float(store.longitude),
                    "zoom": store.zoom,
                }
                for store in stores
            ],
            ensure_ascii=False,
        ),
        "hero_product": hero_product,
        "hero_config": json.dumps(
            {
                "metal": settings_obj.hero_metal,
                "dial": settings_obj.hero_dial,
                "brand": settings_obj.site_name_en or "SANIYEH",
                "brandFa": settings_obj.site_name,
            },
            ensure_ascii=False,
        ),
        "product_count": Product.objects.active().count(),
        "brand_count": Brand.objects.filter(is_active=True).count(),
    }
    return render(request, "core/home.html", context)


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "پیام شما دریافت شد؛ به‌زودی با شما تماس می‌گیریم.")
        return redirect(reverse("core:contact") + "#contact-form")
    stores = list(StoreLocation.objects.filter(is_active=True))
    stores_json = json.dumps(
        [
            {"name": s.name, "address": s.address, "lat": float(s.latitude), "lng": float(s.longitude), "zoom": s.zoom}
            for s in stores
        ],
        ensure_ascii=False,
    )
    return render(request, "core/contact.html", {"form": form, "stores": stores, "stores_json": stores_json})


def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_active=True)
    return render(request, "core/page.html", {"page": page})


@require_GET
def robots_txt(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /account/",
        "Disallow: /cart/",
        "Disallow: /orders/",
        "Disallow: /payment/",
        f"Sitemap: {sitemap_url}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request):
    return render(request, "500.html", status=500)
