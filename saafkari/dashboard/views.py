"""پنل کارفرما: مدیریت نوبت‌ها، خدمات، نمونه‌کارها، بنرها، مقالات و تنظیمات."""
from __future__ import annotations

import datetime as dt

from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.sms import send_sms
from appointments.forms import AppointmentStatusForm
from appointments.models import Appointment, Holiday, WorkingHour
from blog.models import Article, ArticleCategory
from core.jalali import format_jalali
from core.models import ContactMessage, ShopLocation, SiteSettings, SocialLink
from gallery.models import Banner, PortfolioItem
from payments.models import Payment
from services.models import Service, ServiceCategory

from .forms import (
    ArticleCategoryForm,
    ArticleForm,
    BannerForm,
    HolidayForm,
    PortfolioImageFormSet,
    PortfolioItemForm,
    ServiceCategoryForm,
    ServiceForm,
    ShopLocationForm,
    SiteSettingsForm,
    SocialLinkForm,
    WorkingHourFormSet,
)


class StaffRequiredMixin(UserPassesTestMixin):
    """فقط کارفرما و کارکنان به پنل دسترسی دارند."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(f"{reverse_lazy('accounts:staff_login')}?next={self.request.path}")
        messages.error(self.request, "شما به پنل مدیریت دسترسی ندارید.")
        return redirect("core:home")


def staff_required(view_func):
    """نسخه‌ی تابعی محدودسازی دسترسی کارکنان."""

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse_lazy('accounts:staff_login')}?next={request.path}")
        if not request.user.is_staff:
            messages.error(request, "شما به پنل مدیریت دسترسی ندارید.")
            return redirect("core:home")
        return view_func(request, *args, **kwargs)

    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper


# ---------------------------------------------------------------------------
# صفحه‌ی نخست پنل
# ---------------------------------------------------------------------------
@staff_required
def dashboard_home(request):
    """خلاصه‌ی وضعیت مغازه: نوبت‌های امروز، آمار و درآمد بیعانه."""
    today = timezone.localdate()
    appointments = Appointment.objects.select_related("service", "user")
    paid_deposits = Payment.objects.filter(status=Payment.Status.PAID)
    return render(
        request,
        "dashboard/home.html",
        {
            "today_label": format_jalali(today, "%A %d %B %Y"),
            "today_appointments": appointments.filter(date=today).order_by("start_time"),
            "pending_appointments": appointments.filter(status=Appointment.Status.PENDING).order_by("date")[:10],
            "upcoming_count": appointments.upcoming().count(),
            "stats": {
                "pending": appointments.filter(status=Appointment.Status.PENDING).count(),
                "confirmed": appointments.filter(status=Appointment.Status.CONFIRMED).count(),
                "done": appointments.filter(status=Appointment.Status.DONE).count(),
                "services": Service.objects.count(),
                "portfolio": PortfolioItem.objects.count(),
                "articles": Article.objects.count(),
                "unread_messages": ContactMessage.objects.filter(is_read=False).count(),
                "deposit_total": paid_deposits.aggregate(total=Sum("amount"))["total"] or 0,
                "deposit_month": paid_deposits.filter(
                    paid_at__gte=timezone.now() - dt.timedelta(days=30)
                ).aggregate(total=Sum("amount"))["total"] or 0,
            },
        },
    )


# ---------------------------------------------------------------------------
# نوبت‌ها
# ---------------------------------------------------------------------------
@staff_required
def appointment_list(request):
    """فهرست نوبت‌ها با فیلتر وضعیت و جست‌وجو."""
    appointments = Appointment.objects.select_related("service", "user").prefetch_related("photos")
    status = request.GET.get("status")
    if status in dict(Appointment.Status.choices):
        appointments = appointments.filter(status=status)
    query = (request.GET.get("q") or "").strip()
    if query:
        appointments = appointments.filter(
            Q(tracking_code__icontains=query) | Q(user__phone__icontains=query)
            | Q(user__full_name__icontains=query) | Q(car_model__icontains=query)
            | Q(plate_number__icontains=query)
        )
    return render(
        request,
        "dashboard/appointments.html",
        {
            "appointments": appointments[:100],
            "statuses": Appointment.Status.choices,
            "active_status": status,
            "query": query,
            "counts": dict(
                Appointment.objects.values_list("status").annotate(total=Count("id"))
            ),
        },
    )


@staff_required
def appointment_manage(request, code):
    """مدیریت یک نوبت: تغییر وضعیت، برآورد هزینه و یادداشت."""
    appointment = get_object_or_404(
        Appointment.objects.select_related("service", "user").prefetch_related("photos", "payments"),
        tracking_code=code.upper(),
    )
    form = AppointmentStatusForm(request.POST or None, instance=appointment)
    if request.method == "POST" and form.is_valid():
        previous_status = Appointment.objects.get(pk=appointment.pk).status
        updated = form.save()
        if updated.status != previous_status:
            _notify_status_change(updated)
        messages.success(request, "وضعیت نوبت به‌روزرسانی شد.")
        return redirect("dashboard:appointment_manage", code=updated.tracking_code)
    return render(request, "dashboard/appointment_detail.html", {"appointment": appointment, "form": form})


def _notify_status_change(appointment: Appointment) -> None:
    """پیامک اطلاع‌رسانی تغییر وضعیت نوبت به مشتری."""
    labels = {
        Appointment.Status.CONFIRMED: "تایید شد",
        Appointment.Status.IN_PROGRESS: "در حال انجام است",
        Appointment.Status.DONE: "انجام شد",
        Appointment.Status.REJECTED: "متاسفانه پذیرفته نشد",
    }
    label = labels.get(appointment.status)
    if not label:
        return
    try:
        send_sms(
            appointment.contact_phone or appointment.user.phone,
            f"نوبت {appointment.tracking_code} برای {format_jalali(appointment.date, '%d %B')} {label}.",
        )
    except Exception:  # pragma: no cover - وابسته به پنل پیامکی
        pass


# ---------------------------------------------------------------------------
# کلاس‌های پایه‌ی CRUD
# ---------------------------------------------------------------------------
class DashboardListView(StaffRequiredMixin, ListView):
    """فهرست عمومی موجودیت‌ها در پنل."""

    template_name = "dashboard/generic_list.html"
    paginate_by = 20
    page_title = ""
    create_url = ""
    columns: list[tuple[str, str]] = []
    edit_url_name = ""
    delete_url_name = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            create_url=self.create_url,
            columns=self.columns,
            edit_url_name=self.edit_url_name,
            delete_url_name=self.delete_url_name,
        )
        return context


class DashboardCreateView(StaffRequiredMixin, CreateView):
    template_name = "dashboard/generic_form.html"
    page_title = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(page_title=self.page_title, is_create=True)
        return context

    def form_valid(self, form):
        messages.success(self.request, "با موفقیت ثبت شد.")
        return super().form_valid(form)


class DashboardUpdateView(StaffRequiredMixin, UpdateView):
    template_name = "dashboard/generic_form.html"
    page_title = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(page_title=self.page_title, is_create=False)
        return context

    def form_valid(self, form):
        messages.success(self.request, "تغییرات ذخیره شد.")
        return super().form_valid(form)


class DashboardDeleteView(StaffRequiredMixin, DeleteView):
    template_name = "dashboard/confirm_delete.html"

    def form_valid(self, form):
        messages.success(self.request, "مورد انتخاب‌شده حذف شد.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# خدمات
# ---------------------------------------------------------------------------
class ServiceListView(DashboardListView):
    model = Service
    page_title = "خدمات مغازه"
    create_url = "dashboard:service_create"
    edit_url_name = "dashboard:service_edit"
    delete_url_name = "dashboard:service_delete"
    columns = [("عنوان", "title"), ("دسته", "category"), ("قیمت", "price_label"), ("مدت (دقیقه)", "duration_minutes"), ("فعال", "is_active")]


class ServiceCreateView(DashboardCreateView):
    model = Service
    form_class = ServiceForm
    page_title = "افزودن خدمت جدید"
    success_url = reverse_lazy("dashboard:services")


class ServiceUpdateView(DashboardUpdateView):
    model = Service
    form_class = ServiceForm
    page_title = "ویرایش خدمت"
    success_url = reverse_lazy("dashboard:services")


class ServiceDeleteView(DashboardDeleteView):
    model = Service
    success_url = reverse_lazy("dashboard:services")


class ServiceCategoryListView(DashboardListView):
    model = ServiceCategory
    page_title = "دسته‌بندی خدمات"
    create_url = "dashboard:service_category_create"
    edit_url_name = "dashboard:service_category_edit"
    delete_url_name = "dashboard:service_category_delete"
    columns = [("نام", "name"), ("ترتیب", "order"), ("فعال", "is_active")]


class ServiceCategoryCreateView(DashboardCreateView):
    model = ServiceCategory
    form_class = ServiceCategoryForm
    page_title = "افزودن دسته خدمت"
    success_url = reverse_lazy("dashboard:service_categories")


class ServiceCategoryUpdateView(DashboardUpdateView):
    model = ServiceCategory
    form_class = ServiceCategoryForm
    page_title = "ویرایش دسته خدمت"
    success_url = reverse_lazy("dashboard:service_categories")


class ServiceCategoryDeleteView(DashboardDeleteView):
    model = ServiceCategory
    success_url = reverse_lazy("dashboard:service_categories")


# ---------------------------------------------------------------------------
# بنرها
# ---------------------------------------------------------------------------
class BannerListView(DashboardListView):
    model = Banner
    page_title = "بنرهای سایت"
    create_url = "dashboard:banner_create"
    edit_url_name = "dashboard:banner_edit"
    delete_url_name = "dashboard:banner_delete"
    columns = [("عنوان", "title"), ("محل نمایش", "get_position_display"), ("ترتیب", "order"), ("فعال", "is_active")]


class BannerCreateView(DashboardCreateView):
    model = Banner
    form_class = BannerForm
    page_title = "درج بنر تازه"
    success_url = reverse_lazy("dashboard:banners")


class BannerUpdateView(DashboardUpdateView):
    model = Banner
    form_class = BannerForm
    page_title = "ویرایش بنر"
    success_url = reverse_lazy("dashboard:banners")


class BannerDeleteView(DashboardDeleteView):
    model = Banner
    success_url = reverse_lazy("dashboard:banners")


# ---------------------------------------------------------------------------
# نمونه‌کارها (عکس‌های قبل و بعد)
# ---------------------------------------------------------------------------
class PortfolioListView(DashboardListView):
    model = PortfolioItem
    page_title = "نمونه‌کارها"
    create_url = "dashboard:portfolio_create"
    edit_url_name = "dashboard:portfolio_edit"
    delete_url_name = "dashboard:portfolio_delete"
    columns = [("عنوان", "title"), ("خدمت", "service"), ("خودرو", "car_name"), ("تعداد عکس", "image_count"), ("فعال", "is_active")]


@staff_required
def portfolio_form_view(request, pk=None):
    """ساخت/ویرایش نمونه‌کار به همراه عکس‌های قبل و بعد در یک صفحه."""
    item = get_object_or_404(PortfolioItem, pk=pk) if pk else None
    form = PortfolioItemForm(request.POST or None, request.FILES or None, instance=item)
    formset = PortfolioImageFormSet(request.POST or None, request.FILES or None, instance=item)

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        saved_item = form.save()
        formset.instance = saved_item
        formset.save()
        messages.success(request, f"نمونه‌کار «{saved_item.title}» ذخیره شد.")
        return redirect("dashboard:portfolio")

    return render(
        request,
        "dashboard/portfolio_form.html",
        {"form": form, "formset": formset, "item": item, "page_title": "ویرایش نمونه‌کار" if item else "افزودن نمونه‌کار"},
    )


class PortfolioDeleteView(DashboardDeleteView):
    model = PortfolioItem
    success_url = reverse_lazy("dashboard:portfolio")


# ---------------------------------------------------------------------------
# مقالات
# ---------------------------------------------------------------------------
class ArticleListView(DashboardListView):
    model = Article
    page_title = "مقالات"
    create_url = "dashboard:article_create"
    edit_url_name = "dashboard:article_edit"
    delete_url_name = "dashboard:article_delete"
    columns = [("عنوان", "title"), ("دسته", "category"), ("بازدید", "views_count"), ("منتشر شده", "is_published")]


class ArticleCreateView(DashboardCreateView):
    model = Article
    form_class = ArticleForm
    page_title = "نوشتن مقاله تازه"
    success_url = reverse_lazy("dashboard:articles")

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class ArticleUpdateView(DashboardUpdateView):
    model = Article
    form_class = ArticleForm
    page_title = "ویرایش مقاله"
    success_url = reverse_lazy("dashboard:articles")


class ArticleDeleteView(DashboardDeleteView):
    model = Article
    success_url = reverse_lazy("dashboard:articles")


class ArticleCategoryListView(DashboardListView):
    model = ArticleCategory
    page_title = "دسته‌بندی مقالات"
    create_url = "dashboard:article_category_create"
    edit_url_name = "dashboard:article_category_edit"
    delete_url_name = "dashboard:article_category_delete"
    columns = [("نام", "name"), ("ترتیب", "order")]


class ArticleCategoryCreateView(DashboardCreateView):
    model = ArticleCategory
    form_class = ArticleCategoryForm
    page_title = "افزودن دسته مقاله"
    success_url = reverse_lazy("dashboard:article_categories")


class ArticleCategoryUpdateView(DashboardUpdateView):
    model = ArticleCategory
    form_class = ArticleCategoryForm
    page_title = "ویرایش دسته مقاله"
    success_url = reverse_lazy("dashboard:article_categories")


class ArticleCategoryDeleteView(DashboardDeleteView):
    model = ArticleCategory
    success_url = reverse_lazy("dashboard:article_categories")


# ---------------------------------------------------------------------------
# شبکه‌های اجتماعی و لوکیشن
# ---------------------------------------------------------------------------
class SocialLinkListView(DashboardListView):
    model = SocialLink
    page_title = "لینک‌های شبکه اجتماعی"
    create_url = "dashboard:social_create"
    edit_url_name = "dashboard:social_edit"
    delete_url_name = "dashboard:social_delete"
    columns = [("شبکه", "get_platform_display"), ("مقدار", "value"), ("نشانی", "url"), ("فعال", "is_active")]


class SocialLinkCreateView(DashboardCreateView):
    model = SocialLink
    form_class = SocialLinkForm
    page_title = "افزودن لینک شبکه اجتماعی"
    success_url = reverse_lazy("dashboard:socials")


class SocialLinkUpdateView(DashboardUpdateView):
    model = SocialLink
    form_class = SocialLinkForm
    page_title = "ویرایش لینک شبکه اجتماعی"
    success_url = reverse_lazy("dashboard:socials")


class SocialLinkDeleteView(DashboardDeleteView):
    model = SocialLink
    success_url = reverse_lazy("dashboard:socials")


class LocationListView(DashboardListView):
    model = ShopLocation
    page_title = "لوکیشن مغازه"
    create_url = "dashboard:location_create"
    edit_url_name = "dashboard:location_edit"
    delete_url_name = "dashboard:location_delete"
    columns = [("عنوان", "title"), ("شهر", "city"), ("آدرس", "address"), ("اصلی", "is_main"), ("فعال", "is_active")]


class LocationCreateView(DashboardCreateView):
    model = ShopLocation
    form_class = ShopLocationForm
    page_title = "افزودن لوکیشن مغازه"
    success_url = reverse_lazy("dashboard:locations")
    template_name = "dashboard/location_form.html"


class LocationUpdateView(DashboardUpdateView):
    model = ShopLocation
    form_class = ShopLocationForm
    page_title = "ویرایش لوکیشن مغازه"
    success_url = reverse_lazy("dashboard:locations")
    template_name = "dashboard/location_form.html"


class LocationDeleteView(DashboardDeleteView):
    model = ShopLocation
    success_url = reverse_lazy("dashboard:locations")


# ---------------------------------------------------------------------------
# تنظیمات، ساعت کاری و تعطیلات
# ---------------------------------------------------------------------------
@staff_required
def site_settings_view(request):
    """ویرایش تنظیمات کلی سایت."""
    instance = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "تنظیمات سایت ذخیره شد.")
        return redirect("dashboard:settings")
    return render(request, "dashboard/settings.html", {"form": form})


@staff_required
def working_hours_view(request):
    """تنظیم ساعت کاری هفته و ثبت روزهای تعطیل."""
    WorkingHour.ensure_defaults()
    formset = WorkingHourFormSet(request.POST or None, queryset=WorkingHour.objects.order_by("weekday"))
    holiday_form = HolidayForm()
    if request.method == "POST" and formset.is_valid():
        formset.save()
        messages.success(request, "ساعت‌های کاری به‌روزرسانی شد.")
        return redirect("dashboard:working_hours")
    return render(
        request,
        "dashboard/working_hours.html",
        {
            "formset": formset,
            "holiday_form": holiday_form,
            "holidays": Holiday.objects.filter(date__gte=timezone.localdate()).order_by("date"),
        },
    )


@staff_required
@require_POST
def holiday_create(request):
    """افزودن روز تعطیل."""
    form = HolidayForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "روز تعطیل ثبت شد.")
    else:
        messages.error(request, "تاریخ تعطیلی معتبر نیست یا قبلاً ثبت شده است.")
    return redirect("dashboard:working_hours")


@staff_required
@require_POST
def holiday_delete(request, pk):
    """حذف روز تعطیل."""
    Holiday.objects.filter(pk=pk).delete()
    messages.success(request, "روز تعطیل حذف شد.")
    return redirect("dashboard:working_hours")


# ---------------------------------------------------------------------------
# پرداخت‌ها، مشتریان و پیام‌ها
# ---------------------------------------------------------------------------
@staff_required
def payment_list(request):
    """فهرست تراکنش‌های بیعانه."""
    payments = Payment.objects.select_related("user", "appointment")
    status = request.GET.get("status")
    if status in dict(Payment.Status.choices):
        payments = payments.filter(status=status)
    return render(
        request,
        "dashboard/payments.html",
        {
            "payments": payments[:100],
            "statuses": Payment.Status.choices,
            "active_status": status,
            "paid_total": Payment.objects.filter(status=Payment.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0,
        },
    )


@staff_required
def customer_list(request):
    """فهرست مشتریان و تعداد نوبت‌هایشان."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    query = (request.GET.get("q") or "").strip()
    customers = User.objects.annotate(appointments_total=Count("appointments"))
    if query:
        customers = customers.filter(
            Q(phone__icontains=query) | Q(full_name__icontains=query) | Q(car_model__icontains=query)
        )
    return render(request, "dashboard/customers.html", {"customers": customers[:100], "query": query})


@staff_required
def message_list(request):
    """پیام‌های فرم تماس با ما."""
    messages_qs = ContactMessage.objects.all()
    ContactMessage.objects.filter(is_read=False).update(is_read=True)
    return render(request, "dashboard/messages.html", {"contact_messages": messages_qs[:100]})
