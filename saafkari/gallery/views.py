"""نمایش نمونه‌کارها (گالری قبل و بعد)."""
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from services.models import Service

from .models import PortfolioItem


def portfolio_list(request):
    """گالری نمونه‌کارها با فیلتر بر اساس خدمت."""
    items = PortfolioItem.objects.filter(is_active=True).select_related("service").prefetch_related("images")
    service_slug = request.GET.get("service")
    active_service = None
    if service_slug:
        active_service = Service.objects.filter(slug=service_slug).first()
        if active_service:
            items = items.filter(service=active_service)

    paginator = Paginator(items, 9)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "gallery/list.html",
        {
            "page_obj": page,
            "items": page.object_list,
            "services": Service.objects.active(),
            "active_service": active_service,
        },
    )


def portfolio_detail(request, slug):
    """جزئیات یک نمونه‌کار با همه‌ی عکس‌های قبل و بعد."""
    item = get_object_or_404(
        PortfolioItem.objects.select_related("service").prefetch_related("images"),
        slug=slug, is_active=True,
    )
    others = PortfolioItem.objects.filter(is_active=True).exclude(pk=item.pk).prefetch_related("images")[:3]
    return render(request, "gallery/detail.html", {"item": item, "others": others})
