from django.contrib import admin

from .models import PortfolioImage, PortfolioItem


class PortfolioImageInline(admin.TabularInline):
    model = PortfolioImage
    extra = 3
    fields = ["image", "image_type", "order"]


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ["title", "is_published", "order", "created_at"]
    list_editable = ["is_published", "order"]
    search_fields = ["title", "description"]
    inlines = [PortfolioImageInline]
