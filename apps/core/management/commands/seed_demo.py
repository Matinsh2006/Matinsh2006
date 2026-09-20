"""ساخت داده‌های نمونه برای دمو: بنر، دسته‌بندی، برند، سایز، رنگ و محصول."""
import random
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from apps.catalog.models import (
    Brand,
    Category,
    Color,
    Gender,
    Product,
    ProductImage,
    ProductKind,
    ProductVariant,
    Size,
)
from apps.core.models import Banner, SiteSetting

PALETTE = [
    ("#f43f6e", "#88133c"),
    ("#0ea5e9", "#0c4a6e"),
    ("#10b981", "#064e3b"),
    ("#f59e0b", "#7c2d12"),
    ("#8b5cf6", "#4c1d95"),
    ("#64748b", "#1e293b"),
]


def make_image(width, height, colors, label=""):
    """تصویر نمونه با گرادیان ساده می‌سازد (بدون نیاز به اینترنت)."""
    start, end = (int(colors[0][i : i + 2], 16) for i in (1, 3, 5)), (
        int(colors[1][i : i + 2], 16) for i in (1, 3, 5)
    )
    start, end = list(start), list(end)
    image = Image.new("RGB", (width, height), tuple(start))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        ratio = y / max(height - 1, 1)
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(int(start[i] + (end[i] - start[i]) * ratio) for i in range(3)),
        )
    if label:
        draw.text((width // 2 - len(label) * 3, height // 2), label, fill="#ffffff")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = "ساخت داده‌های نمونه برای نمایش دمو فروشگاه"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="حذف داده‌های نمونه قبلی")

    def handle(self, *args, **options):
        random.seed(7)
        if options["flush"]:
            ProductVariant.objects.all().delete()
            ProductImage.objects.all().delete()
            Product.objects.all().delete()
            Banner.objects.all().delete()
            self.stdout.write("داده‌های قبلی حذف شد.")

        self._site_settings()
        self._banners()
        sizes = self._sizes()
        colors = self._colors()
        brands = self._brands()
        categories = self._categories()
        self._products(categories, brands, sizes, colors)
        self.stdout.write(self.style.SUCCESS("داده‌های نمونه با موفقیت ساخته شد."))

    # ------------------------------------------------------------------
    def _site_settings(self):
        site = SiteSetting.load()
        site.site_name = "بوتیک ایرانی"
        site.tagline = "پوشاک، کیف و کفش ایرانی با طراحی اصیل"
        site.about = (
            "بوتیک ایرانی از سال ۱۳۹۵ با هدف عرضه پوشاک باکیفیت ایرانی فعالیت می‌کند.\n"
            "تمام محصولات ما توسط تولیدکنندگان داخلی و با پارچه درجه یک دوخته می‌شوند."
        )
        site.phone = "02112345678"
        site.email = "info@boutique.ir"
        site.city = "تهران"
        site.address = "خیابان ولیعصر، نرسیده به پارک ساعی، پلاک ۱۲۰"
        site.postal_code = "1511943943"
        site.latitude = 35.744660
        site.longitude = 51.415860
        site.working_hours = "شنبه تا پنجشنبه، ۱۰ صبح تا ۹ شب"
        site.telegram = "https://t.me/example_shop"
        site.instagram = "https://instagram.com/example_shop"
        site.whatsapp = "989121234567"
        site.twitter = "https://twitter.com/example_shop"
        site.shipping_cost = 45000
        site.free_shipping_threshold = 2000000
        site.save()
        self.stdout.write("تنظیمات سایت ثبت شد.")

    def _banners(self):
        data = [
            ("کالکشن پاییز ۱۴۰۴", "جدیدترین مانتوهای ایرانی با ۲۰٪ تخفیف", "مشاهده کالکشن", "/shop/women/"),
            ("کیف‌های چرم طبیعی", "دست‌دوز، با ضمانت یک‌ساله", "خرید کیف", "/shop/?kind=bag"),
            ("پوشاک مردانه", "پیراهن و شلوار با دوخت ایرانی", "مشاهده محصولات", "/shop/men/"),
        ]
        for index, (title, subtitle, button, link) in enumerate(data):
            if Banner.objects.filter(title=title).exists():
                continue
            banner = Banner(title=title, subtitle=subtitle, button_text=button, link=link, order=index)
            banner.image.save(
                f"banner-{index + 1}.jpg", make_image(1400, 560, PALETTE[index % len(PALETTE)]), save=False
            )
            banner.save()
        self.stdout.write(f"{Banner.objects.count()} بنر آماده شد.")

    def _sizes(self):
        plan = {
            ProductKind.CLOTHING: ["XS", "S", "M", "L", "XL", "XXL"],
            ProductKind.SHOES: ["37", "38", "39", "40", "41", "42", "43", "44"],
            ProductKind.BAG: ["کوچک", "متوسط", "بزرگ"],
            ProductKind.ACCESSORY: ["تک‌سایز"],
        }
        sizes = {}
        for kind, labels in plan.items():
            sizes[kind] = [
                Size.objects.get_or_create(label=label, size_type=kind, defaults={"order": i})[0]
                for i, label in enumerate(labels)
            ]
        return sizes

    def _colors(self):
        data = [
            ("مشکی", "#111827"), ("سفید", "#f8fafc"), ("سرمه‌ای", "#1e3a8a"),
            ("کرم", "#e7d8c9"), ("زرشکی", "#7f1d1d"), ("زیتونی", "#4d7c0f"),
            ("صورتی", "#f472b6"), ("قهوه‌ای", "#78350f"),
        ]
        return [Color.objects.get_or_create(name=n, defaults={"hex_code": h})[0] for n, h in data]

    def _brands(self):
        data = [
            ("هاکوپیان", "ایران"), ("درسا", "ایران"), ("چرم مشهد", "ایران"),
            ("زی‌بافت", "ایران"), ("پاتن جامه", "ایران"),
        ]
        brands = []
        for name, country in data:
            brand, _ = Brand.objects.get_or_create(name=name, defaults={"country": country})
            brands.append(brand)
        return brands

    def _categories(self):
        plan = {
            Gender.WOMEN: ["مانتو و پالتو", "شومیز و بلوز", "شلوار زنانه", "کیف زنانه", "کفش زنانه"],
            Gender.MEN: ["پیراهن مردانه", "تی‌شرت مردانه", "شلوار مردانه", "کیف مردانه", "کفش مردانه"],
        }
        categories = {}
        for gender, names in plan.items():
            categories[gender] = [
                Category.objects.get_or_create(name=name, gender=gender, parent=None, defaults={"order": i})[0]
                for i, name in enumerate(names)
            ]
        return categories

    def _products(self, categories, brands, sizes, colors):
        templates = {
            Gender.WOMEN: [
                ("مانتو کتان جلو باز", ProductKind.CLOTHING, 0, 1_450_000),
                ("شومیز ابریشمی طرح‌دار", ProductKind.CLOTHING, 1, 890_000),
                ("شلوار پارچه‌ای دم‌پا گشاد", ProductKind.CLOTHING, 2, 760_000),
                ("کیف دوشی چرم طبیعی", ProductKind.BAG, 3, 2_350_000),
                ("کفش لوفر چرم زنانه", ProductKind.SHOES, 4, 1_890_000),
                ("مانتو مجلسی آستین بلند", ProductKind.CLOTHING, 0, 1_980_000),
            ],
            Gender.MEN: [
                ("پیراهن آستین بلند کلاسیک", ProductKind.CLOTHING, 0, 980_000),
                ("تی‌شرت نخ پنبه یقه گرد", ProductKind.CLOTHING, 1, 420_000),
                ("شلوار جین راسته", ProductKind.CLOTHING, 2, 1_150_000),
                ("کیف اداری چرم", ProductKind.BAG, 3, 3_200_000),
                ("کفش رسمی چرم مردانه", ProductKind.SHOES, 4, 2_450_000),
                ("پیراهن کتان تابستانی", ProductKind.CLOTHING, 0, 850_000),
            ],
        }

        created = 0
        for gender, items in templates.items():
            for index, (title, kind, category_index, price) in enumerate(items):
                if Product.objects.filter(title=title).exists():
                    continue
                product = Product.objects.create(
                    title=title,
                    category=categories[gender][category_index],
                    brand=random.choice(brands),
                    kind=kind,
                    gender=gender,
                    short_description="دوخت ایرانی، پارچه درجه یک و ارسال سریع به سراسر کشور.",
                    description=(
                        "این محصول از تولیدکنندگان داخلی تهیه شده است.\n"
                        "جنس: پارچه درجه یک ایرانی\n"
                        "شست‌وشو: با آب سرد و شوینده ملایم\n"
                        "ارسال: ۲ تا ۵ روز کاری"
                    ),
                    price=price,
                    discount_price=int(price * 0.85) if index % 3 == 0 else None,
                    is_featured=index % 2 == 0,
                )

                for image_index in range(3):
                    palette = PALETTE[(index + image_index) % len(PALETTE)]
                    image = ProductImage(product=product, is_main=image_index == 0, order=image_index)
                    image.image.save(
                        f"{product.slug}-{image_index + 1}.jpg",
                        make_image(900, 1200, palette),
                        save=False,
                    )
                    image.save()

                for size in sizes[kind]:
                    for color in random.sample(colors, k=3):
                        ProductVariant.objects.get_or_create(
                            product=product,
                            size=size,
                            color=color,
                            defaults={"stock": random.choice([0, 2, 4, 7, 12])},
                        )
                created += 1

        self.stdout.write(f"{created} محصول نمونه ساخته شد.")
