from django.contrib import admin

from apps.core.admin_utils import jalali_display
from apps.core.templatetags.shop_tags import price

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "gateway_title", "amount_display", "status", "ref_id", "created")
    list_filter = ("status", "gateway")
    search_fields = ("order__number", "ref_id", "authority", "order__user__phone")
    list_select_related = ("order",)
    readonly_fields = (
        "uuid",
        "order",
        "gateway",
        "amount",
        "status",
        "authority",
        "ref_id",
        "card_pan",
        "message",
        "raw_data",
        "created_at",
        "verified_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="درگاه", ordering="gateway")
    def gateway_title(self, obj):
        return obj.get_gateway_display()

    @admin.display(description="مبلغ (تومان)", ordering="amount")
    def amount_display(self, obj):
        return price(obj.amount)

    @admin.display(description="زمان", ordering="created_at")
    def created(self, obj):
        return jalali_display(obj.created_at)
