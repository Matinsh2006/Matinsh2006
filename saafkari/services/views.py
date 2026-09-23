"""نمایش فهرست و جزئیات خدمات."""
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render

from gallery.models import PortfolioItem

from .models import Service, ServiceCategory


def service_list(request):
    """فهرست خدمات، با امکان فیلتر بر اساس دسته."""
    services = Service.objects.active().select_related("category")
    category_slug = request.GET.get("cat")
    active_category = None
    if category_slug:
        active_category = ServiceCategory.objects.filter(slug=category_slug, is_active=True).first()
        if active_category:
            services = services.filter(category=active_category)
    return render(
        request,
        "services/list.html",
        {
            "services": services,
            "categories": ServiceCategory.objects.filter(is_active=True),
            "active_category": active_category,
        },
    )


def service_detail(request, slug):
    """جزئیات یک خدمت به‌همراه نمونه‌کارهای مرتبط."""
    service = get_object_or_404(Service.objects.select_related("category"), slug=slug, is_active=True)
    samples = (
        PortfolioItem.objects.filter(service=service, is_active=True)
        .prefetch_related(Prefetch("images"))[:6]
    )
    related = Service.objects.active().exclude(pk=service.pk).filter(category=service.category)[:3]
    return render(
        request,
        "services/detail.html",
        {"service": service, "samples": samples, "related_services": related},
    )
