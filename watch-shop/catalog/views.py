import json
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Case, ExpressionWrapper, F, FloatField, IntegerField, Q, When
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.html import strip_tags

from core.images import thumbnail_url
from core.utils import format_number

from .forms import ProductFilterForm
from .models import Brand, Category, Gender, Product

PAGE_SIZE = 12
GENDER_TITLES = {Gender.MEN: "ساعت مردانه", Gender.WOMEN: "ساعت زنانه"}
_ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ك": "ک", "ى": "ی", "ة": "ه"})


def normalize_query(text):
    return " ".join((text or "").translate(_ARABIC_TO_PERSIAN).split())


def search_products(queryset, query):
    for word in normalize_query(query).split(" ")[:6]:
        if not word:
            continue
        queryset = queryset.filter(
            Q(name__icontains=word)
            | Q(name_en__icontains=word)
            | Q(sku__iexact=word)
            | Q(brand__name__icontains=word)
            | Q(brand__name_en__icontains=word)
            | Q(category__name__icontains=word)
            | Q(category__parent__name__icontains=word)
        )
    return queryset


def apply_filters(queryset, data):
    if data.get("q"):
        queryset = search_products(queryset, data["q"])
    if data.get("gender"):
        queryset = queryset.for_gender(data["gender"])
    if data.get("brand"):
        queryset = queryset.filter(brand__slug__in=data["brand"])
    if data.get("type"):
        queryset = queryset.filter(
            Q(category__parent__slug__in=data["type"])
            | Q(category__parent__isnull=True, category__slug__in=data["type"])
        )
    if data.get("movement"):
        queryset = queryset.filter(movement__in=data["movement"])
    if data.get("strap"):
        queryset = queryset.filter(strap_material__in=data["strap"])
    if data.get("min_price") is not None:
        queryset = queryset.filter(price__gte=data["min_price"])
    if data.get("max_price"):
        queryset = queryset.filter(price__lte=data["max_price"])
    if data.get("available"):
        queryset = queryset.filter(stock__gt=0)
    if data.get("discount"):
        queryset = queryset.filter(compare_at_price__gt=F("price"))
    return sort_products(queryset, data.get("sort"))


def sort_products(queryset, sort):
    queryset = queryset.annotate(
        _available=Case(When(stock__gt=0, then=1), default=0, output_field=IntegerField())
    )
    if sort == "cheap":
        return queryset.order_by("-_available", "price")
    if sort == "expensive":
        return queryset.order_by("-_available", "-price")
    if sort == "discount":
        return queryset.annotate(
            _discount=Case(
                When(
                    compare_at_price__gt=F("price"),
                    then=ExpressionWrapper(
                        (F("compare_at_price") - F("price")) * 1.0 / F("compare_at_price"),
                        output_field=FloatField(),
                    ),
                ),
                default=0.0,
                output_field=FloatField(),
            )
        ).order_by("-_available", "-_discount", "-created_at")
    return queryset.order_by("-_available", "-created_at")


def _listing(request, base_queryset, *, title, subtitle="", extra=None):
    types = list(Category.objects.active().roots().order_by("order", "name"))
    brands = list(Brand.objects.filter(is_active=True, products__in=base_queryset).distinct().order_by("order", "name"))
    form = ProductFilterForm(request.GET or None, brands=brands, types=types)
    data = form.cleaned_data if form.is_valid() else {}
    queryset = apply_filters(base_queryset, data).with_related()

    page = Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))
    context = {
        "title": title,
        "subtitle": subtitle,
        "page_obj": page,
        "products": page.object_list,
        "form": form,
        "filters": data,
        "filter_brands": brands,
        "filter_types": types,
        "sort_choices": ProductFilterForm.SORT_CHOICES,
        "current_sort": data.get("sort") or "new",
        "has_active_filters": any(
            data.get(key) for key in ("brand", "type", "movement", "strap", "min_price", "max_price", "available", "discount", "gender")
        ),
        **(extra or {}),
    }
    if request.GET.get("partial") == "1":
        return render(request, "catalog/_product_grid_items.html", context)
    return render(request, "catalog/product_list.html", context)


def shop(request):
    return _listing(
        request,
        Product.objects.active(),
        title="همه ساعت‌ها",
        subtitle="مجموعه کامل ساعت‌های مردانه و زنانه، با ضمانت اصالت کالا",
    )


