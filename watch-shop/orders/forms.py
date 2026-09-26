from django import forms


class CheckoutForm(forms.Form):
    address = forms.ModelChoiceField(
        label="نشانی ارسال",
        queryset=None,
        widget=forms.RadioSelect,
        empty_label=None,
        error_messages={"required": "لطفاً یک نشانی برای ارسال انتخاب کنید."},
    )
    gateway = forms.ChoiceField(label="درگاه پرداخت", widget=forms.RadioSelect)
    note = forms.CharField(
        label="توضیحات سفارش (اختیاری)",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "مثلاً: لطفاً کادوپیچ شود"}),
    )
    accept_terms = forms.BooleanField(
        label="قوانین و مقررات فروشگاه را مطالعه کرده‌ام و می‌پذیرم.",
        error_messages={"required": "برای ثبت سفارش باید قوانین را بپذیرید."},
    )

    def __init__(self, user, *args, gateways=(), **kwargs):
        super().__init__(*args, **kwargs)
        addresses = user.addresses.all()
        self.fields["address"].queryset = addresses
        default = next((a for a in addresses if a.is_default), None) or addresses.first()
        if default:
            self.fields["address"].initial = default.pk
        self.fields["gateway"].choices = [(g.code, g.title) for g in gateways]
        if gateways:
            self.fields["gateway"].initial = gateways[0].code
