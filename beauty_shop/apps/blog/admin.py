from django.contrib import admin, messages

from apps.core.admin_utils import image_thumb, jalali_display

from .models import Article, ArticleCategory


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "title", "category", "status", "is_featured", "published", "views")
    list_display_links = ("thumbnail", "title")
    list_editable = ("status", "is_featured")
    list_filter = ("status", "is_featured", "category")
    search_fields = ("title", "summary", "body")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "related_products")
    readonly_fields = ("views", "author", "created_at", "updated_at")
    save_on_top = True
    actions = ("publish", "unpublish")
    fieldsets = (
        (None, {"fields": ("title", "slug", "category", "cover", "summary", "body")}),
        ("انتشار", {"fields": ("status", "published_at", "is_featured")}),
        ("محصولات مرتبط", {"fields": ("related_products",)}),
        ("اطلاعات", {"fields": ("author", "views", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="تصویر")
    def thumbnail(self, obj):
        return image_thumb(obj.cover, "admin-thumb admin-thumb--wide")

    @admin.display(description="زمان انتشار", ordering="published_at")
    def published(self, obj):
        return jalali_display(obj.published_at)

    @admin.action(description="انتشار مقالات انتخاب‌شده")
    def publish(self, request, queryset):
        updated = queryset.update(status=Article.Status.PUBLISHED)
        self.message_user(request, f"{updated} مقاله منتشر شد.", messages.SUCCESS)

    @admin.action(description="تبدیل به پیش‌نویس")
    def unpublish(self, request, queryset):
        updated = queryset.update(status=Article.Status.DRAFT)
        self.message_user(request, f"{updated} مقاله به پیش‌نویس تبدیل شد.", messages.SUCCESS)
