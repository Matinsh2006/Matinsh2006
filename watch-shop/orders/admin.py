from django.contrib import admin

from core.utils import format_number
from payments.models import Payment

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "product_name", "product_sku", "unit_price", "quantity")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ("gateway", "amount", "status", "ref_id", "card_pan", "created_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "recipient_name", "total_display", "status", "created_at", "paid_at")
    list_filter = ("status", "created_at")
    list_editable = ("status",)
    search_fields = ("number", "user__phone", "recipient_name", "recipient_phone", "tracking_code")
    list_select_related = ("user",)
    date_hierarchy = "created_at"
    inlines = [OrderItemInline, PaymentInline]
    readonly_fields = ("number", "user", "subtotal", "shipping_cost", "total", "created_at", "paid_at")
    fieldsets = (
        (None, {"fields": ("number", "user", "status", "tracking_code")}),
        ("گیرنده", {"fields": ("recipient_name", "recipient_phone", ("province", "city"), "postal_code", "address", "note")}),
        ("مبالغ (تومان)", {"fields": (("subtotal", "shipping_cost", "total"),)}),
        ("زمان‌ها", {"fields": (("created_at", "paid_at"),)}),
    )

    @admin.display(description="مبلغ (تومان)", ordering="total")
    def total_display(self, obj):
        return format_number(obj.total)

    def has_add_permission(self, request):
        return False
