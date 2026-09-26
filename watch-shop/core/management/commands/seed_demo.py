"""
Fill the database with a complete demo store: settings, brands, the
"type › gender" category tree, products with several photos each, banners,
store locations and static pages.

    python manage.py seed_demo              # idempotent, safe to re-run
    python manage.py seed_demo --with-admin # also creates a demo superuser
"""
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from catalog.models import Brand, Category, Gender, Product, ProductImage, ProductSpec
from core.models import Banner, Page, SiteSettings, StoreLocation

SEED_DIR = Path(settings.BASE_DIR) / "seed" / "images"

BRANDS = [
    ("saniyeh", "ثانیه", "Saniyeh", "ایران", "برند اختصاصی گالری؛ طراحی ایرانی با اعداد فارسی و تقویم شمسی."),
    ("aurelius", "اورلیوس", "Aurelius", "سوئیس", "ساعت‌های غواصی و ابزاری با استانداردهای سخت‌گیرانه سوئیسی."),
    ("nordvik", "نوردویک", "Nordvik", "سوئد", "کرنوگراف‌هایی با طراحی مینیمال اسکاندیناویایی."),
    ("maris", "ماریس", "Maris", "ایتالیا", "ظرافت کلاسیک ایتالیایی برای لحظه‌های رسمی."),
    ("kaveh", "کاوه", "Kaveh", "ایران", "ساعت‌های روزمره با کیفیت ساخت بالا و قیمت منصفانه."),
    ("lumen", "لومن", "Lumen", "ژاپن", "ساعت‌های هوشمند با باتری ماندگار و طراحی ظریف."),
]

CATEGORIES = [
    ("sport", "اسپرت", "برای ماجراجویی‌های هر روز", "مقاوم در برابر آب و ضربه، آماده برای ورزش و سفر."),
    ("classic", "کلاسیک", "ظرافتی که هرگز از مد نمی‌افتد", "ساعت‌های رسمی و مجلسی با طراحی ماندگار."),
    ("luxury", "لوکس", "برای لحظه‌های به‌یادماندنی", "فلزات گران‌بها، نگین‌کاری و موتورهای اتوماتیک."),
    ("smart", "هوشمند", "زمان، به سبک امروز", "سلامت، ورزش و اعلان‌ها روی مچ دست شما."),
]

