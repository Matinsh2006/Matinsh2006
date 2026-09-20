from django import forms

from apps.accounts.validators import normalize_phone, to_english_digits, validate_iranian_phone

from .models import Order

INPUT_CLASS = (
    "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-slate-800 "
    "placeholder-slate-400 outline-none transition focus:border-rose-400 focus:ring-2 "
    "focus:ring-rose-100"
)


class CheckoutForm(forms.ModelForm):
    """اطلاعات گیرنده سفارش."""

    class Meta:
        model = Order
        fields = ["full_name", "phone", "province", "city", "address", "postal_code", "note"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "نام و نام خانوادگی"}),
            "phone": forms.TextInput(
                attrs={"class": INPUT_CLASS, "placeholder": "09xxxxxxxxx", "dir": "ltr", "inputmode": "numeric"}
            ),
            "province": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "مثال: تهران"}),
            "city": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "مثال: تهران"}),
            "address": forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3, "placeholder": "نشانی کامل پستی"}),
            "postal_code": forms.TextInput(attrs={"class": INPUT_CLASS, "dir": "ltr"}),
            "note": forms.Textarea(
                attrs={"class": INPUT_CLASS, "rows": 2, "placeholder": "توضیح اختیاری برای فروشنده"}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].validators.append(validate_iranian_phone)
        if user is not None and user.is_authenticated and not self.is_bound:
            profile = getattr(user, "profile", None)
            self.fields["full_name"].initial = user.full_name
            self.fields["phone"].initial = user.phone
            if profile:
                self.fields["province"].initial = profile.province
                self.fields["city"].initial = profile.city
                self.fields["address"].initial = profile.address
                self.fields["postal_code"].initial = profile.postal_code

    def clean_phone(self):
        return normalize_phone(self.cleaned_data["phone"])

    def clean_postal_code(self):
        return to_english_digits(self.cleaned_data.get("postal_code", ""))
