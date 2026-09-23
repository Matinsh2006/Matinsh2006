from django.shortcuts import render

from articles.models import Article
from gallery.models import PortfolioItem
from services.models import Service


def home(request):
    context = {
        "services": Service.objects.filter(is_active=True)[:6],
        "portfolio_items": PortfolioItem.objects.filter(is_published=True).prefetch_related(
            "images"
        )[:6],
        "articles": Article.objects.filter(is_published=True)[:3],
    }
    return render(request, "pages/home.html", context)


def contact(request):
    return render(request, "pages/contact.html")
