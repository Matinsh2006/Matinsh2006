"""فهرست و صفحه‌ی مقاله."""
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, render

from .models import Article, ArticleCategory


def article_list(request):
    """فهرست مقالات با جست‌وجو و فیلتر دسته."""
    articles = Article.objects.published().select_related("category", "author")
    query = (request.GET.get("q") or "").strip()
    if query:
        articles = articles.filter(
            Q(title__icontains=query) | Q(summary__icontains=query)
            | Q(content__icontains=query) | Q(tags__icontains=query)
        )
    category_slug = request.GET.get("cat")
    active_category = None
    if category_slug:
        active_category = ArticleCategory.objects.filter(slug=category_slug).first()
        if active_category:
            articles = articles.filter(category=active_category)

    paginator = Paginator(articles, 6)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "blog/list.html",
        {
            "page_obj": page,
            "articles": page.object_list,
            "categories": ArticleCategory.objects.all(),
            "active_category": active_category,
            "query": query,
        },
    )


def article_detail(request, slug):
    """نمایش مقاله و افزایش شمارنده‌ی بازدید."""
    article = get_object_or_404(
        Article.objects.published().select_related("category", "author"), slug=slug
    )
    Article.objects.filter(pk=article.pk).update(views_count=F("views_count") + 1)
    related = (
        Article.objects.published().filter(category=article.category).exclude(pk=article.pk)[:3]
        if article.category
        else Article.objects.published().exclude(pk=article.pk)[:3]
    )
    return render(request, "blog/detail.html", {"article": article, "related_articles": related})
