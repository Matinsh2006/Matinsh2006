from django.conf import settings
from django.core.checks import Tags, Warning, register

DEVELOPMENT_BACKENDS = ("ConsoleSMSBackend", "LocmemSMSBackend")


@register(Tags.security, deploy=True)
def sms_backend_check(app_configs, **kwargs):
    if not settings.DEBUG and settings.SMS_BACKEND.endswith(DEVELOPMENT_BACKENDS):
        return [
            Warning(
                "A development SMS backend is active while DEBUG=False; customers will not receive login codes.",
                hint="Set SMS_BACKEND to the Kavenegar, SMS.ir or Melipayamak backend and its API settings.",
                id="accounts.W001",
            )
        ]
    return []
