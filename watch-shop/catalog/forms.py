from django import forms
from django.forms.models import ModelChoiceIterator

from .models import Category, Product


class GroupedCategoryIterator(ModelChoiceIterator):
    """Render leaf categories grouped under their watch type (<optgroup>)."""

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        groups = {}
        for category in self.queryset:
            groups.setdefault(category.parent, []).append(category)
        for parent, children in groups.items():
            if parent is None:
                for category in children:
                    yield self.choice(category)
            else:
                yield (parent.name, [self.choice(category) for category in children])


class GroupedCategoryChoiceField(forms.ModelChoiceField):
    iterator = GroupedCategoryIterator

    def label_from_instance(self, obj):
        return obj.title if obj.parent_id else obj.name


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleImageInput(attrs={"accept": "image/*", "multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data if item]
        return [single_clean(data, initial)] if data else []


class ProductAdminForm(forms.ModelForm):
    bulk_images = MultipleImageField(
        label="افزودن چند تصویر یکجا",
        required=False,
        help_text="می‌توانید چند تصویر را همزمان انتخاب کنید؛ به انتهای گالری محصول اضافه می‌شوند.",
    )

    class Meta:
        model = Product
        fields = "__all__"


class CategoryAdminForm(forms.ModelForm):
    create_gender_children = forms.BooleanField(
        label="ساخت خودکار زیرشاخه‌های «مردانه» و «زنانه»",
        required=False,
        initial=True,
        help_text="فقط برای دسته‌های اصلی (نوع ساعت) اعمال می‌شود؛ مثلاً اسپرت › مردانه و اسپرت › زنانه.",
    )

    class Meta:
        model = Category
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["create_gender_children"].initial = False


class ProductFilterForm(forms.Form):
    SORT_CHOICES = [
        ("new", "جدیدترین"),
        ("cheap", "ارزان‌ترین"),
        ("expensive", "گران‌ترین"),
        ("discount", "بیشترین تخفیف"),
    ]

    q = forms.CharField(required=False)
    gender = forms.ChoiceField(
        required=False, choices=[("", "همه"), ("men", "مردانه"), ("women", "زنانه")]
    )
    brand = forms.MultipleChoiceField(required=False)
    type = forms.MultipleChoiceField(required=False)
    movement = forms.MultipleChoiceField(required=False, choices=Product.Movement.choices)
    strap = forms.MultipleChoiceField(required=False, choices=Product.Strap.choices)
    min_price = forms.IntegerField(required=False, min_value=0)
    max_price = forms.IntegerField(required=False, min_value=0)
    available = forms.BooleanField(required=False)
    discount = forms.BooleanField(required=False)
    sort = forms.ChoiceField(required=False, choices=SORT_CHOICES)

    def __init__(self, *args, brands=(), types=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].choices = [(b.slug, b.name) for b in brands]
        self.fields["type"].choices = [(c.slug, c.name) for c in types]