# key: (brand, category, gender, name, model, price, compare_at, stock, movement, strap, case, diameter, water, glass, featured, images, short)
PRODUCTS = [
    ("presidential-rose", "saniyeh", "luxury", "men", "ساعت مردانه پرزیدنت رزگلد", "Presidential 40", 189_000_000, None, 3,
     "automatic", "gold", "رزگلد ۱۸ عیار", 40, 100, "sapphire", True, 4,
     "بدنه و بند رزگلد با بزل کنگره‌ای، صفحه شکلاتی سان‌برست، روز هفته و تاریخ شمسی."),
    ("deep-sea-black", "aurelius", "sport", "men", "ساعت مردانه غواصی مشکی", "Deep Sea 300", 42_500_000, 48_000_000, 7,
     "automatic", "steel", "استیل ۳۱۶L", 42, 300, "sapphire", True, 3,
     "ساعت غواصی حرفه‌ای با بزل چرخان سرامیکی و عقربه‌های شب‌تاب."),
    ("deep-sea-blue", "aurelius", "sport", "men", "ساعت مردانه غواصی سرمه‌ای بند رابر", "Deep Sea Blue", 38_900_000, None, 5,
     "automatic", "rubber", "استیل ۳۱۶L", 42, 300, "sapphire", False, 3,
     "نسخه سرمه‌ای با بند رابر نرم؛ همراه همیشگی برای شنا و سفر."),
    ("chrono-panda", "nordvik", "sport", "men", "ساعت مردانه کرنوگراف پاندا", "Chrono Panda", 56_000_000, None, 4,
     "automatic", "steel", "استیل", 41, 100, "sapphire", True, 3,
     "کرنوگراف با صفحه سفید و سه زیرصفحه، بزل تاکیمتر برای اندازه‌گیری سرعت."),
    ("noir-chrono", "nordvik", "sport", "men", "ساعت مردانه کرنوگراف مشکی مات", "Noir Chrono", 49_000_000, 54_000_000, 2,
     "quartz", "rubber", "استیل با پوشش PVD مشکی", 43, 100, "sapphire", False, 3,
     "تمام‌مشکی و مات؛ کرنوگراف اسپرت با بند رابر."),
    ("classico-oro", "maris", "classic", "men", "ساعت مردانه کلاسیک طلایی بند چرم", "Classico Oro", 24_700_000, None, 6,
     "automatic", "leather", "استیل با روکش طلا", 40, 50, "sapphire", False, 3,
     "صفحه نقره‌ای با اعداد رومی و بند چرم طبیعی قهوه‌ای."),
    ("kaveh-blue", "kaveh", "classic", "men", "ساعت مردانه کلاسیک صفحه آبی", "Kaveh Blue 39", 18_900_000, 21_000_000, 9,
     "automatic", "steel", "استیل", 39, 100, "sapphire", True, 3,
     "صفحه آبی سان‌برست با شاخص‌های برجسته و بند استیل."),
    ("presidential-green", "saniyeh", "luxury", "men", "ساعت مردانه لوکس صفحه سبز طلایی", "Presidential Green", 176_000_000, None, 2,
     "automatic", "gold", "طلای زرد ۱۸ عیار", 40, 100, "sapphire", False, 3,
     "طلای زرد با صفحه سبز زیتونی و اعداد فارسی برجسته."),
    ("pulse-one", "lumen", "smart", "men", "ساعت هوشمند مردانه مشکی", "Pulse One", 12_900_000, 14_500_000, 12,
     "smart", "rubber", "آلومینیوم", 45, 50, "sapphire", False, 3,
     "پایش ضربان قلب، قدم‌شمار و اعلان‌ها؛ با شارژ ۷ روزه."),
    ("perla-32", "saniyeh", "luxury", "women", "ساعت زنانه لوکس صفحه صدفی با نگین", "Perla 32", 142_000_000, None, 2,
     "automatic", "gold", "رزگلد ۱۸ عیار", 32, 50, "sapphire", True, 4,
     "صفحه صدفی رنگین‌کمانی، بزل و شاخص‌های نگین‌دار و بند رزگلد."),
    ("milano-rosa", "maris", "classic", "women", "ساعت زنانه کلاسیک بند حصیری رزگلد", "Milano Rosa", 16_800_000, 19_500_000, 8,
     "quartz", "mesh", "استیل با روکش رزگلد", 32, 30, "mineral", True, 3,
     "بند حصیری میلانیز و صفحه صورتی؛ ظریف برای هر روز."),
    ("classica-donna", "maris", "classic", "women", "ساعت زنانه کلاسیک شامپاینی بند چرم", "Classica Donna", 21_300_000, None, 5,
     "quartz", "leather", "استیل با روکش طلا", 32, 30, "sapphire", False, 3,
     "صفحه شامپاینی با اعداد رومی و بند چرم کرم."),
    ("aqua-lady", "aurelius", "sport", "women", "ساعت زنانه اسپرت سفید", "Aqua Lady", 29_800_000, None, 6,
     "automatic", "rubber", "استیل ۳۱۶L", 36, 200, "sapphire", True, 3,
     "ساعت اسپرت زنانه با صفحه سفید، بزل غواصی و بند رابر سفید."),
    ("chrono-rose", "nordvik", "sport", "women", "ساعت زنانه کرنوگراف رزگلد", "Chrono Rosé", 33_500_000, 36_000_000, 4,
     "quartz", "rubber", "استیل با روکش رزگلد", 36, 100, "sapphire", False, 3,
     "کرنوگراف رزگلد با صفحه صدفی و بند رابر به رنگ پوست."),
    ("pulse-rose", "lumen", "smart", "women", "ساعت هوشمند زنانه رزگلد", "Pulse Rosé", 11_400_000, None, 10,
     "smart", "rubber", "آلومینیوم رزگلد", 41, 50, "sapphire", False, 3,
     "ساعت هوشمند سبک با بند سیلیکونی صورتی."),
    ("shirin-34", "kaveh", "luxury", "women", "ساعت زنانه لوکس طلایی صفحه شامپاینی", "Shirin 34", 98_000_000, None, 3,
     "automatic", "gold", "طلای زرد", 34, 100, "sapphire", False, 3,
     "بزل کنگره‌ای طلایی و صفحه شامپاینی با اعداد فارسی."),
]

EXTRA_SPECS = {
    "presidential-rose": [("ذخیره انرژی", "۷۰ ساعت"), ("تعداد جواهر", "۳۱"), ("قابلیت‌ها", "روز هفته فارسی و تاریخ شمسی")],
    "deep-sea-black": [("بزل", "چرخان یک‌طرفه سرامیکی"), ("شب‌تاب", "سوپرلومینوا")],
    "chrono-panda": [("قابلیت‌ها", "کرنوگراف، تاکیمتر، تاریخ")],
    "pulse-one": [("باتری", "تا ۷ روز"), ("سنسورها", "ضربان قلب، اکسیژن خون، GPS")],
    "perla-32": [("نگین", "۴۴ الماس روی بزل")],
}

