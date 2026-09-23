from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import OTP, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["phone_number", "full_name", "is_phone_verified", "is_staff", "date_joined"]
    list_filter = ["is_staff", "is_superuser", "is_active", "is_phone_verified"]
    search_fields = ["phone_number", "full_name"]
    readonly_fields = ["date_joined", "last_login"]
    fieldsets = (
        (None, {"fields": ("phone_number", "password")}),
        ("اطلاعات شخصی", {"fields": ("full_name",)}),
        (
            "دسترسی‌ها",
            {
                "fields": (
                    "is_active",
                    "is_phone_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_number", "password1", "password2"),
            },
        ),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ["phone_number", "code", "purpose", "created_at", "is_used", "attempts"]
    list_filter = ["purpose", "is_used"]
    search_fields = ["phone_number"]
    readonly_fields = [f.name for f in OTP._meta.fields]

    def has_add_permission(self, request):
        return False
