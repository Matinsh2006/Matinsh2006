from django import forms
from django.urls import NoReverseMatch, reverse


class RichTextWidget(forms.Textarea):
    """
    Lightweight WYSIWYG editor (no external dependencies).

    The JavaScript in ``static/shop_admin/richtext.js`` turns the textarea into
    an RTL editor with headings, lists, links, quotes and image upload.
    """

    template_name = "core/widgets/richtext.html"

    def __init__(self, attrs=None):
        default_attrs = {"rows": 14, "class": "rte-source", "dir": "rtl"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    class Media:
        css = {"all": ("shop_admin/richtext.css",)}
        js = ("shop_admin/richtext.js",)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        try:
            context["widget"]["upload_url"] = reverse("core:editor_upload")
        except NoReverseMatch:
            context["widget"]["upload_url"] = ""
        return context
