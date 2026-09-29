from django import forms

_UNSTYLED_WIDGETS = (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect, forms.FileInput)


class StyledFormMixin:
    """Adds the shared ``input`` CSS class to text-like widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, _UNSTYLED_WIDGETS):
                continue
            classes = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{classes} input".strip()
