"""Helpers for Persian text, digits and Iranian phone numbers."""
import re
from html import unescape

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
LATIN_DIGITS = "0123456789"

_TO_LATIN = str.maketrans(PERSIAN_DIGITS + ARABIC_DIGITS, LATIN_DIGITS * 2)
_TO_PERSIAN = str.maketrans(LATIN_DIGITS + ARABIC_DIGITS, PERSIAN_DIGITS * 2)
# Arabic keyboard variants that look identical but break search/uniqueness.
_ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
_DIACRITICS_RE = re.compile("[ً-ٰٟ]")
_SPACES_RE = re.compile(r"\s+")

IRAN_MOBILE_RE = re.compile(r"^09\d{9}$")


def to_latin_digits(value):
    return "" if value is None else str(value).translate(_TO_LATIN)


def to_persian_digits(value):
    return "" if value is None else str(value).translate(_TO_PERSIAN)


def normalize_persian(text):
    """Unify Arabic/Persian letters and digits so stored text is consistent."""
    if not text:
        return text
    return to_latin_digits(text).translate(_ARABIC_TO_PERSIAN).strip()


def normalize_search_query(text):
    text = normalize_persian(text or "")
    text = _DIACRITICS_RE.sub("", text).replace("‌", " ")
    return _SPACES_RE.sub(" ", text).strip()


def html_to_text(html):
    """Plain text from (already sanitized) HTML, keeping words separated."""
    return _SPACES_RE.sub(" ", unescape(re.sub(r"<[^>]+>", " ", html or ""))).strip()


def normalize_phone(value):
    """
    Convert common Iranian mobile formats to ``09xxxxxxxxx``.

    ``+98 912 123 4567``, ``00989121234567``, ``۰۹۱۲۱۲۳۴۵۶۷`` and ``9121234567``
    all become ``09121234567``. Invalid input is returned cleaned but unchanged
    otherwise, so validators can reject it.
    """
    if value is None:
        return ""
    phone = re.sub(r"[\s\-().]", "", to_latin_digits(value))
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("0098"):
        phone = "0" + phone[4:]
    elif phone.startswith("98") and len(phone) == 12:
        phone = "0" + phone[2:]
    elif phone.startswith("9") and len(phone) == 10:
        phone = "0" + phone
    return phone


def is_valid_mobile(phone):
    return bool(IRAN_MOBILE_RE.match(phone or ""))


def mask_phone(phone):
    phone = phone or ""
    if len(phone) != 11:
        return phone
    return f"{phone[:4]}***{phone[-4:]}"


def phone_to_international(value):
    """``0912...`` → ``98912...`` (digits only, as used by wa.me links)."""
    digits = re.sub(r"\D", "", to_latin_digits(value))
    if digits.startswith("00"):
        return digits[2:]
    if digits.startswith("0"):
        return "98" + digits[1:]
    return digits


def phone_for_tel_link(value):
    """Keep digits and a leading ``+`` for ``tel:`` links."""
    cleaned = re.sub(r"[^\d+]", "", to_latin_digits(value))
    return ("+" if cleaned.startswith("+") else "") + cleaned.replace("+", "")
