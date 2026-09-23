"""
پرکردن سایت با داده‌های نمونه.

    python manage.py seed_demo

این دستور تنظیمات سایت، لوکیشن، شبکه‌های اجتماعی، خدمات، نمونه‌کارها
(با عکس قبل و بعد)، بنرها، مقالات و ساعت کاری را می‌سازد تا سایت از همان
ابتدا خالی نباشد. اجرای دوباره، داده‌های تکراری نمی‌سازد.
"""
from __future__ import annotations

import datetime as dt
import io
import random

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import WorkingHour
from blog.models import Article, ArticleCategory
from core.models import ShopLocation, SiteSettings, SocialLink
from gallery.models import Banner, PortfolioImage, PortfolioItem
from services.models import Service, ServiceCategory

PALETTES = [
    ((15, 23, 42), (245, 158, 11)),
    ((30, 41, 59), (56, 189, 248)),
    ((51, 65, 85), (16, 185, 129)),
    ((88, 28, 135), (244, 114, 182)),
    ((120, 53, 15), (253, 224, 71)),
]


def make_image(text: str, width: int = 1200, height: int = 700, seed: int = 0, name: str = "sample.jpg") -> ContentFile:
    """ساخت تصویر نمونه (گرادیان + متن) بدون نیاز به فایل خارجی."""
    from PIL import Image, ImageDraw

    random.seed(seed)
    start, end = PALETTES[seed % len(PALETTES)]
    image = Image.new("RGB", (width, height), start)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / height
        color = tuple(int(start[i] + (end[i] - start[i]) * ratio) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    # چند شکل ساده برای اینکه تصویر یکنواخت نباشد
    for _ in range(6):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        size = random.randint(60, 220)
        draw.ellipse([x1, y1, x1 + size, y1 + size], outline=(255, 255, 255), width=3)
    draw.text((40, height - 60), text, fill=(255, 255, 255))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return ContentFile(buffer.getvalue(), name=name)


class Command(BaseCommand):
    help = "ساخت داده‌های نمونه برای سایت مغازه صافکاری"

    def add_arguments(self, parser):
        parser.add_argument("--with-images", action="store_true", help="ساخت تصاویر نمونه (نیازمند Pillow)")

    def handle(self, *args, **options):
        with_images = options["with_images"]
        counter = 0

        # ------------------------------------------------- تنظیمات و لوکیشن
        site = SiteSettings.load()
        site.brand_name = "صافکاری و نقاشی مکانیک‌پلاس"
        site.tagline = "صافکاری بدون رنگ (PDR)، نقاشی کوره‌ای و پولیش تخصصی خودرو"
        site.about = (
            "مجموعه‌ی ما با بیش از ۱۵ سال سابقه در صافکاری و نقاشی خودرو، با تجهیزات روز و "
            "رنگ‌های اصل، بدنه‌ی خودروی شما را به حالت کارخانه برمی‌گرداند.\n"
            "در صافکاری بدون رنگ، فرورفتگی‌ها بدون آسیب به رنگ اصلی خودرو برطرف می‌شوند؛ "
            "روشی که هم ارزان‌تر است و هم ارزش خودرو را حفظ می‌کند."
        )
        site.phone = "02133445566"
        site.second_phone = "09121234567"
        site.email = "info@example.com"
        site.working_hours = "شنبه تا پنجشنبه، ۹ صبح تا ۸ شب"
        site.deposit_amount = 200000
        site.meta_description = "صافکاری بدون رنگ، نقاشی و پولیش خودرو با رزرو نوبت آنلاین"
        site.save()

        location, created = ShopLocation.objects.get_or_create(
            title="شعبه اصلی",
            defaults={
                "settings": site,
                "address": "تهران، خیابان آزادی، نبش کوچه بهار، پلاک ۱۲۰",
                "city": "تهران",
                "province": "تهران",
                "phone": "02133445566",
                "latitude": 35.7009,
                "longitude": 51.3707,
                "map_zoom": 16,
            },
        )
        counter += int(created)

        for platform, value, header in [
            ("telegram", "saafkari_shop", True),
            ("instagram", "saafkari_shop", True),
            ("whatsapp", "09121234567", True),
            ("twitter", "saafkari_shop", False),
            ("phone", "09121234567", True),
        ]:
            _link, made = SocialLink.objects.get_or_create(
                platform=platform, defaults={"value": value, "show_in_header": header}
            )
            counter += int(made)

        WorkingHour.ensure_defaults()

        # -------------------------------------------------------- خدمات
        categories = {}
        for name, order in [("صافکاری", 1), ("نقاشی", 2), ("پولیش و سرامیک", 3)]:
            category, _ = ServiceCategory.objects.get_or_create(name=name, defaults={"order": order})
            categories[name] = category

        services_data = [
            ("صافکاری بدون رنگ (PDR)", "صافکاری", 850000, 90,
             "برداشتن فرورفتگی بدون آسیب به رنگ اصلی خودرو.",
             "در روش PDR با ابزار مخصوص از پشت قطعه، فرورفتگی به آرامی به حالت اول برمی‌گردد. "
             "رنگ اصلی خودرو دست‌نخورده می‌ماند و ارزش خودرو حفظ می‌شود."),
            ("صافکاری و تعویض قطعه", "صافکاری", 0, 240,
             "بازسازی قطعات آسیب‌دیده یا تعویض با قطعه‌ی نو.",
             "برای آسیب‌های شدید، قطعه صاف یا در صورت نیاز تعویض می‌شود و سپس آماده‌سازی رنگ انجام می‌گیرد."),
            ("نقاشی کوره‌ای قطعه", "نقاشی", 1500000, 300,
             "رنگ‌آمیزی با کد رنگ کارخانه و پخت در کوره.",
             "کد رنگ خودرو خوانده می‌شود، رنگ ساخته و پس از آماده‌سازی سطح، در کوره پخته می‌شود."),
            ("پولیش و واکس بدنه", "پولیش و سرامیک", 600000, 120,
             "برطرف‌کردن خط‌وخش‌های سطحی و براق‌سازی بدنه.",
             "با پولیش سه‌مرحله‌ای، کدری و خط‌وخش‌های ریز برداشته می‌شود و بدنه براق می‌گردد."),
            ("پوشش سرامیک بدنه", "پولیش و سرامیک", 3500000, 360,
             "محافظت طولانی‌مدت از رنگ خودرو در برابر خط‌وخش.",
             "لایه‌ی سرامیک روی رنگ می‌نشیند و تا مدت‌ها از بدنه در برابر آفتاب و آلودگی محافظت می‌کند."),
            ("تعمیر و تعویض شیشه", "صافکاری", 0, 120,
             "تعویض شیشه‌ی شکسته با شیشه‌ی استاندارد.",
             "شیشه‌ی آسیب‌دیده با شیشه‌ی استاندارد و چسب مخصوص تعویض می‌شود."),
        ]
        services = []
        for index, (title, category_name, price, duration, short, long_text) in enumerate(services_data):
            service, made = Service.objects.get_or_create(
                title=title,
                defaults={
                    "category": categories[category_name],
                    "base_price": price,
                    "duration_minutes": duration,
                    "short_description": short,
                    "description": long_text,
                    "is_featured": index < 3,
                    "order": index,
                    "price_note": "" if price else "قیمت پس از کارشناسی",
                },
            )
            if made and with_images:
                service.image.save(f"service-{index}.jpg", make_image(title, 900, 600, index), save=True)
            services.append(service)
            counter += int(made)

        # --------------------------------------------------- نمونه‌کارها
        portfolio_data = [
            ("بازسازی گلگیر جلو پژو ۲۰۶", "پژو ۲۰۶ تیپ ۵ سفید", 0, "۲ روز کاری"),
            ("صافکاری بدون رنگ درب راننده", "پراید ۱۳۱ نقره‌ای", 0, "۴ ساعت"),
            ("نقاشی کامل کاپوت سمند", "سمند LX مشکی", 2, "۳ روز کاری"),
            ("پولیش و سرامیک بدنه", "تیبا ۲ آبی", 3, "۱ روز کاری"),
        ]
        for index, (title, car, service_index, duration) in enumerate(portfolio_data):
            item, made = PortfolioItem.objects.get_or_create(
                title=title,
                defaults={
                    "service": services[service_index] if service_index < len(services) else None,
                    "car_name": car,
                    "duration_label": duration,
                    "description": "عکس‌های پیش از شروع کار و پس از تحویل خودرو، از زاویه‌های مختلف.",
                    "completed_at": timezone.localdate() - dt.timedelta(days=10 * (index + 1)),
                    "is_featured": index < 3,
                    "order": index,
                },
            )
            counter += int(made)
            if made and with_images:
                # برای هر نمونه‌کار: ۲ عکس «قبل» و ۲ عکس «بعد»
                for position in range(2):
                    PortfolioImage.objects.create(
                        item=item, kind=PortfolioImage.Kind.BEFORE,
                        caption=f"قبل — نمای {position + 1}", order=position,
                        image=make_image(f"BEFORE {index}-{position}", 900, 600, index + position, f"before-{index}-{position}.jpg"),
                    )
                for position in range(2):
                    PortfolioImage.objects.create(
                        item=item, kind=PortfolioImage.Kind.AFTER,
                        caption=f"بعد — نمای {position + 1}", order=position,
                        image=make_image(f"AFTER {index}-{position}", 900, 600, index + position + 2, f"after-{index}-{position}.jpg"),
                    )
                item.cover.save(f"cover-{index}.jpg", make_image(title, 1000, 700, index + 1), save=True)

        # -------------------------------------------------------- بنرها
        banners_data = [
            ("صافکاری بدون رنگ، بدون آسیب به رنگ خودرو", "کارشناسی رایگان پس از ارسال عکس خودرو", "hero"),
            ("نقاشی کوره‌ای با رنگ اصل", "تطبیق دقیق کد رنگ کارخانه", "hero"),
            ("پولیش تخصصی بدنه", "بدنه‌ی خودرو را نو کنید", "middle"),
        ]
        for index, (title, subtitle, position) in enumerate(banners_data):
            banner, made = Banner.objects.get_or_create(
                title=title,
                defaults={"subtitle": subtitle, "position": position, "order": index},
            )
            counter += int(made)
            if made:
                if with_images:
                    banner.image.save(f"banner-{index}.jpg", make_image(title, 1600, 800, index + 2), save=True)
                else:
                    banner.delete()  # بنر بدون تصویر معنا ندارد

        # ------------------------------------------------------- مقالات
        blog_category, _ = ArticleCategory.objects.get_or_create(name="راهنمای خودرو")
        articles_data = [
            ("صافکاری بدون رنگ چیست و چه زمانی جواب می‌دهد؟",
             "در این روش، فرورفتگی بدنه بدون آسیب‌زدن به رنگ اصلی برطرف می‌شود.",
             "صافکاری بدون رنگ یا PDR روشی است که در آن با ابزار مخصوص از پشت قطعه، فرورفتگی به حالت اول برمی‌گردد.\n\n"
             "این روش زمانی جواب می‌دهد که رنگ خودرو ترک نخورده و فلز کشیده نشده باشد. مزیت بزرگ آن، حفظ رنگ کارخانه است.\n\n"
             "اگر فرورفتگی روی لبه‌ی قطعه یا نزدیک درزها باشد، ممکن است کارشناس روش دیگری پیشنهاد دهد."),
            ("چطور بفهمیم خودرو رنگ‌شدگی دارد؟",
             "چند نشانه‌ی ساده که هنگام خرید خودروی دست‌دوم باید بررسی کنید.",
             "یکدست‌نبودن رنگ در نور آفتاب، تفاوت بافت رنگ و پاشش رنگ روی نوارهای لاستیکی از نشانه‌های رنگ‌شدگی است.\n\n"
             "بهترین راه، استفاده از دستگاه ضخامت‌سنج رنگ است. عدد طبیعی رنگ کارخانه معمولاً بین ۹۰ تا ۱۴۰ میکرون است.\n\n"
             "پیش از خرید، خودرو را به یک کارشناس بدنه نشان دهید."),
            ("نگهداری از رنگ خودرو پس از نقاشی",
             "تا یک ماه پس از نقاشی، چند نکته را رعایت کنید.",
             "تا دو هفته خودرو را زیر آفتاب شدید پارک نکنید و از واکس استفاده نکنید.\n\n"
             "شستشو را با آب ولرم و شامپوی مخصوص انجام دهید و از برس زبر استفاده نکنید.\n\n"
             "پس از یک ماه می‌توانید پولیش و واکس را انجام دهید تا رنگ تثبیت شود."),
        ]
        staff = get_user_model().objects.filter(is_staff=True).first()
        for index, (title, summary, content) in enumerate(articles_data):
            article, made = Article.objects.get_or_create(
                title=title,
                defaults={
                    "category": blog_category,
                    "summary": summary,
                    "content": content,
                    "author": staff,
                    "is_featured": index == 0,
                    "tags": "صافکاری, نقاشی خودرو, نگهداری",
                    "published_at": timezone.now() - dt.timedelta(days=index * 3),
                },
            )
            counter += int(made)
            if made and with_images:
                article.cover.save(f"article-{index}.jpg", make_image(title, 1000, 600, index + 3), save=True)

        self.stdout.write(self.style.SUCCESS(f"داده‌های نمونه ساخته شد. ({counter} مورد تازه)"))
        if not with_images:
            self.stdout.write("برای ساخت تصاویر نمونه، دستور را با سوییچ --with-images اجرا کنید.")
