from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Article


def article_list(request):
    articles_qs = Article.objects.filter(is_published=True, published_at__lte=timezone.now())
    paginator = Paginator(articles_qs, 6)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "articles/list.html", {"page_obj": page_obj})


def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    return render(request, "articles/detail.html", {"article": article})
