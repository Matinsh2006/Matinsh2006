import uuid

from django.db import models


class Payment(models.Model):
    """One attempt to pay an order through an online gateway."""

    class Status(models.TextChoices):
        INITIATED = "initiated", "ایجاد شده"
        REDIRECTED = "redirected", "ارسال به درگاه"
        SUCCESS = "success", "موفق"
        FAILED = "failed", "ناموفق"

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    order = models.ForeignKey(
        "orders.Order", verbose_name="سفارش", on_delete=models.PROTECT, related_name="payments"
    )
    gateway = models.CharField("درگاه", max_length=30)
    amount = models.PositiveBigIntegerField("مبلغ (تومان)")
    status = models.CharField("وضعیت", max_length=20, choices=Status.choices, default=Status.INITIATED, db_index=True)
    authority = models.CharField("شناسه تراکنش درگاه", max_length=100, blank=True, db_index=True)
    ref_id = models.CharField("کد پیگیری بانکی", max_length=100, blank=True)
    card_pan = models.CharField("شماره کارت (ماسک‌شده)", max_length=30, blank=True)
    message = models.CharField("پیام درگاه", max_length=255, blank=True)
    raw_data = models.JSONField("پاسخ خام درگاه", default=dict, blank=True)
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)
    verified_at = models.DateTimeField("زمان تایید", null=True, blank=True)

    class Meta:
        verbose_name = "تراکنش پرداخت"
        verbose_name_plural = "تراکنش‌های پرداخت"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_gateway_display()} – {self.amount} تومان ({self.get_status_display()})"

    def get_gateway_display(self):
        from .gateways import GATEWAY_TITLES

        return GATEWAY_TITLES.get(self.gateway, self.gateway)

    @property
    def is_success(self):
        return self.status == self.Status.SUCCESS
