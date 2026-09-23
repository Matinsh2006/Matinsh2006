from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "price",
        "duration_minutes",
        "deposit_amount",
        "is_active",
        "order",
    ]
    list_editable = ["is_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["name", "short_description", "description"]
    prepopulated_fields = {"slug": ("name",)}
