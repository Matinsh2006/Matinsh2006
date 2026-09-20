from django.shortcuts import render

from apps.catalog.models import Category, Gender, Product

from .models import Banner, SiteSetting


def home(request):
    """صفحه اصلی: اسلایدر بنرها، دسته‌ها و محصولات منتخب."""
    products = Product.objects.active().with_relations()
    context = {
        "banners": Banner.objects.filter(is_active=True),
        "featured_products": products.filter(is_featured=True)[:8],
        "newest_products": products[:8],
        "women_products": products.filter(gender=Gender.WOMEN)[:4],
        "men_products": products.filter(gender=Gender.MEN)[:4],
        "women_categories": Category.objects.filter(
            is_active=True, gender=Gender.WOMEN, parent__isnull=True
        )[:6],
        "men_categories": Category.objects.filter(
            is_active=True, gender=Gender.MEN, parent__isnull=True
        )[:6],
    }
    return render(request, "core/home.html", context)


def contact(request):
    """صفحه تماس و لوکیشن مغازه روی نقشه."""
    return render(request, "core/contact.html", {"site": SiteSetting.load()})


def about(request):
    return render(request, "core/about.html", {"site": SiteSetting.load()})
