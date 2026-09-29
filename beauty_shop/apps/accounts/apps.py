from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    label = "accounts"
    verbose_name = "کاربران"

    def ready(self):
        from . import checks  # noqa: F401  (registers system checks)
