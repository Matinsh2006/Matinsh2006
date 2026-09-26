import re

_EN_TO_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_digits(value) -> str:
    """Render Latin digits with Persian glyphs (for display only)."""
    if value is None:
        return ""
    return str(value).translate(_EN_TO_FA)


def format_number(value) -> str:
    """12500000 -> ۱۲٬۵۰۰٬۰۰۰"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fa_digits(value)
    return fa_digits(f"{number:,}".replace(",", "٬"))


def normalize_link(value: str, pattern: str) -> str:
    """Turn a username, a bare domain path or a full URL into a full URL."""
    value = (value or "").strip()
    if not value:
        return ""
    if re.match(r"^https?://", value, re.I):
        return value
    if "/" in value:  # e.g. "t.me/myshop" or "instagram.com/myshop"
        return "https://" + value.lstrip("/")
    # A bare username (Instagram usernames may contain dots).
    return pattern.format(value.lstrip("@"))


def whatsapp_link(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if re.match(r"^https?://", value, re.I):
        return value
    from accounts.utils import to_english_digits

    digits = re.sub(r"\D", "", to_english_digits(value))
    if digits.startswith("00"):
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = "98" + digits[1:]
    return f"https://wa.me/{digits}"


def tel_link(value: str) -> str:
    from accounts.utils import to_english_digits

    cleaned = re.sub(r"[^\d+]", "", to_english_digits(value or ""))
    return f"tel:{cleaned}" if cleaned else ""
