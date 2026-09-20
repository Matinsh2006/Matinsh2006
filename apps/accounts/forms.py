from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Profile, User
from .validators import normalize_phone, to_english_digits, validate_iranian_phone

INPUT_CLASS = (
    "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 "
    "placeholder-slate-400 outline-none transition focus:border-rose-400 focus:ring-2 "
    "focus:ring-rose-100"
)


class PhoneForm(forms.Form):
    """گام اول ورود: گرفتن شماره موبایل."""

    phone = forms.CharField(
        label=_("شماره موبایل"),
        max_length=15,
        validators=[validate_iranian_phone],
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "placeholder": "09xxxxxxxxx",
                "inputmode": "numeric",
                "autofocus": "autofocus",
                "dir": "ltr",
            }
        ),
    )

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])


class ChangePhoneForm(PhoneForm):
    """شماره جدید برای تغییر نام کاربری."""

    phone = forms.CharField(
        label=_("شماره موبایل جدید"),
        max_length=15,
        validators=[validate_iranian_phone],
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "placeholder": "09xxxxxxxxx", "inputmode": "numeric", "dir": "ltr"}
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if self.user and phone == self.user.phone:
            raise forms.ValidationError(_("شماره جدید با شماره فعلی یکسان است."))
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError(_("این شماره قبلاً در سایت ثبت شده است."))
        return phone


class OTPForm(forms.Form):
    """گام دوم: کد پیامک‌شده."""

    code = forms.CharField(
        label=_("کد تایید"),
        max_length=8,
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS + " text-center tracking-[0.6em] text-lg",
                "placeholder": "- - - - -",
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "autofocus": "autofocus",
                "dir": "ltr",
            }
        ),
    )

    def clean_code(self):
        return to_english_digits(self.cleaned_data["code"]).strip()


class ProfileForm(forms.ModelForm):
    """ویرایش اطلاعات کاربر (شماره موبایل از مسیر پیامک تغییر می‌کند)."""

    full_name = forms.CharField(
        label=_("نام و نام خانوادگی"),
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "مثال: مریم احمدی"}),
    )
    email = forms.EmailField(
        label=_("ایمیل"),
        required=False,
        widget=forms.EmailInput(attrs={"class": INPUT_CLASS, "dir": "ltr"}),
    )

    class Meta:
        model = Profile
        fields = ["avatar", "province", "city", "address", "postal_code", "newsletter"]
        labels = {
            "avatar": _("تصویر پروفایل"),
            "province": _("استان"),
            "city": _("شهر"),
            "address": _("آدرس پستی"),
            "postal_code": _("کد پستی"),
            "newsletter": _("دریافت پیامک تخفیف‌ها"),
        }
        widgets = {
            "avatar": forms.ClearableFileInput(attrs={"class": "w-full text-sm text-slate-600"}),
            "province": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "city": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "address": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
            "postal_code": forms.TextInput(attrs={"class": INPUT_CLASS, "dir": "ltr"}),
            "newsletter": forms.CheckboxInput(
                attrs={"class": "h-5 w-5 rounded border-slate-300 text-rose-500"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields["full_name"].initial = self.instance.user.full_name
            self.fields["email"].initial = self.instance.user.email

    def clean_postal_code(self):
        return to_english_digits(self.cleaned_data.get("postal_code", ""))

    def save(self, commit=True):
        profile = super().save(commit=commit)
        user = profile.user
        user.full_name = self.cleaned_data.get("full_name", "")
        user.email = self.cleaned_data.get("email", "")
        if commit:
            user.save(update_fields=["full_name", "email"])
        return profile
