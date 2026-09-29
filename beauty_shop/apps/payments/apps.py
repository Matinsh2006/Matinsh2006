from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    label = "payments"
    verbose_name = "پرداخت‌ها"

    def ready(self):
        from . import checks  # noqa: F401  (registers system checks)
