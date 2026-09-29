import ipaddress

from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme


def get_client_ip(request):
    header = settings.CLIENT_IP_HEADER
    raw = (request.META.get(header) if header else None) or request.META.get("REMOTE_ADDR", "")
    # With X-Forwarded-For the right-most entry is the one added by our own proxy.
    candidate = raw.split(",")[-1].strip()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def get_safe_next_url(request, url):
    """Return ``url`` only if it points to this site (prevents open redirects)."""
    if url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return url
    return ""
