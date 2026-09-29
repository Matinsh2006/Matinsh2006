from django.conf import settings
from django.utils.module_loading import import_string

from .base import BaseSMSBackend, SMSError

__all__ = ["BaseSMSBackend", "SMSError", "get_sms_backend", "send_otp_sms"]


def get_sms_backend():
    return import_string(settings.SMS_BACKEND)()


def send_otp_sms(phone, code):
    get_sms_backend().send_otp(phone, code)
