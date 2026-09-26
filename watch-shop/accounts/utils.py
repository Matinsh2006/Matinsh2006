import re

_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_TO_EN = str.maketrans(_PERSIAN_DIGITS + _ARABIC_DIGITS, "0123456789" * 2)

MOBILE_RE = re.compile(r"^09\d{9}$")


def to_english_digits(value) -> str:
    return str(value or "").translate(_TO_EN)


def normalize_phone(value) -> str:
    """Normalise an Iranian mobile number to the canonical ``09XXXXXXXXX`` form.

    Accepts Persian/Arabic digits, spaces, dashes and the ``+98`` / ``0098`` /
    ``98`` prefixes. Anything that cannot be normalised is returned as digits
    only, so validation can reject it with a clear message.
    """
    digits = re.sub(r"\D", "", to_english_digits(value))
    if digits.startswith("0098"):
        digits = "0" + digits[4:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif digits.startswith("9") and len(digits) == 10:
        digits = "0" + digits
    return digits


def is_valid_mobile(value) -> bool:
    return bool(MOBILE_RE.match(value or ""))


def mask_phone(phone: str) -> str:
    """0912***4567 style masking for display."""
    if not phone or len(phone) < 8:
        return phone or ""
    return f"{phone[:4]}***{phone[-4:]}"


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None
