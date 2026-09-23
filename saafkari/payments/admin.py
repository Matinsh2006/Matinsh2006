from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "user", "appointment", "amount", "kind", "gateway", "status", "paid_at")
    list_filter = ("status", "kind", "gateway", "created_at")
    search_fields = ("invoice_number", "authority", "ref_id", "user__phone", "appointment__tracking_code")
    readonly_fields = ("invoice_number", "authority", "ref_id", "card_pan", "gateway_response", "created_at", "updated_at", "paid_at")

    def has_add_permission(self, request):
        return False
