from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.core.admin_utils import jalali_display

from .forms import AdminUserAddForm, AdminUserEditForm
from .models import Address, OTPCode, User


class AddressInline(admin.StackedInline):
    model = Address
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = AdminUserEditForm
    add_form = AdminUserAddForm
    list_display = ("phone", "full_name", "email", "is_staff", "is_active", "joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("phone", "first_name", "last_name", "email")
    ordering = ("-date_joined",)
    readonly_fields = ("last_login", "date_joined", "phone_verified_at")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "email", "avatar")}),
        ("دسترسی‌ها", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined", "phone_verified_at")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "usable_password", "password1", "password2")}),
    )

    def get_inlines(self, request, obj):
        return [AddressInline] if obj else []

    @admin.display(description="نام و نام خانوادگی")
    def full_name(self, obj):
        return obj.get_full_name() or "—"

    @admin.display(description="تاریخ عضویت", ordering="date_joined")
    def joined(self, obj):
        return jalali_display(obj.date_joined, "%Y/%m/%d")


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    """Read-only log of sent verification codes (codes are stored hashed)."""

    list_display = ("phone", "purpose", "sent_at", "attempts", "is_used", "ip_address")
    list_filter = ("purpose", "is_used")
    search_fields = ("phone",)
    exclude = ("code_hash",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="زمان ارسال", ordering="created_at")
    def sent_at(self, obj):
        return jalali_display(obj.created_at)
