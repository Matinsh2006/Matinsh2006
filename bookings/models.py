from django.conf import settings
from django.db import models

from accounts.models import phone_validator
from services.models import Service


class Appointment(models.Model):
    STATUS_AWAITING_DEPOSIT = "awaiting_deposit"
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_DONE = "done"
    STATUS_CHOICES = [
        (STATUS_AWAITING_DEPOSIT, "در انتظار پرداخت بیعانه"),
        (STATUS_PENDING, "در انتظار بررسی و تایید"),
        (STATUS_CONFIRMED, "تایید شده"),
        (STATUS_CANCELLED, "لغو شده"),
        (STATUS_DONE, "انجام شده"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
        verbose_name="مشتری",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="خدمت",
    )
    full_name = models.CharField("نام و نام خانوادگی", max_length=150)
    phone_number = models.CharField(
        "شماره تماس", max_length=11, validators=[phone_validator]
    )
    notes = models.TextField("توضیحات مشتری", blank=True)

    date = models.DateField("تاریخ نوبت")
    start_time = models.TimeField("ساعت شروع")
    end_time = models.TimeField("ساعت پایان")

    status = models.CharField(
        "وضعیت", max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    admin_notes = models.TextField("یادداشت داخلی", blank=True)
    created_at = models.DateTimeField("زمان ثبت", auto_now_add=True)

    class Meta:
        verbose_name = "نوبت"
        verbose_name_plural = "نوبت‌ها"
        ordering = ["date", "start_time"]

    def __str__(self):
        return f"{self.full_name} - {self.service.name} - {self.date}"

    @property
    def requires_deposit(self):
        return self.service.deposit_amount > 0

    @property
    def is_paid(self):
        payment = getattr(self, "payment", None)
        return bool(payment and payment.status == payment.STATUS_SUCCESS)
