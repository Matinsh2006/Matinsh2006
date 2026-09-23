"""فرم‌های ورود، تایید پیامکی و پروفایل کاربر."""
from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from core.jalali import to_latin_digits
from core.validators import normalize_phone, validate_iran_mobile

User = get_user_model()

INPUT_CLASS = (
    "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 shadow-sm "
    "transition focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-200"
)


class PhoneForm(forms.Form):
    """گرفتن شماره موبایل برای ارسال کد تایید."""

    phone = forms.CharField(
        label=_("شماره موبایل"), max_length=20,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS, "inputmode": "numeric", "autocomplete": "tel",
            "placeholder": "۰۹۱۲۱۲۳۴۵۶۷", "dir": "ltr", "autofocus": "autofocus",
        }),
    )

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        validate_iran_mobile(phone)
        return phone


class OTPVerifyForm(forms.Form):
    """فرم ورود کد تایید پیامکی."""

    code = forms.CharField(
        label=_("کد تایید"), max_length=8,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS + " text-center tracking-[0.6em] text-xl font-bold",
            "inputmode": "numeric", "autocomplete": "one-time-code",
            "dir": "ltr", "autofocus": "autofocus", "placeholder": "- - - - -",
        }),
    )

    def clean_code(self):
        code = to_latin_digits(self.cleaned_data["code"]).strip()
        if not code.isdigit():
            raise forms.ValidationError(_("کد تایید فقط شامل عدد است."))
        return code


class StaffLoginForm(forms.Form):
    """ورود کارفرما با شماره موبایل و رمز عبور."""

    phone = forms.CharField(
        label=_("شماره موبایل"),
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "dir": "ltr", "inputmode": "numeric"}),
    )
    password = forms.CharField(
        label=_("رمز عبور"),
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASS, "dir": "ltr"}),
    )

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])


class ProfileForm(forms.ModelForm):
    """ویرایش اطلاعات پروفایل (به‌جز شماره موبایل)."""

    class Meta:
        model = User
        fields = ("full_name", "email", "avatar", "car_model", "plate_number")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "مثال: متین شیرانی"}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS, "dir": "ltr", "placeholder": "example@mail.com"}),
            "avatar": forms.ClearableFileInput(attrs={"class": "w-full text-sm", "accept": "image/*"}),
            "car_model": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "مثال: پژو ۲۰۶ سفید"}),
            "plate_number": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "۱۲ ب ۳۴۵ ایران ۲۲"}),
        }


class PhoneChangeForm(forms.Form):
    """درخواست تغییر شماره موبایل (نام کاربری)."""

    new_phone = forms.CharField(
        label=_("شماره موبایل جدید"), max_length=20,
        widget=forms.TextInput(attrs={
            "class": INPUT_CLASS, "dir": "ltr", "inputmode": "numeric",
            "placeholder": "۰۹۱۲۱۲۳۴۵۶۷", "autofocus": "autofocus",
        }),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_new_phone(self):
        phone = normalize_phone(self.cleaned_data["new_phone"])
        validate_iran_mobile(phone)
        if self.user and phone == self.user.phone:
            raise forms.ValidationError(_("شماره‌ی جدید با شماره‌ی فعلی یکسان است."))
        query = User.objects.filter(phone=phone)
        if self.user:
            query = query.exclude(pk=self.user.pk)
        if query.exists():
            raise forms.ValidationError(_("این شماره قبلاً در سایت ثبت شده است."))
        return phone
