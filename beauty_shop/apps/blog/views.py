from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, F, Prefetch, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.catalog.models import Product
from apps.core.utils.text import normalize_search_query

from .models import Article, ArticleCategory

VIEWED_SESSION_KEY = "viewed_articles"


def _categories_with_articles():
    published = Q(articles__status=Article.Status.PUBLISHED, articles__published_at__lte=timezone.now())
    return ArticleCategory.objects.annotate(num_articles=Count("articles", filter=published)).filter(num_articles__gt=0)


def article_list(request, slug=None):
    articles = Article.objects.published().select_related("category", "author")
    category = None
    if slug:
        category = get_object_or_404(ArticleCategory, slug=slug)
        articles = articles.filter(category=category)

    query = normalize_search_query(request.GET.get("q", ""))[:100]
    if query:
        articles = articles.filter(Q(title__icontains=query) | Q(summary__icontains=query))

    page_obj = Paginator(articles, settings.ARTICLES_PER_PAGE).get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "articles": page_obj.object_list,
        "category": category,
        "categories": _categories_with_articles(),
        "query": query,
    }
    return render(request, "blog/article_list.html", context)


def article_detail(request, slug):
    queryset = Article.objects.select_related("category", "author").prefetch_related(
        Prefetch("related_products", queryset=Product.objects.active().for_listing())
    )
    article = get_object_or_404(queryset, slug=slug)
    # Staff can preview drafts and scheduled articles.
    if not article.is_published and not request.user.is_staff:
        raise Http404

    if article.is_published:
        viewed = request.session.get(VIEWED_SESSION_KEY, [])
        if article.pk not in viewed:
            Article.objects.filter(pk=article.pk).update(views=F("views") + 1)
            request.session[VIEWED_SESSION_KEY] = (viewed + [article.pk])[-50:]

    related_articles = Article.objects.published().exclude(pk=article.pk).select_related("category")
    if article.category_id:
        related_articles = related_articles.filter(category_id=article.category_id)
    context = {
        "article": article,
        "related_products": article.related_products.all(),
        "related_articles": related_articles[:3],
    }
    return render(request, "blog/article_detail.html", context)
