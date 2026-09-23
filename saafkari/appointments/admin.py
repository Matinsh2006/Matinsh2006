from django.contrib import admin
from django.utils.html import format_html

from core.jalali import format_jalali

from .models import Appointment, AppointmentPhoto, Holiday, WorkingHour


class AppointmentPhotoInline(admin.TabularInline):
    model = AppointmentPhoto
    extra = 0
    readonly_fields = ("preview", "uploaded_at")
    fields = ("preview", "image", "angle", "caption", "uploaded_at")

    @admin.display(description="پیش‌نمایش")
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html('<img src="{}" style="height:70px;border-radius:8px" />', obj.image.url)
        return "—"


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("tracking_code", "user", "service", "jalali_date_display", "time_range", "status", "is_deposit_paid")
    list_filter = ("status", "is_deposit_paid", "service", "date")
    search_fields = ("tracking_code", "user__phone", "user__full_name", "car_model", "plate_number", "description")
    readonly_fields = ("tracking_code", "created_at", "updated_at", "deposit_paid_at", "jalali_date_display")
    inlines = [AppointmentPhotoInline]
    date_hierarchy = "date"
    fieldsets = (
        ("نوبت", {"fields": ("tracking_code", "user", "service", "date", "jalali_date_display", "start_time", "end_time", "status")}),
        ("خودرو و توضیحات", {"fields": ("car_model", "plate_number", "contact_phone", "description")}),
        ("مالی", {"fields": ("deposit_amount", "is_deposit_paid", "deposit_paid_at", "estimated_price")}),
        ("یادداشت مغازه", {"fields": ("staff_note",)}),
        ("زمان‌ها", {"fields": ("created_at", "updated_at")}),
    )
    actions = ["confirm_appointments", "mark_done"]

    @admin.display(description="تاریخ شمسی")
    def jalali_date_display(self, obj):
        return format_jalali(obj.date, "%A %d %B %Y")

    @admin.action(description="تایید نوبت‌های انتخاب‌شده")
    def confirm_appointments(self, request, queryset):
        updated = queryset.update(status=Appointment.Status.CONFIRMED)
        self.message_user(request, f"{updated} نوبت تایید شد.")

    @admin.action(description="علامت‌زدن به عنوان انجام‌شده")
    def mark_done(self, request, queryset):
        updated = queryset.update(status=Appointment.Status.DONE)
        self.message_user(request, f"{updated} نوبت انجام‌شده شد.")


@admin.register(WorkingHour)
class WorkingHourAdmin(admin.ModelAdmin):
    list_display = ("get_weekday_display", "is_open", "open_time", "close_time", "slot_minutes", "capacity")
    list_editable = ("is_open", "open_time", "close_time", "slot_minutes", "capacity")


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ("jalali_date", "date", "title")
    search_fields = ("title",)
