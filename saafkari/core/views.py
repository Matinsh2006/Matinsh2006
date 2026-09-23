"""صفحه نخست، درباره‌ی ما و تماس با ما."""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from appointments.models import Appointment
from blog.models import Article
from gallery.models import Banner, PortfolioItem
from services.models import Service

from .forms import ContactForm
from .models import ShopLocation, SiteSettings


def home(request):
    """صفحه نخست: بنرها، خدمات، نمونه‌کارها و آخرین مقالات."""
    site = SiteSettings.load()
    return render(
        request,
        "core/home.html",
        {
            "hero_banners": Banner.objects.live().filter(position=Banner.Position.HERO),
            "middle_banners": Banner.objects.live().filter(position=Banner.Position.MIDDLE),
            "featured_services": Service.objects.featured()[:6] or Service.objects.active()[:6],
            "portfolio_items": (
                PortfolioItem.objects.filter(is_active=True, is_featured=True).prefetch_related("images")[:6]
                or PortfolioItem.objects.filter(is_active=True).prefetch_related("images")[:6]
            ),
            "latest_articles": Article.objects.published()[:3],
            "stats": {
                "services": Service.objects.active().count(),
                "portfolio": PortfolioItem.objects.filter(is_active=True).count(),
                "done_jobs": Appointment.objects.filter(status=Appointment.Status.DONE).count(),
                "articles": Article.objects.published().count(),
            },
            "site": site,
        },
    )


def about(request):
    """درباره‌ی مغازه و لوکیشن شعبه‌ها."""
    return render(
        request,
        "core/about.html",
        {"locations": ShopLocation.objects.filter(is_active=True), "site": SiteSettings.load()},
    )


@require_http_methods(["GET", "POST"])
def contact(request):
    """فرم تماس و نمایش نقشه‌ی مغازه."""
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "پیام شما ثبت شد. به‌زودی با شما تماس می‌گیریم.")
        return redirect("core:contact")
    return render(
        request,
        "core/contact.html",
        {"form": form, "locations": ShopLocation.objects.filter(is_active=True)},
    )


def page_not_found(request, exception):  # pragma: no cover - نمایش خطا
    return render(request, "errors/404.html", status=404)


def server_error(request):  # pragma: no cover - نمایش خطا
    return render(request, "errors/500.html", status=500)
