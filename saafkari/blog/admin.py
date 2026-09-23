from django.contrib import admin

from .models import Article, ArticleCategory


@admin.register(ArticleCategory)
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "author", "published_at", "is_published", "is_featured", "views_count")
    list_editable = ("is_published", "is_featured")
    list_filter = ("is_published", "is_featured", "category")
    search_fields = ("title", "summary", "content", "tags")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    readonly_fields = ("views_count",)

    def save_model(self, request, obj, form, change):
        if obj.author is None:
            obj.author = request.user
        super().save_model(request, obj, form, change)