def gender_view(request, gender):
    if gender not in GENDER_TITLES:
        raise Http404
    chips = [
        {"label": child.parent.name, "url": child.get_absolute_url()}
        for child in Category.objects.active()
        .filter(gender=gender, parent__isnull=False, parent__is_active=True)
        .select_related("parent")
        .order_by("parent__order", "parent__name")
    ]
    return _listing(
        request,
        Product.objects.active().for_gender(gender),
        title=GENDER_TITLES[gender],
        subtitle="بر اساس نوع ساعت انتخاب کنید",
        extra={"gender": gender, "chips": chips, "chips_all_label": "همه"},
    )


def category_view(request, slug):
    category = get_object_or_404(Category.objects.active().roots(), slug=slug)
    children = list(category.children.active().order_by("order", "name"))
    chips = [{"label": child.name, "url": child.get_absolute_url()} for child in children]
    return _listing(
        request,
        Product.objects.active().in_category(category),
        title=category.title,
        subtitle=category.tagline or category.description,
        extra={"category": category, "chips": chips, "chips_all_label": "همه", "chips_all_url": category.get_absolute_url()},
    )


def subcategory_view(request, parent_slug, slug):
    category = get_object_or_404(
        Category.objects.active().select_related("parent"),
        parent__slug=parent_slug,
        parent__is_active=True,
        slug=slug,
    )
    siblings = category.parent.children.active().order_by("order", "name")
    chips = [
        {"label": sibling.name, "url": sibling.get_absolute_url(), "active": sibling.pk == category.pk}
        for sibling in siblings
    ]
    return _listing(
        request,
        Product.objects.active().filter(category=category),
        title=category.title,
        subtitle=category.tagline or category.parent.tagline,
        extra={
            "category": category,
            "chips": chips,
            "chips_all_label": f"همه {category.parent.name}",
            "chips_all_url": category.parent.get_absolute_url(),
        },
    )


def brand_view(request, slug):
    brand = get_object_or_404(Brand.objects.filter(is_active=True), slug=slug)
    return _listing(
        request,
        Product.objects.active().filter(brand=brand),
        title=f"ساعت‌های {brand.name}",
        subtitle=brand.description,
        extra={"brand": brand},
    )


def search_view(request):
    query = normalize_query(request.GET.get("q", ""))
    return _listing(
        request,
        Product.objects.active(),
        title=f"نتایج جستجو برای «{query}»" if query else "جستجو",
        extra={"query": query, "is_search": True},
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.active().with_related().prefetch_related("specs"), slug=slug
    )
    related = list(
        Product.objects.active()
        .filter(category=product.category)
        .exclude(pk=product.pk)
        .with_related()[:8]
    )
    if len(related) < 4 and product.category.parent_id:
        related += list(
            Product.objects.active()
            .filter(category__parent=product.category.parent_id)
            .exclude(pk__in=[product.pk, *[item.pk for item in related]])
            .with_related()[: 8 - len(related)]
        )

    images = product.ordered_images
    structured_data = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": product.name,
        "sku": product.sku or str(product.pk),
        "brand": {"@type": "Brand", "name": product.brand.name_en or product.brand.name},
        "description": strip_tags(product.short_description or product.description)[:300],
        "image": [request.build_absolute_uri(image.image.url) for image in images],
        "offers": {
            "@type": "Offer",
            "priceCurrency": "IRR",
            "price": product.price * 10,
            "availability": "https://schema.org/InStock" if product.in_stock else "https://schema.org/OutOfStock",
            "url": request.build_absolute_uri(product.get_absolute_url()),
        },
    }
    return render(
        request,
        "catalog/product_detail.html",
        {
            "product": product,
            "images": images,
            "related": related,
            "structured_data": json.dumps(structured_data, ensure_ascii=False),
        },
    )


def search_suggest(request):
    query = normalize_query(request.GET.get("q", ""))
    if len(query) < 2:
        return JsonResponse({"products": [], "categories": [], "brands": []})
    products = search_products(Product.objects.active(), query).with_related()[:6]
    categories = Category.objects.active().filter(name__icontains=query).select_related("parent")[:4]
    brands = Brand.objects.filter(is_active=True).filter(Q(name__icontains=query) | Q(name_en__icontains=query))[:4]
    return JsonResponse(
        {
            "products": [
                {
                    "name": product.name,
                    "name_en": product.name_en,
                    "brand": product.brand.name,
                    "price": format_number(product.price),
                    "url": product.get_absolute_url(),
                    "image": thumbnail_url(product.main_image.image, 160) if product.main_image else "",
                }
                for product in products
            ],
            "categories": [{"name": c.title, "url": c.get_absolute_url()} for c in categories],
            "brands": [{"name": b.name, "url": b.get_absolute_url()} for b in brands],
            "all_url": f"{reverse('catalog:search')}?{urlencode({'q': query})}",
        }
    )
