from django.conf import settings
from django.utils.module_loading import import_string


def get_backend():
    backend_class = import_string(settings.SMS_BACKEND)
    return backend_class()


def send_otp_sms(phone_number, code):
    """Send an OTP code through the configured SMS backend.

    Swap ``settings.SMS_BACKEND`` to point at a real provider (see
    ``accounts/sms/backends.py``) once an account/API key is available.
    """
    backend = get_backend()
    return backend.send_otp(phone_number, code)
