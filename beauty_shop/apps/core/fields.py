from django.db import models

from .sanitizer import sanitize_html
from .widgets import RichTextWidget


class RichTextField(models.TextField):
    """A TextField holding HTML that is sanitized every time it is saved."""

    description = "Sanitized rich text (HTML)"

    def formfield(self, **kwargs):
        # The admin passes its own Textarea widget for TextFields; always use the editor.
        widget = kwargs.get("widget")
        is_editor = isinstance(widget, RichTextWidget) or (
            isinstance(widget, type) and issubclass(widget, RichTextWidget)
        )
        if not is_editor:
            kwargs["widget"] = RichTextWidget
        return super().formfield(**kwargs)

    def pre_save(self, model_instance, add):
        cleaned = sanitize_html(getattr(model_instance, self.attname))
        setattr(model_instance, self.attname, cleaned)
        return cleaned
