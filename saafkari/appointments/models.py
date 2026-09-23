"""رزرو نوبت با تاریخ شمسی، همراه با عکس‌های خودرو از زاویه‌های مختلف."""
from __future__ import annotations

import datetime as dt
import secrets
import string

from django.conf import settings as django_settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.jalali import format_jalali, jalali_weekday
from core.models import TimeStampedModel
from core.validators import normalize_phone

WEEKDAY_CHOICES = [
    (0, _("شنبه")), (1, _("یکشنبه")), (2, _("دوشنبه")), (3, _("سه‌شنبه")),
    (4, _("چهارشنبه")), (5, _("پنجشنبه")), (6, _("جمعه")),
]


class WorkingHour(models.Model):
    """ساعت کاری مغازه در هر روز هفته (مبنای ساخت نوبت‌های خالی)."""

    weekday = models.PositiveSmallIntegerField(_("روز هفته"), choices=WEEKDAY_CHOICES, unique=True)
    is_open = models.BooleanField(_("باز است"), default=True)
    open_time = models.TimeField(_("ساعت شروع"), default=dt.time(9, 0))
    close_time = models.TimeField(_("ساعت پایان"), default=dt.time(20, 0))
    slot_minutes = models.PositiveSmallIntegerField(
        _("فاصله‌ی نوبت‌ها (دقیقه)"), default=60,
        help_text=_("مثلاً ۶۰ یعنی نوبت‌ها ساعت ۹:۰۰، ۱۰:۰۰ و ... باشند."),
    )
    capacity = models.PositiveSmallIntegerField(
        _("ظرفیت هم‌زمان"), default=1,
        help_text=_("چند خودرو را می‌توانید هم‌زمان در یک بازه بپذیرید."),
    )

    class Meta:
        verbose_name = _("ساعت کاری")
        verbose_name_plural = _("ساعت‌های کاری")
        ordering = ("weekday",)

    def __str__(self):
        if not self.is_open:
            return f"{self.get_weekday_display()} — تعطیل"
        return f"{self.get_weekday_display()} — {self.open_time:%H:%M} تا {self.close_time:%H:%M}"

    @classmethod
    def ensure_defaults(cls):
        """ساخت ساعت‌های کاری پیش‌فرض (شنبه تا پنجشنبه باز، جمعه تعطیل)."""
        for weekday, _label in WEEKDAY_CHOICES:
            cls.objects.get_or_create(weekday=weekday, defaults={"is_open": weekday != 6})


class Holiday(models.Model):
    """روز تعطیل مغازه (تعطیلات رسمی یا تعطیلی موردی)."""

    date = models.DateField(_("تاریخ"), unique=True)
    title = models.CharField(_("مناسبت"), max_length=120, blank=True, default="")

    class Meta:
        verbose_name = _("روز تعطیل")
        verbose_name_plural = _("روزهای تعطیل")
        ordering = ("date",)

    def __str__(self):
        return f"{format_jalali(self.date)} — {self.title or 'تعطیل'}"

    @property
    def jalali_date(self) -> str:
        return format_jalali(self.date)


class AppointmentQuerySet(models.QuerySet):
    def active(self):
        """نوبت‌هایی که هنوز لغو/رد نشده‌اند."""
        return self.exclude(status__in=[Appointment.Status.CANCELLED, Appointment.Status.REJECTED])

    def upcoming(self):
        return self.active().filter(date__gte=timezone.localdate())


