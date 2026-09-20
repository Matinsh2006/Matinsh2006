from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Order


class PaymentStatus(models.TextChoices):
    CREATED = "created", _("ایجاد شده")
    REDIRECTED = "redirected", _("هدایت به درگاه")
    SUCCESS = "success", _("موفق")
    FAILED = "failed", _("ناموفق")
    CANCELED = "canceled", _("لغو توسط کاربر")


class Payment(models.Model):
    """تراکنش پرداخت یک سفارش."""

    order = models.ForeignKey(
        Order, verbose_name=_("سفارش"), on_delete=models.CASCADE, related_name="payments"
    )
    gateway = models.CharField(_("درگاه"), max_length=30, default="dummy")
    amount = models.PositiveIntegerField(_("مبلغ (تومان)"))
    authority = models.CharField(_("شناسه تراکنش درگاه"), max_length=120, blank=True, db_index=True)
    ref_id = models.CharField(_("کد رهگیری بانک"), max_length=120, blank=True)
    status = models.CharField(
        _("وضعیت"), max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.CREATED
    )
    error_message = models.CharField(_("پیام خطا"), max_length=250, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(_("زمان تایید"), blank=True, null=True)

    class Meta:
        verbose_name = _("پرداخت")
        verbose_name_plural = _("پرداخت‌ها")
        ordering = ["-created_at"]

    def __str__(self):
        return f"پرداخت {self.order.ref_code} - {self.get_status_display()}"
