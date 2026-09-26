import re

from django import forms
from django.conf import settings

from .models import Address, User
from .utils import is_valid_mobile, normalize_phone, to_english_digits


class PhoneForm(forms.Form):
    phone = forms.CharField(
        label="شماره موبایل",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "inputmode": "tel",
                "autocomplete": "tel",
                "placeholder": "۰۹۱۲ ۱۲۳ ۴۵۶۷",
                "dir": "ltr",
                "autofocus": True,
            }
        ),
    )

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if not is_valid_mobile(phone):
            raise forms.ValidationError("شماره موبایل معتبر نیست. نمونه صحیح: ۰۹۱۲۱۲۳۴۵۶۷")
        return phone


class ChangePhoneForm(PhoneForm):
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["phone"].label = "شماره موبایل جدید"

    def clean_phone(self):
        phone = super().clean_phone()
        if self.user and phone == self.user.phone:
            raise forms.ValidationError("شماره جدید با شماره فعلی شما یکسان است.")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("این شماره موبایل متعلق به حساب کاربری دیگری است.")
        return phone


class OTPForm(forms.Form):
    code = forms.CharField(
        label="کد تایید",
        max_length=10,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "dir": "ltr",
                "autofocus": True,
            }
        ),
    )

    def clean_code(self):
        code = re.sub(r"\s", "", to_english_digits(self.cleaned_data["code"]))
        if not re.fullmatch(rf"\d{{{settings.OTP_LENGTH}}}", code):
            raise forms.ValidationError("کد تایید باید عددی و کامل وارد شود.")
        return code


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "dir": "ltr"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True


class AddressForm(forms.ModelForm):
    recipient_phone = forms.CharField(
        label="موبایل گیرنده",
        max_length=20,
        widget=forms.TextInput(attrs={"inputmode": "tel", "dir": "ltr", "autocomplete": "tel"}),
    )
    postal_code = forms.CharField(
        label="کد پستی",
        max_length=12,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "dir": "ltr", "autocomplete": "postal-code"}),
    )

    class Meta:
        model = Address
        fields = [
            "title",
            "recipient_name",
            "recipient_phone",
            "province",
            "city",
            "postal_code",
            "address",
            "plaque",
            "unit",
            "is_default",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_recipient_phone(self):
        phone = normalize_phone(self.cleaned_data["recipient_phone"])
        if not is_valid_mobile(phone):
            raise forms.ValidationError("شماره موبایل گیرنده معتبر نیست.")
        return phone

    def clean_postal_code(self):
        return to_english_digits(self.cleaned_data["postal_code"]).strip()
