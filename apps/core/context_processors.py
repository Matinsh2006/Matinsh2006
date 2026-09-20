from .models import SiteSetting


def site_context(request):
    """تنظیمات فروشگاه را در همه قالب‌ها در دسترس قرار می‌دهد."""
    return {"site": SiteSetting.load()}