PAGES = [
    ("about", "درباره ما", 0,
     "<p>گالری ساعت ثانیه از سال ۱۴۰۵ با یک هدف ساده شروع به کار کرد: عرضه ساعت‌های اصل، با مشاوره صادقانه و خدمات پس از فروش واقعی.</p>"
     "<h2>چرا ثانیه؟</h2><ul><li>ضمانت اصالت تمام کالاها</li><li>ارسال بیمه‌شده به سراسر ایران</li><li>۷ روز ضمانت بازگشت</li></ul>"),
    ("terms", "قوانین و مقررات", 1,
     "<p>ثبت سفارش در فروشگاه به معنای پذیرش قوانین زیر است.</p><h2>ثبت سفارش</h2><p>سفارش پس از پرداخت موفق قطعی می‌شود و وضعیت آن از بخش «سفارش‌های من» قابل پیگیری است.</p>"
     "<h2>بازگشت کالا</h2><p>تا ۷ روز پس از دریافت، در صورت سالم بودن پلمب و بسته‌بندی، امکان بازگشت کالا وجود دارد.</p>"),
    ("shipping", "شیوه‌های ارسال", 2,
     "<p>سفارش‌های تهران با پیک ویژه و سایر شهرها با پست پیشتاز بیمه‌شده ارسال می‌شوند.</p><ul><li>تهران: ۱ تا ۲ روز کاری</li><li>سایر شهرها: ۲ تا ۴ روز کاری</li></ul>"),
    ("warranty", "ضمانت اصالت و گارانتی", 3,
     "<p>تمام ساعت‌ها همراه با کارت گارانتی معتبر عرضه می‌شوند. در صورت اثبات عدم اصالت، وجه پرداختی به‌طور کامل بازگردانده می‌شود.</p>"),
]


