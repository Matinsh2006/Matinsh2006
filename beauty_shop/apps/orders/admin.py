from django.contrib import admin, messages

from apps.core.admin_utils import jalali_display
from apps.core.templatetags.shop_tags import price
from apps.payments.models import Payment

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("product_name", "product", "unit_price", "original_price", "quantity", "line_total")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="جمع (تومان)")
    def line_total(self, obj):
        return price(obj.total_price)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    can_delete = False
    fields = ("gateway", "amount", "status", "ref_id", "card_pan", "message", "created")
    readonly_fields = fields
    verbose_name_plural = "تراکنش‌های پرداخت"

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="زمان")
    def created(self, obj):
        return jalali_display(obj.created_at)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "receiver_name", "total_display", "status", "created", "paid")
    list_filter = ("status",)
    search_fields = ("number", "user__phone", "receiver_name", "receiver_phone", "tracking_code")
    readonly_fields = ("number", "user", "items_total", "shipping_cost", "total", "note", "created", "paid")
    fieldsets = (
        ("سفارش", {"fields": ("number", "user", "status", "tracking_code", "admin_note")}),
        (
            "اطلاعات ارسال",
            {"fields": ("receiver_name", "receiver_phone", "province", "city", "postal_code", "address", "note")},
        ),
        ("مبالغ (تومان)", {"fields": ("items_total", "shipping_cost", "total")}),
        ("زمان‌ها", {"fields": ("created", "paid")}),
    )
    inlines = (OrderItemInline, PaymentInline)
    actions = ("mark_processing", "mark_shipped", "mark_delivered", "mark_canceled")
    list_select_related = ("user",)

    def has_add_permission(self, request):
        return False

    @admin.display(description="مبلغ (تومان)", ordering="total")
    def total_display(self, obj):
        return price(obj.total)

    @admin.display(description="تاریخ ثبت", ordering="created_at")
    def created(self, obj):
        return jalali_display(obj.created_at)

    @admin.display(description="زمان پرداخت", ordering="paid_at")
    def paid(self, obj):
        return jalali_display(obj.paid_at)

    def _set_status(self, request, queryset, status):
        updated = queryset.exclude(status=Order.Status.PENDING).update(status=status)
        skipped = queryset.count() - updated
        self.message_user(request, f"وضعیت {updated} سفارش به «{Order.Status(status).label}» تغییر کرد.", messages.SUCCESS)
        if skipped:
            self.message_user(request, f"{skipped} سفارش پرداخت‌نشده تغییر نکرد.", messages.WARNING)

    @admin.action(description="تغییر وضعیت به «در حال آماده‌سازی»")
    def mark_processing(self, request, queryset):
        self._set_status(request, queryset, Order.Status.PROCESSING)

    @admin.action(description="تغییر وضعیت به «ارسال‌شده»")
    def mark_shipped(self, request, queryset):
        self._set_status(request, queryset, Order.Status.SHIPPED)

    @admin.action(description="تغییر وضعیت به «تحویل‌شده»")
    def mark_delivered(self, request, queryset):
        self._set_status(request, queryset, Order.Status.DELIVERED)

    @admin.action(description="لغو سفارش‌های انتخاب‌شده")
    def mark_canceled(self, request, queryset):
        updated = queryset.update(status=Order.Status.CANCELED)
        self.message_user(request, f"{updated} سفارش لغو شد.", messages.SUCCESS)
