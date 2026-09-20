import secrets

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import ProductVariant


class Cart(models.Model):
    """سبد خرید؛ هم برای کاربر مهمان (کلید سشن) و هم کاربر وارد شده."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("کاربر"),
        on_delete=models.CASCADE,
        related_name="cart",
        blank=True,
        null=True,
    )
    session_key = models.CharField(_("کلید سشن"), max_length=60, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("سبد خرید")
        verbose_name_plural = _("سبدهای خرید")

    def __str__(self):
        return f"سبد {self.user or self.session_key}"

    @property
    def items_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    def merge_from(self, other):
        """ادغام سبد مهمان با سبد کاربر پس از ورود."""
        for item in other.items.all():
            existing = self.items.filter(variant=item.variant).first()
            if existing:
                existing.quantity = min(existing.quantity + item.quantity, item.variant.stock or 1)
                existing.save(update_fields=["quantity"])
            else:
                item.cart = self
                item.save(update_fields=["cart"])
        other.delete()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant, verbose_name=_("تنوع محصول"), on_delete=models.CASCADE
    )
    quantity = models.PositiveSmallIntegerField(_("تعداد"), default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("قلم سبد خرید")
        verbose_name_plural = _("اقلام سبد خرید")
        unique_together = [("cart", "variant")]
        ordering = ["added_at"]

    def __str__(self):
        return f"{self.variant} × {self.quantity}"

    @property
    def unit_price(self):
        return self.variant.price

    @property
    def total_price(self):
        return self.unit_price * self.quantity


class OrderStatus(models.TextChoices):
    PENDING = "pending", _("در انتظار پرداخت")
    PAID = "paid", _("پرداخت شده")
    PROCESSING = "processing", _("در حال آماده‌سازی")
    SHIPPED = "shipped", _("ارسال شده")
    DELIVERED = "delivered", _("تحویل شده")
    CANCELED = "canceled", _("لغو شده")


class Order(models.Model):
    """سفارش ثبت‌شده کاربر."""

    ref_code = models.CharField(_("کد پیگیری"), max_length=20, unique=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("کاربر"),
        on_delete=models.SET_NULL,
        related_name="orders",
        blank=True,
        null=True,
    )
    full_name = models.CharField(_("نام گیرنده"), max_length=150)
    phone = models.CharField(_("شماره تماس"), max_length=11)
    province = models.CharField(_("استان"), max_length=60, blank=True)
    city = models.CharField(_("شهر"), max_length=60)
    address = models.TextField(_("آدرس"))
    postal_code = models.CharField(_("کد پستی"), max_length=10, blank=True)
    note = models.TextField(_("توضیحات"), blank=True)
    items_price = models.PositiveIntegerField(_("جمع کالاها"), default=0)
    shipping_cost = models.PositiveIntegerField(_("هزینه ارسال"), default=0)
    total_price = models.PositiveIntegerField(_("مبلغ نهایی"), default=0)
    status = models.CharField(
        _("وضعیت"), max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING
    )
    created_at = models.DateTimeField(_("تاریخ ثبت"), auto_now_add=True)
    paid_at = models.DateTimeField(_("تاریخ پرداخت"), blank=True, null=True)

    class Meta:
        verbose_name = _("سفارش")
        verbose_name_plural = _("سفارش‌ها")
        ordering = ["-created_at"]

    def __str__(self):
        return f"سفارش {self.ref_code}"

    def save(self, *args, **kwargs):
        if not self.ref_code:
            self.ref_code = self.generate_ref_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_ref_code():
        while True:
            code = str(secrets.randbelow(10**9)).zfill(9)
            if not Order.objects.filter(ref_code=code).exists():
                return code

    @property
    def is_paid(self):
        return self.status not in {OrderStatus.PENDING, OrderStatus.CANCELED}

    def recalculate(self, shipping_cost=None):
        self.items_price = sum(item.total_price for item in self.items.all())
        if shipping_cost is not None:
            self.shipping_cost = shipping_cost
        self.total_price = self.items_price + self.shipping_cost
        return self.total_price


class OrderItem(models.Model):
    """قلم سفارش؛ اطلاعات محصول در زمان خرید ذخیره می‌شود."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(
        ProductVariant, on_delete=models.SET_NULL, blank=True, null=True, related_name="order_items"
    )
    product_title = models.CharField(_("نام محصول"), max_length=200)
    variant_label = models.CharField(_("سایز و رنگ"), max_length=120, blank=True)
    unit_price = models.PositiveIntegerField(_("قیمت واحد"))
    quantity = models.PositiveSmallIntegerField(_("تعداد"), default=1)

    class Meta:
        verbose_name = _("قلم سفارش")
        verbose_name_plural = _("اقلام سفارش")

    def __str__(self):
        return f"{self.product_title} × {self.quantity}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity
