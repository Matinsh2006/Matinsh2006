from django.contrib import admin

from .models import Service, ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "is_active")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "price_label", "duration_minutes", "is_active", "is_featured", "order")
    list_editable = ("is_active", "is_featured", "order")
    list_filter = ("is_active", "is_featured", "category")
    search_fields = ("title", "short_description", "description")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "image")}),
        ("توضیحات", {"fields": ("short_description", "description")}),
        ("قیمت و زمان", {"fields": ("base_price", "price_note", "duration_minutes", "deposit_amount")}),
        ("نمایش", {"fields": ("is_active", "is_featured", "order")}),
    )
