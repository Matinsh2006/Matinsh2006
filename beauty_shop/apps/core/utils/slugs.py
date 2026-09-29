from django.utils.text import slugify


def unique_slugify(instance, value, slug_field="slug"):
    """Build a unique (Persian-friendly) slug for ``instance`` from ``value``."""
    max_length = instance._meta.get_field(slug_field).max_length
    base = slugify((value or "").replace("‌", " "), allow_unicode=True)
    base = base[:max_length].strip("-") or "item"
    queryset = type(instance)._default_manager.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    slug, counter = base, 2
    while queryset.filter(**{slug_field: slug}).exists():
        suffix = f"-{counter}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        counter += 1
    return slug
