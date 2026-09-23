"""پرداخت بیعانه‌ی نوبت."""
from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel


class Payment(TimeStampedModel):
    """یک تراکنش پرداخت (بیعانه یا تسویه)."""

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار پرداخت")
        PAID = "paid", _("پرداخت موفق")
        FAILED = "failed", _("ناموفق")
        CANCELLED = "cancelled", _("انصراف کاربر")
        REFUNDED = "refunded", _("بازگشت وجه")

    class Kind(models.TextChoices):
        DEPOSIT = "deposit", _("بیعانه")
        SETTLEMENT = "settlement", _("تسویه نهایی")

    appointment = models.ForeignKey(
        "appointments.Appointment", verbose_name=_("نوبت"), related_name="payments",
        on_delete=models.CASCADE, null=True, blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("پرداخت‌کننده"), related_name="payments",
        on_delete=models.CASCADE,
    )
    invoice_number = models.CharField(_("شماره فاکتور"), max_length=20, unique=True, blank=True)
    kind = models.CharField(_("نوع پرداخت"), max_length=20, choices=Kind.choices, default=Kind.DEPOSIT)
    amount = models.PositiveIntegerField(_("مبلغ (تومان)"))
    description = models.CharField(_("بابت"), max_length=200, blank=True, default="")

    gateway = models.CharField(_("درگاه"), max_length=40, default="sandbox")
    authority = models.CharField(_("کد رهگیری درگاه"), max_length=120, blank=True, default="", db_index=True)
    ref_id = models.CharField(_("شماره پیگیری بانک"), max_length=60, blank=True, default="")
    card_pan = models.CharField(_("شماره کارت"), max_length=30, blank=True, default="")

    status = models.CharField(_("وضعیت"), max_length=20, choices=Status.choices, default=Status.PENDING)
    paid_at = models.DateTimeField(_("زمان پرداخت"), null=True, blank=True)
    gateway_response = models.JSONField(_("پاسخ درگاه"), default=dict, blank=True)

    class Meta:
        verbose_name = _("پرداخت")
        verbose_name_plural = _("پرداخت‌ها")
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.invoice_number} — {self.amount:,} تومان — {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_invoice_number() -> str:
        """
        شماره فاکتور یکتا: تاریخ + شش رقم تصادفی.

        فضای تصادفی به اندازه‌ای بزرگ است که احتمال برخورد ناچیز باشد و
        علاوه بر آن، یکتایی در پایگاه داده هم بررسی می‌شود.
        """
        for _ in range(12):
            number = f"{timezone.now():%y%m%d}{secrets.randbelow(1_000_000):06d}"
            if not Payment.objects.filter(invoice_number=number).exists():
                return number
        # حالت بسیار نادر: افزودن رقم بیشتر برای تضمین یکتایی
        return f"{timezone.now():%y%m%d}{secrets.token_hex(3)}"

    def get_absolute_url(self):
        return reverse("payments:receipt", kwargs={"invoice": self.invoice_number})

    @property
    def amount_rial(self) -> int:
        return self.amount * 10

    @property
    def is_paid(self) -> bool:
        return self.status == self.Status.PAID

    @property
    def status_color(self) -> str:
        return {
            self.Status.PENDING: "bg-amber-100 text-amber-800 ring-amber-200",
            self.Status.PAID: "bg-emerald-100 text-emerald-800 ring-emerald-200",
            self.Status.FAILED: "bg-rose-100 text-rose-800 ring-rose-200",
            self.Status.CANCELLED: "bg-slate-200 text-slate-700 ring-slate-300",
            self.Status.REFUNDED: "bg-sky-100 text-sky-800 ring-sky-200",
        }.get(self.status, "bg-slate-100 text-slate-700 ring-slate-200")

    def mark_paid(self, ref_id: str = "", card_pan: str = "", response: dict | None = None):
        """ثبت پرداخت موفق و قطعی‌کردن بیعانه‌ی نوبت."""
        self.status = self.Status.PAID
        self.ref_id = ref_id or self.ref_id
        self.card_pan = card_pan or self.card_pan
        self.paid_at = timezone.now()
        if response is not None:
            self.gateway_response = response
        self.save(update_fields=["status", "ref_id", "card_pan", "paid_at", "gateway_response", "updated_at"])
        if self.appointment_id and self.kind == self.Kind.DEPOSIT:
            self.appointment.mark_deposit_paid()

    def mark_failed(self, status: str | None = None, response: dict | None = None):
        self.status = status or self.Status.FAILED
        if response is not None:
            self.gateway_response = response
        self.save(update_fields=["status", "gateway_response", "updated_at"])
