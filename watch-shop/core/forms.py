from django import forms

from accounts.utils import is_valid_mobile, normalize_phone

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    phone = forms.CharField(
        label="شماره تماس",
        max_length=20,
        widget=forms.TextInput(attrs={"inputmode": "tel", "dir": "ltr", "autocomplete": "tel"}),
    )
    # Honeypot field: real visitors never see or fill it.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = ContactMessage
        fields = ["name", "phone", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}

    def clean_phone(self):
        phone = normalize_phone(self.cleaned_data["phone"])
        if not (is_valid_mobile(phone) or (phone.startswith("0") and len(phone) == 11)):
            raise forms.ValidationError("شماره تماس معتبر نیست.")
        return phone

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("website"):
            raise forms.ValidationError("درخواست نامعتبر است.")
        return cleaned
