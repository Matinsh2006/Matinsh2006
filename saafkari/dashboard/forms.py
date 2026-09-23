"""فرم‌های پنل کارفرما (ساخت و ویرایش محتوای سایت)."""
from __future__ import annotations

from django import forms
from django.forms import inlineformset_factory, modelformset_factory

from appointments.models import Holiday, WorkingHour
from blog.models import Article, ArticleCategory
from core.forms import INPUT_CLASS, JalaliDateField, JalaliDateWidget
from core.models import ContactMessage, ShopLocation, SiteSettings, SocialLink
from gallery.models import Banner, PortfolioImage, PortfolioItem
from services.models import Service, ServiceCategory

CHECKBOX_CLASS = "h-5 w-5 rounded border-slate-300 text-amber-600 focus:ring-amber-400"
FILE_CLASS = (
    "w-full text-sm text-slate-600 file:ml-4 file:rounded-lg file:border-0 file:bg-amber-100 "
    "file:px-4 file:py-2 file:text-amber-800 hover:file:bg-amber-200"
)


class StyledFormMixin:
    """کلاس‌های تیلویند را روی همه‌ی ورودی‌های فرم اعمال می‌کند."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                widget.attrs.setdefault("class", CHECKBOX_CLASS)
            elif isinstance(widget, (forms.FileInput, forms.ClearableFileInput)):
                widget.attrs.setdefault("class", FILE_CLASS)
                widget.attrs.setdefault("accept", "image/*")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", INPUT_CLASS)
                widget.attrs.setdefault("rows", 5)
            elif isinstance(widget, JalaliDateWidget):
                continue
            else:
                widget.attrs.setdefault("class", INPUT_CLASS)


class ServiceForm(StyledFormMixin, forms.ModelForm):
    """افزودن یا ویرایش خدمت."""

    class Meta:
        model = Service
        fields = (
            "title", "category", "short_description", "description", "image",
            "base_price", "price_note", "duration_minutes", "deposit_amount",
            "is_active", "is_featured", "order",
        )


class ServiceCategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ServiceCategory
        fields = ("name", "description", "icon", "order", "is_active")


class BannerForm(StyledFormMixin, forms.ModelForm):
    """درج بنر (اسلایدر صفحه نخست و ...)."""

    class Meta:
        model = Banner
        fields = (
            "title", "subtitle", "image", "mobile_image", "link_url", "button_text",
            "position", "order", "is_active", "start_at", "end_at",
        )
        widgets = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class PortfolioItemForm(StyledFormMixin, forms.ModelForm):
    """نمونه‌کار: مشخصات کلی (عکس‌ها در فرم جداگانه اضافه می‌شوند)."""

    completed_at = JalaliDateField(label="تاریخ انجام", required=False)

    class Meta:
        model = PortfolioItem
        fields = (
            "title", "service", "car_name", "description", "cover", "duration_label",
            "completed_at", "is_featured", "is_active", "order",
        )


#: فرم‌ست عکس‌های نمونه‌کار — هر نمونه‌کار می‌تواند چندین عکس قبل و بعد داشته باشد
PortfolioImageFormSet = inlineformset_factory(
    PortfolioItem,
    PortfolioImage,
    fields=("image", "kind", "caption", "order"),
    extra=4,
    can_delete=True,
    widgets={
        "image": forms.ClearableFileInput(attrs={"class": FILE_CLASS, "accept": "image/*"}),
        "kind": forms.Select(attrs={"class": INPUT_CLASS}),
        "caption": forms.TextInput(attrs={"class": INPUT_CLASS, "placeholder": "توضیح کوتاه عکس"}),
        "order": forms.NumberInput(attrs={"class": INPUT_CLASS, "min": 0}),
    },
)


class ArticleForm(StyledFormMixin, forms.ModelForm):
    """افزودن یا ویرایش مقاله."""

    class Meta:
        model = Article
        fields = (
            "title", "category", "cover", "summary", "content", "tags",
            "is_published", "is_featured", "published_at",
        )
        widgets = {
            "content": forms.Textarea(attrs={"rows": 14}),
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.published_at:
            self.initial["published_at"] = self.instance.published_at.strftime("%Y-%m-%dT%H:%M")


class ArticleCategoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ArticleCategory
        fields = ("name", "description", "order")


class SocialLinkForm(StyledFormMixin, forms.ModelForm):
    """افزودن لینک شبکه اجتماعی."""

    class Meta:
        model = SocialLink
        fields = ("platform", "value", "label", "order", "show_in_header", "is_active")


class ShopLocationForm(StyledFormMixin, forms.ModelForm):
    """ثبت لوکیشن مغازه روی نقشه."""

    class Meta:
        model = ShopLocation
        fields = (
            "title", "address", "city", "province", "postal_code", "phone",
            "latitude", "longitude", "map_zoom", "map_link", "is_main", "is_active",
        )
        widgets = {
            "latitude": forms.NumberInput(attrs={"step": "0.0000001", "dir": "ltr", "data-lat": "true"}),
            "longitude": forms.NumberInput(attrs={"step": "0.0000001", "dir": "ltr", "data-lng": "true"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["settings"] = forms.ModelChoiceField(
            queryset=SiteSettings.objects.all(), required=False, widget=forms.HiddenInput()
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.settings = SiteSettings.load()
        if commit:
            instance.save()
        return instance


class SiteSettingsForm(StyledFormMixin, forms.ModelForm):
    """ویرایش تنظیمات کلی سایت."""

    class Meta:
        model = SiteSettings
        fields = (
            "brand_name", "tagline", "about", "logo", "hero_image",
            "phone", "second_phone", "email", "working_hours",
            "deposit_amount", "online_payment_enabled", "require_deposit",
            "meta_description", "enamad_code",
        )
        widgets = {"about": forms.Textarea(attrs={"rows": 6}), "enamad_code": forms.Textarea(attrs={"rows": 3})}


class HolidayForm(StyledFormMixin, forms.ModelForm):
    """ثبت روز تعطیل با تاریخ شمسی."""

    date = JalaliDateField(label="تاریخ تعطیلی")

    class Meta:
        model = Holiday
        fields = ("date", "title")


#: فرم‌ست ساعت‌های کاری هفته
WorkingHourFormSet = modelformset_factory(
    WorkingHour,
    fields=("weekday", "is_open", "open_time", "close_time", "slot_minutes", "capacity"),
    extra=0,
    widgets={
        "weekday": forms.Select(attrs={"class": INPUT_CLASS, "disabled": "disabled"}),
        "is_open": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        "open_time": forms.TimeInput(attrs={"class": INPUT_CLASS, "type": "time"}),
        "close_time": forms.TimeInput(attrs={"class": INPUT_CLASS, "type": "time"}),
        "slot_minutes": forms.NumberInput(attrs={"class": INPUT_CLASS, "min": 15, "step": 15}),
        "capacity": forms.NumberInput(attrs={"class": INPUT_CLASS, "min": 1}),
    },
)


class ContactReplyForm(StyledFormMixin, forms.ModelForm):
    """علامت‌گذاری پیام تماس به عنوان خوانده‌شده."""

    class Meta:
        model = ContactMessage
        fields = ("is_read",)
