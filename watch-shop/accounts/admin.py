from django.contrib import admin
from django.contrib.auth import forms as auth_forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Address, OneTimePassword, User
from .utils import normalize_phone


class UserCreationForm(auth_forms.AdminUserCreationForm):
    class Meta:
        model = User
        fields = ("phone", "first_name", "last_name")

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])


class UserChangeForm(auth_forms.UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])


class AddressInline(admin.StackedInline):
    model = Address
    extra = 0
    classes = ("collapse",)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ("phone", "get_full_name", "email", "is_staff", "is_active", "date_joined")
    list_display_links = ("phone", "get_full_name")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("phone", "first_name", "last_name", "email")
    ordering = ("-date_joined",)
    readonly_fields = ("last_login", "date_joined", "phone_verified_at")
    inlines = [AddressInline]
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "email")}),
        (
            "دسترسی‌ها",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("تاریخ‌ها", {"fields": ("last_login", "date_joined", "phone_verified_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "first_name", "last_name", "usable_password", "password1", "password2"),
            },
        ),
    )

    @admin.display(description="نام و نام خانوادگی")
    def get_full_name(self, obj):
        return obj.get_full_name() or "—"


@admin.register(OneTimePassword)
class OneTimePasswordAdmin(admin.ModelAdmin):
    list_display = ("phone", "purpose", "created_at", "expires_at", "attempts", "is_used", "ip_address")
    list_filter = ("purpose", "is_used")
    search_fields = ("phone",)
    exclude = ("code_hash",)
    readonly_fields = ("phone", "purpose", "user", "attempts", "is_used", "ip_address", "created_at", "expires_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
