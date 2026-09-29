import json

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Case, Count, ExpressionWrapper, F, FloatField, IntegerField, Prefetch, Q, Value, When
from django.db.models.functions import NullIf
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe

from apps.cart.cart import Cart
from apps.core.utils.text import normalize_search_query, to_latin_digits

from .models import Brand, Category, Product

SORT_OPTIONS = {
    "newest": "جدیدترین",
    "bestselling": "پرفروش‌ترین",
    "cheapest": "ارزان‌ترین",
    "expensive": "گران‌ترین",
    "discount": "بیشترین تخفیف",
}
SORT_ORDERING = {
    "newest": ["-created_at"],
    "bestselling": ["-sold_count", "-created_at"],
    "cheapest": ["effective_price", "-created_at"],
    "expensive": ["-effective_price", "-created_at"],
    "discount": ["-discount_ratio", "-created_at"],
}


def _parse_price(value):
    digits = "".join(ch for ch in to_latin_digits(value or "") if ch.isdigit())
    return int(digits) if digits else None


def _active_categories():
    return Category.objects.filter(is_active=True, parent__isnull=True).prefetch_related(
        Prefetch("children", queryset=Category.objects.filter(is_active=True))
    )


def product_list(request, category_slug=None, brand_slug=None):
    """Product listing with search, filters, sorting and pagination (also used for category/brand pages)."""
    params = request.GET
    products = Product.objects.active().for_listing().with_effective_price()

    category = brand = None
    if category_slug:
        category = get_object_or_404(Category.objects.select_related("parent"), slug=category_slug, is_active=True)
        products = products.filter(category_id__in=category.get_descendant_ids())
    if brand_slug:
        brand = get_object_or_404(Brand, slug=brand_slug, is_active=True)
        products = products.filter(brand=brand)

    query = normalize_search_query(params.get("q", ""))[:100]
    for word in query.split()[:6]:
        products = products.filter(
            Q(name__icontains=word)
            | Q(brand__name__icontains=word)
            | Q(brand__name_en__icontains=word)
            | Q(category__name__icontains=word)
            | Q(short_description__icontains=word)
            | Q(sku__iexact=word)
        )

    selected_category = None
    if not category:
        selected_category = Category.objects.filter(slug=params.get("category") or "", is_active=True).first()
        if selected_category:
            products = products.filter(category_id__in=selected_category.get_descendant_ids())

    selected_brands = [] if brand else [slug for slug in params.getlist("brand") if slug]
    if selected_brands:
        products = products.filter(brand__slug__in=selected_brands)

    min_price, max_price = _parse_price(params.get("min_price")), _parse_price(params.get("max_price"))
    if min_price is not None:
        products = products.filter(effective_price__gte=min_price)
    if max_price is not None:
        products = products.filter(effective_price__lte=max_price)

    only_available = params.get("available") == "1"
    if only_available:
        products = products.in_stock()
    only_discounted = params.get("discount") == "1"
    if only_discounted:
        products = products.discounted()

    sort = params.get("sort") if params.get("sort") in SORT_OPTIONS else "newest"
    if sort == "discount":
        products = products.annotate(
            discount_ratio=ExpressionWrapper(
                (F("price") - F("effective_price")) * 1.0 / NullIf(F("price"), 0), output_field=FloatField()
            )
        )
    # Available products first, then the chosen ordering.
    products = products.annotate(
        is_available=Case(When(stock__gt=0, then=Value(1)), default=Value(0), output_field=IntegerField())
    ).order_by("-is_available", *SORT_ORDERING[sort])

    page_obj = Paginator(products, settings.PRODUCTS_PER_PAGE).get_page(params.get("page"))
    active_filters = sum(
        [
            bool(selected_category),
            bool(selected_brands),
            min_price is not None,
            max_price is not None,
            only_available,
            only_discounted,
        ]
    )

    filter_brands = Brand.objects.filter(is_active=True)
    if category:
        filter_brands = filter_brands.filter(
            products__category_id__in=category.get_descendant_ids(), products__is_active=True
        ).distinct()

    context = {
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "category": category,
        "brand": brand,
        "query": query,
        "sort": sort,
        "sort_options": SORT_OPTIONS.items(),
        "filter_categories": _active_categories(),
        "filter_brands": filter_brands,
        "selected_category": selected_category,
        "selected_brands": selected_brands,
        "min_price": min_price,
        "max_price": max_price,
        "only_available": only_available,
        "only_discounted": only_discounted,
        "active_filters": active_filters,
    }
    return render(request, "catalog/product_list.html", context)


def _product_json_ld(request, product, images):
    """schema.org Product data so search engines can show price and availability."""
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "sku": product.sku or str(product.pk),
        "description": product.short_description or product.name,
        "image": [request.build_absolute_uri(image.image.url) for image in images[:5]],
        "offers": {
            "@type": "Offer",
            "priceCurrency": "IRR",
            "price": product.final_price * 10,
            "availability": "https://schema.org/InStock" if product.in_stock else "https://schema.org/OutOfStock",
            "url": request.build_absolute_uri(product.get_absolute_url()),
        },
    }
    if product.brand:
        data["brand"] = {"@type": "Brand", "name": product.brand.name}
    return mark_safe(json.dumps(data, ensure_ascii=False).replace("<", "\\u003c"))


def _related_products(product, limit=10):
    """Same category first, then the parent category, then the same brand."""
    base = Product.objects.active().for_listing().exclude(pk=product.pk).order_by("-sold_count", "-created_at")
    filters = []
    if product.category_id:
        filters.append(Q(category_id=product.category_id))
        if product.category.parent_id:
            filters.append(Q(category__parent_id=product.category.parent_id) | Q(category_id=product.category.parent_id))
    if product.brand_id:
        filters.append(Q(brand_id=product.brand_id))

    related, seen = [], set()
    for condition in filters:
        for item in base.filter(condition).exclude(pk__in=seen)[: limit - len(related)]:
            related.append(item)
            seen.add(item.pk)
        if len(related) >= limit:
            break
    return related


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.active()
        .select_related("brand", "category", "category__parent")
        .prefetch_related("images", "specifications"),
        slug=slug,
    )
    images = list(product.images.all())
    related = _related_products(product)

    context = {
        "product": product,
        "images": images,
        "json_ld": _product_json_ld(request, product, images),
        "specifications": product.specifications.all(),
        "related_products": related,
        "related_articles": product.articles.published()[:3],
        "in_cart_quantity": Cart(request).get_quantity(product.pk),
    }
    return render(request, "catalog/product_detail.html", context)


def brand_list(request):
    brands = Brand.objects.filter(is_active=True).annotate(
        product_count=Count("products", filter=Q(products__is_active=True))
    )
    return render(request, "catalog/brand_list.html", {"brands": brands})


def category_list(request):
    return render(request, "catalog/category_list.html", {"categories": _active_categories()})