class Command(BaseCommand):
    help = "Creates demo data (settings, brands, categories, products with photos, banners, stores, pages)."

    def add_arguments(self, parser):
        parser.add_argument("--with-admin", action="store_true", help="Create the demo superuser 09120000000 / admin12345")

    @transaction.atomic
    def handle(self, *args, **options):
        self._settings()
        brands = self._brands()
        categories = self._categories()
        self._products(brands, categories)
        self._banners()
        self._stores()
        self._pages()
        self._finish_settings()
        if options["with_admin"]:
            self._admin()
        call_command("warm_thumbnails", verbosity=0)
        self.stdout.write(self.style.SUCCESS("Demo store is ready."))

    # ------------------------------------------------------------------
    def _image(self, name):
        path = SEED_DIR / name
        return path if path.exists() else None

    def _settings(self):
        site = SiteSettings.load()
        site.site_name = "ثانیه"
        site.site_name_en = "SANIYEH"
        site.tagline = "گالری ساعت‌های اصل مردانه و زنانه"
        site.phone = "021-88776655"
        site.mobile = "0912-345-6789"
        site.email = "info@example.com"
        site.address = "تهران، خیابان ولیعصر، بالاتر از میدان ونک، کوچه نگار، پلاک ۱۸"
        site.working_hours = "شنبه تا پنجشنبه، ۱۰ تا ۲۲"
        site.instagram = "saniyeh.gallery"
        site.telegram = "saniyeh_gallery"
        site.whatsapp = "09123456789"
        site.twitter = "saniyeh_gallery"
        site.footer_about = "گالری ثانیه؛ عرضه‌کننده ساعت‌های اصل مردانه و زنانه با ضمانت اصالت، ارسال بیمه‌شده و مشاوره تخصصی."
        site.meta_description = "خرید آنلاین ساعت مچی اصل مردانه و زنانه؛ اسپرت، کلاسیک، لوکس و هوشمند با ضمانت اصالت."
        site.save()

    def _brands(self):
        brands = {}
        for index, (slug, name, name_en, country, description) in enumerate(BRANDS):
            brand, _ = Brand.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "name_en": name_en, "country": country, "description": description, "order": index},
            )
            brands[slug] = brand
        return brands

    def _categories(self):
        tree = {}
        for index, (slug, name, tagline, description) in enumerate(CATEGORIES):
            root, _ = Category.objects.update_or_create(
                parent=None, slug=slug, defaults={"name": name, "tagline": tagline, "description": description, "order": index}
            )
            for child_index, (child_slug, child_name, gender) in enumerate(
                [("men", "مردانه", Gender.MEN), ("women", "زنانه", Gender.WOMEN)]
            ):
                child, _ = Category.objects.update_or_create(
                    parent=root, slug=child_slug, defaults={"name": child_name, "gender": gender, "order": child_index}
                )
                tree[(slug, child_slug)] = child
        return tree

    def _products(self, brands, categories):
        for index, (key, brand, category, gender, name, model, price, compare, stock, movement, strap, case, diameter,
                    water, glass, featured, image_count, short) in enumerate(PRODUCTS):
            product, _ = Product.objects.update_or_create(
                slug=key,
                defaults={
                    "name": name,
                    "name_en": model,
                    "sku": f"SN-{1001 + index}",
                    "brand": brands[brand],
                    "category": categories[(category, gender)],
                    "short_description": short,
                    "description": (
                        f"{short}\n\nاین ساعت با ضمانت اصالت کالا و کارت گارانتی عرضه می‌شود و در جعبه اختصاصی "
                        "به همراه دفترچه راهنما ارسال خواهد شد."
                    ),
                    "price": price,
                    "compare_at_price": compare,
                    "stock": stock,
                    "movement": movement,
                    "strap_material": strap,
                    "case_material": case,
                    "case_diameter": diameter,
                    "water_resistance": water,
                    "glass": glass,
                    "warranty": "۲ سال گارانتی بین‌المللی",
                    "is_featured": featured,
                    "is_active": True,
                },
            )
            if not product.images.exists():
                for order in range(1, image_count + 1):
                    path = self._image(f"{key}-{order}.webp")
                    if path is None:
                        continue
                    with path.open("rb") as handle:
                        ProductImage.objects.create(
                            product=product,
                            image=File(handle, name=path.name),
                            alt=f"{name} — تصویر {order}",
                            order=order,
                        )
            ProductSpec.objects.filter(product=product).delete()
            for order, (label, value) in enumerate(EXTRA_SPECS.get(key, [])):
                ProductSpec.objects.create(product=product, label=label, value=value, order=order)

    def _banners(self):
        Banner.objects.update_or_create(
            title="جشنواره پاییزه ثانیه؛ تا ۲۰٪ تخفیف ساعت‌های منتخب",
            placement=Banner.Placement.HEADER,
            defaults={
                "subtitle": "ارسال رایگان و بیمه‌شده برای تمام سفارش‌های جشنواره",
                "link": "/shop/?discount=1",
                "button_text": "مشاهده تخفیف‌ها",
                "style": Banner.Style.GOLD,
                "order": 0,
            },
        )
        for order, (title, subtitle, link, button, image) in enumerate(
            [
                ("مجموعه اسپرت ۱۴۰۵", "ساعت‌هایی برای عمق دریا و اوج کوه؛ مقاوم، دقیق و شب‌تاب.", "/category/sport/", "مشاهده مجموعه", "banner-sport.webp"),
                ("هدیه‌ای برای همیشه", "ساعت‌های زنانه لوکس با صفحه صدفی و نگین‌های درخشان.", "/category/luxury/women/", "انتخاب هدیه", "banner-women.webp"),
            ]
        ):
            banner, created = Banner.objects.get_or_create(
                title=title,
                placement=Banner.Placement.HOME,
                defaults={"subtitle": subtitle, "link": link, "button_text": button, "order": order, "is_dismissible": False},
            )
            path = self._image(image)
            if path and not banner.image:
                with path.open("rb") as handle:
                    banner.image.save(path.name, File(handle), save=True)

    def _stores(self):
        StoreLocation.objects.update_or_create(
            name="گالری ثانیه — شعبه ونک",
            defaults={
                "address": "تهران، خیابان ولیعصر، بالاتر از میدان ونک، کوچه نگار، پلاک ۱۸، طبقه همکف",
                "phone": "021-88776655",
                "working_hours": "شنبه تا پنجشنبه ۱۰ تا ۲۲ · جمعه‌ها ۱۶ تا ۲۲",
                "latitude": "35.757450",
                "longitude": "51.409680",
                "zoom": 16,
                "order": 0,
            },
        )
        StoreLocation.objects.update_or_create(
            name="شعبه اصفهان — چهارباغ",
            defaults={
                "address": "اصفهان، خیابان چهارباغ عباسی، مجتمع تجاری سپاهان، طبقه اول، واحد ۴",
                "phone": "031-32211445",
                "working_hours": "شنبه تا پنجشنبه ۱۰ تا ۲۱",
                "latitude": "32.653900",
                "longitude": "51.667800",
                "zoom": 16,
                "order": 1,
            },
        )

    def _pages(self):
        for slug, title, order, content in PAGES:
            Page.objects.update_or_create(slug=slug, defaults={"title": title, "content": content, "order": order})

    def _finish_settings(self):
        site = SiteSettings.load()
        site.hero_product = Product.objects.filter(slug="presidential-rose").first()
        site.save()

    def _admin(self):
        phone = "09120000000"
        if not User.objects.filter(phone=phone).exists():
            User.objects.create_superuser(phone=phone, password="admin12345", first_name="مدیر", last_name="فروشگاه")
            self.stdout.write(self.style.WARNING(f"Demo superuser created: {phone} / admin12345 (change it!)"))
