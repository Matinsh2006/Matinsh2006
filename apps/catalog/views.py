from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from .models import Brand, Category, Color, Gender, Product, ProductKind, Size

PAGE_SIZE = 12

SORT_OPTIONS = {
    "newest": ("-created_at", "جدیدترین"),
    "cheap": ("price", "ارزان‌ترین"),
    "expensive": ("-price", "گران‌ترین"),
    "popular": ("-is_featured", "پیشنهاد فروشگاه"),
}


def _filter_products(request, base_queryset=None):
    """اعمال فیلترهای کوئری‌استرینگ روی لیست محصولات."""
    products = (base_queryset if base_queryset is not None else Product.objects.all())
    products = products.active().with_relations()

    params = request.GET
    gender = params.get("gender")
    if gender in Gender.values:
        products = products.filter(Q(gender=gender) | Q(gender=Gender.UNISEX))

    category_slug = params.get("category")
    if category_slug:
        products = products.filter(
            Q(category__slug=category_slug) | Q(category__parent__slug=category_slug)
        )

    brand_slug = params.get("brand")
    if brand_slug:
        products = products.filter(brand__slug=brand_slug)

    kind = params.get("kind")
    if kind in ProductKind.values:
        products = products.filter(kind=kind)

    color = params.get("color")
    if color:
        products = products.filter(variants__color__id=color)

    size = params.get("size")
    if size:
        products = products.filter(variants__size__id=size)

    search = (params.get("q") or "").strip()
    if search:
        products = products.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(brand__name__icontains=search)
        )

    min_price, max_price = params.get("min_price"), params.get("max_price")
    if min_price and min_price.isdigit():
        products = products.filter(price__gte=int(min_price))
    if max_price and max_price.isdigit():
        products = products.filter(price__lte=int(max_price))

    if params.get("available") == "1":
        products = products.filter(variants__stock__gt=0)

    sort = params.get("sort", "newest")
    order_by = SORT_OPTIONS.get(sort, SORT_OPTIONS["newest"])[0]
    return products.distinct().order_by(order_by, "-id")


def _filter_context(request, products):
    """داده‌های نوار فیلتر کنار لیست محصولات."""
    querystring = request.GET.copy()
    querystring.pop("page", None)
    return {
        "categories": Category.objects.filter(is_active=True, parent__isnull=True).annotate(
            product_count=Count("products")
        ),
        "brands": Brand.objects.filter(is_active=True),
        "colors": Color.objects.all(),
        "sizes": Size.objects.all(),
        "kinds": ProductKind.choices,
        "genders": Gender.choices,
        "sort_options": [(key, label) for key, (_field, label) in SORT_OPTIONS.items()],
        "current": request.GET,
        "querystring": querystring.urlencode(),
        "total_count": products.count(),
    }


def product_list(request):
    products = _filter_products(request)
    page = Paginator(products, PAGE_SIZE).get_page(request.GET.get("page"))
    context = {"page_obj": page, "products": page.object_list, **_filter_context(request, products)}
    return render(request, "catalog/product_list.html", context)


def gender_list(request, gender):
    """صفحه اختصاصی دسته‌بندی زنانه یا مردانه."""
    request.GET = request.GET.copy()
    request.GET["gender"] = gender
    products = _filter_products(request)
    page = Paginator(products, PAGE_SIZE).get_page(request.GET.get("page"))
    context = {
        "page_obj": page,
        "products": page.object_list,
        "active_gender": gender,
        "gender_label": dict(Gender.choices).get(gender, ""),
        "gender_categories": Category.objects.filter(is_active=True, gender=gender),
        **_filter_context(request, products),
    }
    return render(request, "catalog/product_list.html", context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    request.GET = request.GET.copy()
    request.GET["category"] = category.slug
    products = _filter_products(request)
    page = Paginator(products, PAGE_SIZE).get_page(request.GET.get("page"))
    context = {
        "page_obj": page,
        "products": page.object_list,
        "category": category,
        "active_gender": category.gender,
        **_filter_context(request, products),
    }
    return render(request, "catalog/product_list.html", context)


def brand_list(request):
    brands = Brand.objects.filter(is_active=True).annotate(product_count=Count("products"))
    return render(request, "catalog/brand_list.html", {"brands": brands})


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.active().with_relations().select_related("category__parent"), slug=slug
    )
    variants = product.variants.select_related("size", "color")
    related = (
        Product.objects.active()
        .with_relations()
        .filter(category=product.category)
        .exclude(pk=product.pk)[:4]
    )
    context = {
        "product": product,
        "images": product.images.all(),
        "variants": variants,
        "sizes": product.available_sizes,
        "colors": product.available_colors,
        "related_products": related,
        "variant_map": {
            f"{v.size_id or 0}-{v.color_id or 0}": {"id": v.pk, "stock": v.stock, "price": v.price}
            for v in variants
        },
    }
    return render(request, "catalog/product_detail.html", context)
