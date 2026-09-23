from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["appointment", "amount", "status", "ref_id", "created_at", "paid_at"]
    list_filter = ["status"]
    search_fields = [
        "ref_id",
        "authority",
        "appointment__full_name",
        "appointment__phone_number",
    ]
    readonly_fields = [f.name for f in Payment._meta.fields]

    def has_add_permission(self, request):
        return False
