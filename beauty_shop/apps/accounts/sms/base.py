import logging

import requests
from django.conf import settings

logger = logging.getLogger("apps.accounts.sms")


class SMSError(Exception):
    """Raised when an SMS provider rejects a message or cannot be reached."""


class BaseSMSBackend:
    """Interface every SMS panel backend implements."""

    def send_otp(self, phone, code):
        raise NotImplementedError

    def _request(self, url, **kwargs):
        try:
            response = requests.post(url, timeout=settings.SMS_TIMEOUT, **kwargs)
        except requests.RequestException as exc:
            raise SMSError(f"Connection to SMS provider failed: {exc}") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise SMSError(f"Invalid response from SMS provider (HTTP {response.status_code})") from exc
