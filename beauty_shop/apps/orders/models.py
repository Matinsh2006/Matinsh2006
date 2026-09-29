import secrets

from django.conf import settings
from django.db import models
from django.urls import reverse


def generate_order_number():
    """8-digit, easy to read over the phone."""
    return str(10_000_000 + secrets.randbelow(90_000_000))


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار پرداخت"
        PAID = "paid", "پرداخت‌شده"
        PROCESSING = "processing", "در حال آماده‌سازی"
        SHIPPED = "shipped", "ارسال‌شده"
        DELIVERED = "delivered", "تحویل‌شده"
        CANCELED = "canceled", "لغوشده"

    number = models.CharField("شماره سفارش", max_length=12, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="کاربر", on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField("وضعیت", max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    receiver_name = models.CharField("نام گیرنده", max_length=120)
    receiver_phone = models.CharField("موبایل گیرنده", max_length=11)
    province = models.CharField("استان", max_length=40)
    city = models.CharField("شهر", max_length=60)
    postal_code = models.CharField("کد پستی", max_length=10)
    address = models.TextField("آدرس")
    note = models.TextField("توضیحات مشتری", blank=True)

    items_total = models.PositiveBigIntegerField("جمع کالاها (تومان)", default=0)
    shipping_cost = models.PositiveIntegerField("هزینه ارسال (تومان)", default=0)
    total = models.PositiveBigIntegerField("مبلغ قابل پرداخت (تومان)", default=0)

    tracking_code = models.CharField(
        "کد رهگیری مرسوله", max_length=50, blank=True, help_text="پس از ارسال، کد رهگیری پست را وارد کنید."
    )
    admin_note = models.TextField("یادداشت داخلی مدیر", blank=True)
    created_at = models.DateTimeField("تاریخ ثبت", auto_now_add=True)
    updated_at = models.DateTimeField("آخرین تغییر", auto_now=True)
    paid_at = models.DateTimeField("زمان پرداخت", null=True, blank=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return f"سفارش {self.number}"

    def save(self, *args, **kwargs):
        if not self.number:
            number = generate_order_number()
            while Order.objects.filter(number=number).exists():
                number = generate_order_number()
            self.number = number
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("orders:order_detail", kwargs={"number": self.number})

    @property
    def is_payable(self):
        return self.status == self.Status.PENDING

    @property
    def address_text(self):
        return f"{self.province}، {self.city}، {self.address}"

    @property
    def status_css(self):
        return {
            self.Status.PENDING: "warning",
            self.Status.PAID: "success",
            self.Status.PROCESSING: "info",
            self.Status.SHIPPED: "info",
            self.Status.DELIVERED: "success",
            self.Status.CANCELED: "muted",
        }.get(self.status, "muted")


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name="سفارش", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        "catalog.Product",
        verbose_name="محصول",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    product_name = models.CharField("نام محصول", max_length=200)
    unit_price = models.PositiveIntegerField("قیمت واحد (تومان)")
    original_price = models.PositiveIntegerField("قیمت بدون تخفیف (تومان)")
    quantity = models.PositiveIntegerField("تعداد")

    class Meta:
        verbose_name = "قلم سفارش"
        verbose_name_plural = "اقلام سفارش"

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity
