from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

from .gateways import GATEWAYS


@register(Tags.security, deploy=True)
def payment_gateway_check(app_configs, **kwargs):
    issues = []
    gateway = settings.PAYMENT_GATEWAY
    if gateway not in GATEWAYS:
        issues.append(
            Error(f"PAYMENT_GATEWAY='{gateway}' is not a known gateway.", hint=f"Use one of: {', '.join(GATEWAYS)}", id="payments.E001")
        )
    elif gateway == "fake" and not settings.DEBUG:
        issues.append(
            Warning(
                "The built-in test payment gateway is selected while DEBUG=False.",
                hint="Set PAYMENT_GATEWAY=zarinpal (or zibal) and its merchant id before going live.",
                id="payments.W001",
            )
        )
    elif gateway == "zarinpal" and not settings.ZARINPAL_MERCHANT_ID:
        issues.append(Warning("ZARINPAL_MERCHANT_ID is empty.", id="payments.W002"))
    return issues
