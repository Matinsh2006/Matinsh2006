from django.shortcuts import get_object_or_404, render

from .models import PortfolioItem


def gallery_list(request):
    items = PortfolioItem.objects.filter(is_published=True).prefetch_related("images")
    return render(request, "gallery/list.html", {"items": items})


def gallery_detail(request, pk):
    item = get_object_or_404(
        PortfolioItem.objects.prefetch_related("images"), pk=pk, is_published=True
    )
    return render(request, "gallery/detail.html", {"item": item})
