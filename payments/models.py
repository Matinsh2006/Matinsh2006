from django.db import models

from bookings.models import Appointment


class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار پرداخت"),
        (STATUS_SUCCESS, "موفق"),
        (STATUS_FAILED, "ناموفق"),
    ]

    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name="payment",
        verbose_name="نوبت",
    )
    amount = models.PositiveIntegerField("مبلغ بیعانه (تومان)")
    authority = models.CharField("کد Authority زرین‌پال", max_length=64, blank=True)
    ref_id = models.CharField("کد پیگیری تراکنش", max_length=64, blank=True)
    card_pan = models.CharField("شماره کارت پرداخت‌کننده", max_length=32, blank=True)
    status = models.CharField(
        "وضعیت", max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    created_at = models.DateTimeField("زمان ایجاد", auto_now_add=True)
    paid_at = models.DateTimeField("زمان پرداخت موفق", null=True, blank=True)

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.appointment} - {self.get_status_display()}"
