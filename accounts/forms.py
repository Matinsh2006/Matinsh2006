from django import forms

from .models import User, phone_validator


class PhoneForm(forms.Form):
    phone_number = forms.CharField(
        label="شماره موبایل",
        max_length=11,
        min_length=11,
        validators=[phone_validator],
        widget=forms.TextInput(
            attrs={
                "placeholder": "09xxxxxxxxx",
                "inputmode": "numeric",
                "autofocus": True,
                "class": "form-control",
                "dir": "ltr",
                "autocomplete": "tel",
            }
        ),
    )

    def clean_phone_number(self):
        value = self.cleaned_data["phone_number"].strip()
        if not value.isdigit():
            raise forms.ValidationError("شماره موبایل باید فقط شامل عدد باشد.")
        return value


class OTPCodeForm(forms.Form):
    code = forms.CharField(
        label="کد تایید پیامک‌شده",
        max_length=8,
        widget=forms.TextInput(
            attrs={
                "placeholder": "کد را وارد کنید",
                "inputmode": "numeric",
                "autofocus": True,
                "class": "form-control otp-input",
                "dir": "ltr",
                "autocomplete": "one-time-code",
            }
        ),
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name"]
        labels = {"full_name": "نام و نام خانوادگی"}
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "مثلاً سارا احمدی"}
            ),
        }
