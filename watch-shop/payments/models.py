from django.db import models
from django.db.models import Q

from orders.models import Order


class Payment(models.Model):
    """One attempt to pay an order through an online gateway."""

    class Status(models.TextChoices):
        INITIATED = "initiated", "ایجاد شده"
        REDIRECTED = "redirected", "هدایت به درگاه"
        PAID = "paid", "موفق"
        FAILED = "failed", "ناموفق"
        CANCELED = "canceled", "انصراف از پرداخت"

    order = models.ForeignKey(Order, verbose_name="سفارش", related_name="payments", on_delete=models.CASCADE)
    gateway = models.CharField("درگاه", max_length=20)
    amount = models.PositiveBigIntegerField("مبلغ (ریال)")
    status = models.CharField(
        "وضعیت", max_length=20, choices=Status.choices, default=Status.INITIATED, db_index=True
    )
    authority = models.CharField("شناسه تراکنش درگاه", max_length=100, blank=True, db_index=True)
    ref_id = models.CharField("کد پیگیری بانکی", max_length=100, blank=True)
    card_pan = models.CharField("شماره کارت", max_length=30, blank=True)
    message = models.CharField("پیام", max_length=255, blank=True)
    request_data = models.JSONField("پاسخ درخواست", default=dict, blank=True)
    verify_data = models.JSONField("پاسخ تایید", default=dict, blank=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)
    verified_at = models.DateTimeField("زمان تایید", null=True, blank=True)

    class Meta:
        verbose_name = "تراکنش پرداخت"
        verbose_name_plural = "تراکنش‌های پرداخت"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["gateway", "authority"],
                condition=~Q(authority=""),
                name="payments_unique_gateway_authority",
            )
        ]

    def __str__(self):
        return f"{self.get_gateway_display()} - {self.order.number}"

    def get_gateway_display(self):
        from .gateways import GATEWAY_TITLES

        return GATEWAY_TITLES.get(self.gateway, self.gateway)

    @property
    def amount_toman(self):
        return self.amount // 10
