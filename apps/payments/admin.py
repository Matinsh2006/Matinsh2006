from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "gateway", "amount", "status", "ref_id", "created_at")
    list_filter = ("gateway", "status")
    search_fields = ("order__ref_code", "authority", "ref_id")
    readonly_fields = ("created_at", "verified_at")
