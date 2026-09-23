"""پنل مدیریت کاربران و کدهای تایید."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.utils.translation import gettext_lazy as _

from .models import OTPCode, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    change_password_form = AdminPasswordChangeForm
    ordering = ("-date_joined",)
    list_display = ("phone", "full_name", "car_model", "is_phone_verified", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_active", "is_phone_verified")
    search_fields = ("phone", "full_name", "email", "car_model", "plate_number")
    readonly_fields = ("last_login", "date_joined", "phone_changed_at")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        (_("اطلاعات شخصی"), {"fields": ("full_name", "email", "avatar", "car_model", "plate_number")}),
        (_("دسترسی‌ها"), {"fields": ("is_active", "is_phone_verified", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("تاریخ‌ها"), {"fields": ("last_login", "date_joined", "phone_changed_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "full_name", "password1", "password2")}),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("phone", "purpose", "created_at", "expires_at", "used_at", "attempts")
    list_filter = ("purpose", "created_at")
    search_fields = ("phone",)
    readonly_fields = ("phone", "purpose", "code_hash", "user", "created_at", "expires_at", "used_at", "attempts", "ip_address")

    def has_add_permission(self, request):
        return False
