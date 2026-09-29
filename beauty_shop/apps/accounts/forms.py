import re

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from apps.core.forms import StyledFormMixin
from apps.core.utils.text import is_valid_mobile, to_latin_digits, to_persian_digits

from .fields import PhoneNumberFormField
from .models import Address, User

AVATAR_MAX_SIZE = 2 * 1024 * 1024


class PhoneForm(StyledFormMixin, forms.Form):
    phone = PhoneNumberFormField(label="شماره موبایل")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].widget.attrs.update({"autofocus": True, "inputmode": "numeric", "data-latin-digits": ""})

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        if not is_valid_mobile(phone):
            raise forms.ValidationError("شماره موبایل معتبر نیست. نمونه صحیح: 09123456789")
        return phone


class OTPForm(StyledFormMixin, forms.Form):
    code = forms.CharField(
        label="کد تایید",
        max_length=12,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "dir": "ltr",
                "autofocus": True,
                "class": "otp-input",
                "data-latin-digits": "",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["code"].widget.attrs["data-autosubmit-length"] = settings.OTP_LENGTH

    def clean_code(self):
        code = re.sub(r"\D", "", to_latin_digits(self.cleaned_data["code"]))
        if len(code) != settings.OTP_LENGTH:
            raise forms.ValidationError(f"کد تایید باید {to_persian_digits(settings.OTP_LENGTH)} رقم باشد.")
        return code


class ChangePhoneForm(PhoneForm):
    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["phone"].label = "شماره موبایل جدید"

    def clean_phone(self):
        phone = super().clean_phone()
        if phone == self.user.phone:
            raise forms.ValidationError("شماره جدید با شماره فعلی شما یکسان است.")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("این شماره قبلاً در سایت ثبت شده است.")
        return phone


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "avatar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["email"].widget.attrs["dir"] = "ltr"

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")
        if avatar and getattr(avatar, "size", 0) > AVATAR_MAX_SIZE:
            raise forms.ValidationError("حجم تصویر نباید بیشتر از ۲ مگابایت باشد.")
        return avatar


class AddressForm(StyledFormMixin, forms.ModelForm):
    # Longer than 10 so values typed with spaces/dashes reach clean_postal_code().
    postal_code = forms.CharField(
        label="کد پستی",
        max_length=20,
        widget=forms.TextInput(
            attrs={"dir": "ltr", "inputmode": "numeric", "placeholder": "1234567890", "data-latin-digits": ""}
        ),
    )

    class Meta:
        model = Address
        fields = (
            "title",
            "receiver_name",
            "receiver_phone",
            "province",
            "city",
            "postal_code",
            "full_address",
            "is_default",
        )
        widgets = {
            "full_address": forms.Textarea(attrs={"rows": 3, "placeholder": "خیابان، کوچه، پلاک، واحد"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["province"].choices = [("", "انتخاب استان")] + list(self.fields["province"].choices)[1:]
        self.fields["receiver_phone"].widget.attrs["data-latin-digits"] = ""

    def clean_postal_code(self):
        postal_code = re.sub(r"\D", "", to_latin_digits(self.cleaned_data["postal_code"]))
        if len(postal_code) != 10:
            raise forms.ValidationError("کد پستی باید ۱۰ رقم باشد.")
        return postal_code


# --- Admin forms ------------------------------------------------------------


class AdminUserAddForm(AdminUserCreationForm):
    class Meta:
        model = User
        fields = ("phone",)
        field_classes = {}


class AdminUserEditForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"
        field_classes = {}
