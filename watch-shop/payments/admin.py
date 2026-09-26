from django.contrib import admin

from core.utils import format_number

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "gateway_title", "amount_display", "status", "ref_id", "created_at")
    list_filter = ("status", "gateway")
    search_fields = ("order__number", "authority", "ref_id", "order__user__phone")
    list_select_related = ("order",)
    readonly_fields = [field.name for field in Payment._meta.fields]

    @admin.display(description="درگاه")
    def gateway_title(self, obj):
        return obj.get_gateway_display()

    @admin.display(description="مبلغ (تومان)", ordering="amount")
    def amount_display(self, obj):
        return format_number(obj.amount_toman)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