class Appointment(TimeStampedModel):
    """درخواست نوبت مشتری."""

    class Status(models.TextChoices):
        PENDING = "pending", _("در انتظار تایید")
        CONFIRMED = "confirmed", _("تایید شده")
        IN_PROGRESS = "in_progress", _("در حال انجام")
        DONE = "done", _("انجام شده")
        CANCELLED = "cancelled", _("لغو شده توسط مشتری")
        REJECTED = "rejected", _("رد شده توسط مغازه")

    #: وضعیت‌هایی که ظرفیت نوبت را اشغال می‌کنند
    BLOCKING_STATUSES = (Status.PENDING, Status.CONFIRMED, Status.IN_PROGRESS)

    tracking_code = models.CharField(_("کد پیگیری"), max_length=10, unique=True, blank=True)
    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, verbose_name=_("مشتری"), related_name="appointments",
        on_delete=models.CASCADE,
    )
    service = models.ForeignKey(
        "services.Service", verbose_name=_("خدمت"), related_name="appointments",
        on_delete=models.PROTECT,
    )
    contact_phone = models.CharField(_("شماره تماس"), max_length=11, blank=True, default="")

    date = models.DateField(_("تاریخ نوبت"), help_text=_("تاریخ به صورت شمسی از تقویم انتخاب می‌شود."))
    start_time = models.TimeField(_("ساعت شروع"))
    end_time = models.TimeField(_("ساعت پایان"), null=True, blank=True)

    car_model = models.CharField(_("خودرو"), max_length=120, blank=True, default="")
    plate_number = models.CharField(_("شماره پلاک"), max_length=20, blank=True, default="")
    description = models.TextField(
        _("توضیحات مشتری"),
        help_text=_("آسیب خودرو را شرح دهید: محل ضربه، میزان خرابی و خواسته‌ی شما."),
    )

    status = models.CharField(_("وضعیت"), max_length=20, choices=Status.choices, default=Status.PENDING)
    staff_note = models.TextField(_("یادداشت مغازه"), blank=True, default="")
    estimated_price = models.PositiveIntegerField(_("برآورد هزینه (تومان)"), null=True, blank=True)

    deposit_amount = models.PositiveIntegerField(_("مبلغ بیعانه (تومان)"), default=0)
    is_deposit_paid = models.BooleanField(_("بیعانه پرداخت شده"), default=False)
    deposit_paid_at = models.DateTimeField(_("زمان پرداخت بیعانه"), null=True, blank=True)

    objects = AppointmentQuerySet.as_manager()

    class Meta:
        verbose_name = _("نوبت")
        verbose_name_plural = _("نوبت‌ها")
        ordering = ("-date", "-start_time")
        indexes = [
            models.Index(fields=["date", "start_time"]),
            models.Index(fields=["status", "-date"]),
        ]

    def __str__(self):
        return f"{self.tracking_code} — {self.user} — {self.jalali_date}"

    # ------------------------------------------------------------------ ذخیره
    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.tracking_code = self.generate_tracking_code()
        if not self.contact_phone and self.user_id:
            self.contact_phone = self.user.phone
        self.contact_phone = normalize_phone(self.contact_phone) or self.contact_phone
        if not self.end_time and self.start_time and self.service_id:
            self.end_time = self.compute_end_time()
        if not self.deposit_amount and self.service_id:
            self.deposit_amount = self.service.deposit_for_booking()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_tracking_code() -> str:
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = "".join(secrets.choice(alphabet) for _ in range(8))
            if not Appointment.objects.filter(tracking_code=code).exists():
                return code

    def compute_end_time(self) -> dt.time:
        duration = self.service.duration_minutes or 60
        start = dt.datetime.combine(self.date or timezone.localdate(), self.start_time)
        return (start + dt.timedelta(minutes=duration)).time()

    # ------------------------------------------------------------------ نمایش
    def get_absolute_url(self):
        return reverse("appointments:detail", kwargs={"code": self.tracking_code})

    @property
    def jalali_date(self) -> str:
        return format_jalali(self.date, "%A %d %B %Y")

    @property
    def jalali_date_short(self) -> str:
        return format_jalali(self.date, "%Y/%m/%d")

    @property
    def time_range(self) -> str:
        if self.end_time:
            return f"{self.start_time:%H:%M} تا {self.end_time:%H:%M}"
        return f"{self.start_time:%H:%M}"

    @property
    def status_color(self) -> str:
        """کلاس رنگ برای نمایش وضعیت در قالب."""
        return {
            self.Status.PENDING: "bg-amber-100 text-amber-800 ring-amber-200",
            self.Status.CONFIRMED: "bg-emerald-100 text-emerald-800 ring-emerald-200",
            self.Status.IN_PROGRESS: "bg-sky-100 text-sky-800 ring-sky-200",
            self.Status.DONE: "bg-slate-200 text-slate-800 ring-slate-300",
            self.Status.CANCELLED: "bg-rose-100 text-rose-800 ring-rose-200",
            self.Status.REJECTED: "bg-rose-100 text-rose-800 ring-rose-200",
        }.get(self.status, "bg-slate-100 text-slate-700 ring-slate-200")

    @property
    def is_past(self) -> bool:
        return self.date < timezone.localdate()

    @property
    def can_cancel(self) -> bool:
        """تا پیش از شروع نوبت و در وضعیت‌های اولیه، امکان لغو هست."""
        return self.status in {self.Status.PENDING, self.Status.CONFIRMED} and not self.is_past

    @property
    def needs_deposit(self) -> bool:
        from core.models import SiteSettings

        site = SiteSettings.load()
        return bool(
            site.online_payment_enabled
            and self.deposit_amount
            and not self.is_deposit_paid
            and self.status in {self.Status.PENDING, self.Status.CONFIRMED}
        )

    def mark_deposit_paid(self):
        self.is_deposit_paid = True
        self.deposit_paid_at = timezone.now()
        if self.status == self.Status.PENDING:
            self.status = self.Status.CONFIRMED
        self.save(update_fields=["is_deposit_paid", "deposit_paid_at", "status", "updated_at"])


class AppointmentPhoto(models.Model):
    """
    عکس‌های خودرو که مشتری هنگام ثبت نوبت می‌فرستد.

    برای هر زاویه یک باکس جدا در فرم وجود دارد تا مشتری بتواند چند نما از
    خودرو را ارسال کند.
    """

    class Angle(models.TextChoices):
        FRONT = "front", _("جلوی خودرو")
        BACK = "back", _("عقب خودرو")
        LEFT = "left", _("سمت چپ")
        RIGHT = "right", _("سمت راست")
        CLOSEUP = "closeup", _("نمای نزدیک آسیب")
        ROOF = "roof", _("سقف / کاپوت")
        OTHER = "other", _("سایر")

    appointment = models.ForeignKey(
        Appointment, verbose_name=_("نوبت"), related_name="photos", on_delete=models.CASCADE
    )
    image = models.ImageField(_("عکس خودرو"), upload_to="appointments/%Y/%m/")
    angle = models.CharField(_("زاویه عکس"), max_length=10, choices=Angle.choices, default=Angle.OTHER)
    caption = models.CharField(_("توضیح عکس"), max_length=150, blank=True, default="")
    uploaded_at = models.DateTimeField(_("زمان بارگذاری"), auto_now_add=True)

    class Meta:
        verbose_name = _("عکس نوبت")
        verbose_name_plural = _("عکس‌های نوبت")
        ordering = ("angle", "id")

    def __str__(self):
        return f"{self.appointment.tracking_code} — {self.get_angle_display()}"
