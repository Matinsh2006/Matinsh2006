import secrets

from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.urls import reverse
from django.utils import timezone

from catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار پرداخت"
        PAID = "paid", "پرداخت شده"
        PROCESSING = "processing", "در حال آماده‌سازی"
        SHIPPED = "shipped", "ارسال شده"
        DELIVERED = "delivered", "تحویل داده شده"
        CANCELED = "canceled", "لغو شده"

    number = models.CharField("شماره سفارش", max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="مشتری", related_name="orders", on_delete=models.PROTECT
    )
    status = models.CharField("وضعیت", max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    recipient_name = models.CharField("نام گیرنده", max_length=120)
    recipient_phone = models.CharField("موبایل گیرنده", max_length=11)
    province = models.CharField("استان", max_length=40)
    city = models.CharField("شهر", max_length=60)
    postal_code = models.CharField("کد پستی", max_length=10)
    address = models.TextField("نشانی")
    note = models.TextField("توضیحات مشتری", blank=True)

    subtotal = models.PositiveBigIntegerField("جمع کالاها (تومان)")
    shipping_cost = models.PositiveBigIntegerField("هزینه ارسال (تومان)", default=0)
    total = models.PositiveBigIntegerField("مبلغ قابل پرداخت (تومان)")
    tracking_code = models.CharField("کد رهگیری مرسوله", max_length=60, blank=True)

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
            self.number = self._generate_number()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_number():
        while True:
            number = f"{timezone.localtime():%y%m}{secrets.randbelow(900000) + 100000}"
            if not Order.objects.filter(number=number).exists():
                return number

    def get_absolute_url(self):
        return reverse("orders:detail", args=[self.number])

    @property
    def is_payable(self):
        return self.status == self.Status.PENDING

    @property
    def is_paid(self):
        return self.status not in (self.Status.PENDING, self.Status.CANCELED)

    @property
    def status_step(self):
        """Progress index for the order timeline in the profile."""
        steps = [self.Status.PAID, self.Status.PROCESSING, self.Status.SHIPPED, self.Status.DELIVERED]
        return steps.index(self.status) + 1 if self.status in steps else 0

    def unavailable_items(self):
        return [
            item
            for item in self.items.select_related("product")
            if item.product is None or not item.product.is_active or item.product.stock < item.quantity
        ]

    def mark_paid(self):
        """Mark as paid and take the purchased items out of stock (idempotent)."""
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=self.pk)
            if order.status != self.Status.PENDING:
                return False
            for item in order.items.all():
                if item.product_id:
                    Product.objects.filter(pk=item.product_id).update(
                        stock=Greatest(F("stock") - item.quantity, 0)
                    )
            order.status = self.Status.PAID
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at", "updated_at"])
        self.refresh_from_db()
        return True


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, verbose_name="محصول", related_name="order_items", null=True, on_delete=models.SET_NULL
    )
    product_name = models.CharField("نام محصول", max_length=200)
    product_sku = models.CharField("کد محصول", max_length=40, blank=True)
    unit_price = models.PositiveBigIntegerField("قیمت واحد (تومان)")
    quantity = models.PositiveIntegerField("تعداد")

    class Meta:
        verbose_name = "قلم سفارش"
        verbose_name_plural = "اقلام سفارش"

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def total(self):
        return self.unit_price * self.quantity
