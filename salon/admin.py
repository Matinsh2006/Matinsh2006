from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .models import SalonProfile


@admin.register(SalonProfile)
class SalonProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        ("نام و معرفی", {"fields": ("name", "tagline", "about", "logo", "hero_image")}),
        ("لوکیشن مغازه", {"fields": ("address", "map_lat", "map_lng", "map_link")}),
        (
            "راه‌های ارتباطی و شبکه‌های اجتماعی",
            {
                "fields": (
                    "contact_phone",
                    "telegram_url",
                    "instagram_url",
                    "whatsapp_url",
                    "twitter_url",
                )
            },
        ),
        (
            "روزها و ساعات کاری",
            {
                "fields": (
                    (
                        "is_open_saturday",
                        "is_open_sunday",
                        "is_open_monday",
                        "is_open_tuesday",
                        "is_open_wednesday",
                        "is_open_thursday",
                        "is_open_friday",
                    ),
                    ("opening_time", "closing_time", "slot_duration_minutes"),
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return not SalonProfile.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SalonProfile.get_solo()
        return redirect(reverse("admin:salon_salonprofile_change", args=[obj.pk]))
