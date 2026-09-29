"""
Fill the database with demo content so the storefront can be reviewed quickly:

    python manage.py seed_demo

Everything is created with get_or_create, so running it twice is safe. All
names, phone numbers and addresses are placeholders – replace them from the
admin panel before going live.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.blog.models import Article, ArticleCategory
from apps.catalog.models import Brand, Category, Product, ProductImage, ProductSpecification
from apps.core.models import Banner, Branch, Page, SiteSettings, SocialLink

from ._demo_images import category_image, logo_image, product_image, scene_image

PINK = (214, 51, 118)

CATEGORIES = [
    # (name, slug, icon kind, color, children [(name, slug)])
    ("مراقبت از پوست", "skin-care", "jar", (104, 158, 214), [
        ("کرم مرطوب‌کننده", "moisturizer"), ("ضدآفتاب", "sunscreen"), ("سرم پوست", "serum"), ("پاک‌کننده و تونر", "cleanser"),
    ]),
    ("آرایش صورت", "face-makeup", "compact", (221, 160, 120), [
        ("کرم پودر", "foundation"), ("پنکک و پودر", "powder"), ("رژگونه", "blush"),
    ]),
    ("آرایش چشم و ابرو", "eye-makeup", "palette", (150, 105, 170), [
        ("ریمل", "mascara"), ("خط چشم", "eyeliner"), ("سایه چشم", "eyeshadow"),
    ]),
    ("آرایش لب", "lip-makeup", "lipstick", (196, 38, 76), [
        ("رژ لب", "lipstick"), ("برق لب", "lip-gloss"), ("بالم لب", "lip-balm"),
    ]),
    ("مراقبت از مو", "hair-care", "pump", (132, 102, 186), [
        ("شامپو", "shampoo"), ("ماسک و نرم‌کننده مو", "hair-mask"),
    ]),
    ("عطر و ادکلن", "perfume", "perfume", (205, 150, 170), []),
]

BRANDS = [
    # (name, latin name, country, color)
    ("گلارا", "Glara", "ایران", (194, 24, 91)),
    ("مهرسا", "Mehrsa", "ایران", (142, 36, 170)),
    ("لیانا", "Liana", "فرانسه", (216, 67, 21)),
    ("آوین", "Avin", "ایران", (0, 137, 123)),
    ("نیلا", "Nila", "کره جنوبی", (30, 136, 229)),
    ("پرنیا", "Parnia", "ایران", (233, 30, 99)),
    ("ترنج", "Toranj", "ایران", (175, 125, 45)),
    ("روژان", "Rojan", "ایتالیا", (84, 110, 122)),
]

PRODUCTS = [
    # name, category slug, brand latin, price, discount, stock, kind, color, featured, sold, specs, summary
    ("کرم مرطوب‌کننده آبرسان هیالورونیک", "moisturizer", "Glara", 385000, 329000, 25, "jar", (110, 170, 225), True, 64,
     [("حجم", "۵۰ میلی‌لیتر"), ("مناسب برای", "انواع پوست به‌ویژه پوست خشک"), ("ویژگی", "آبرسانی ۲۴ ساعته")],
     "کرمی سبک و سریع‌الجذب برای آبرسانی عمیق و نرمی پوست در طول روز."),
    ("کرم ضدآفتاب رنگی SPF50", "sunscreen", "Nila", 520000, None, 18, "tube", (222, 184, 150), False, 51,
     [("حجم", "۵۰ میلی‌لیتر"), ("SPF", "۵۰"), ("مناسب برای", "پوست چرب و مختلط"), ("بافت", "فلوئید سبک")],
     "محافظت در برابر اشعه UVA و UVB با پوشش سبک و طبیعی، بدون ایجاد چربی."),
    ("سرم ویتامین C روشن‌کننده", "serum", "Liana", 690000, 589000, 12, "dropper", (240, 160, 60), True, 38,
     [("حجم", "۳۰ میلی‌لیتر"), ("ماده مؤثره", "ویتامین C پایدار"), ("مناسب برای", "پوست کدر و دارای لک")],
     "سرمی سبک برای یکدست‌کردن رنگ پوست و افزایش شفافیت آن."),
    ("ژل شست‌وشوی صورت پوست چرب", "cleanser", "Avin", 210000, None, 40, "pump", (110, 185, 145), False, 72,
     [("حجم", "۲۰۰ میلی‌لیتر"), ("مناسب برای", "پوست چرب و مستعد آکنه"), ("pH", "متعادل")],
     "پاک‌کننده ملایم روزانه که چربی اضافه را بدون خشک‌کردن پوست پاک می‌کند."),
    ("تونر گلاب و آلوئه‌ورا", "cleanser", "Parnia", 175000, 149000, 30, "bottle", (238, 160, 186), False, 45,
     [("حجم", "۲۵۰ میلی‌لیتر"), ("فاقد", "الکل"), ("مناسب برای", "انواع پوست")],
     "تونر آرام‌بخش با عصاره گلاب طبیعی برای طراوت و آماده‌سازی پوست."),
    ("کرم پودر مات با پوشش بالا", "foundation", "Mehrsa", 450000, None, 20, "bottle", (208, 158, 120), False, 29,
     [("حجم", "۳۰ میلی‌لیتر"), ("پوشش", "زیاد"), ("فینیش", "مات"), ("ماندگاری", "تا ۱۲ ساعت")],
     "کرم پودری با پوشش بالا و فینیش مات طبیعی، مناسب استفاده روزانه."),
    ("پنکک فشرده دو حالته", "powder", "Toranj", 330000, 279000, 15, "compact", (230, 190, 160), True, 33,
     [("وزن", "۱۲ گرم"), ("کاربرد", "خشک و مرطوب"), ("فینیش", "نیمه‌مات")],
     "پنککی نرم که هم به‌صورت خشک و هم مرطوب قابل استفاده است."),
    ("رژگونه پودری هلویی", "blush", "Liana", 298000, None, 0, "compact", (245, 150, 140), False, 58,
     [("وزن", "۶ گرم"), ("رنگ", "هلویی"), ("بافت", "پودری ابریشمی")],
     "رژگونه‌ای با رنگدانه‌های لطیف برای ظاهری شاداب و طبیعی."),
    ("ریمل حجم‌دهنده ضدآب", "mascara", "Glara", 365000, 310000, 22, "mascara", (45, 45, 58), False, 91,
     [("حجم", "۱۰ میلی‌لیتر"), ("ویژگی", "ضدآب و ضدریزش"), ("رنگ", "مشکی")],
     "ریمل حجم‌دهنده با برس مخصوص برای مژه‌هایی پرپشت و جدا از هم."),
    ("خط چشم ماژیکی مشکی", "eyeliner", "Nila", 255000, None, 35, "mascara", (30, 30, 40), False, 47,
     [("نوع", "ماژیکی"), ("ماندگاری", "تا ۲۴ ساعت"), ("رنگ", "مشکی")],
     "خط چشمی با نوک بسیار نازک برای کشیدن خطوط دقیق و ماندگار."),
    ("پالت سایه چشم ۱۲ رنگ نود", "eyeshadow", "Rojan", 780000, 650000, 9, "palette", (190, 140, 120), True, 22,
     [("تعداد رنگ", "۱۲"), ("بافت", "مات و شاین"), ("وزن هر رنگ", "۱٫۵ گرم")],
     "دوازده رنگ کاربردی نود برای آرایش روزانه تا مجلسی."),
    ("رژ لب جامد مات رنگ ۱۰۵", "lipstick", "Mehrsa", 280000, None, 50, "lipstick", (190, 30, 60), True, 120,
     [("رنگ", "قرمز آجری"), ("فینیش", "مات"), ("وزن", "۳٫۸ گرم")],
     "رژ لبی با رنگدانه بالا و بافت کرمی که لب‌ها را خشک نمی‌کند."),
    ("رژ لب مایع بادوام", "lipstick", "Glara", 320000, 272000, 27, "mascara", (200, 40, 90), False, 83,
     [("حجم", "۵ میلی‌لیتر"), ("ماندگاری", "تا ۱۶ ساعت"), ("فینیش", "مخملی")],
     "رژ لب مایع بسیار بادوام که پس از خشک شدن پاک نمی‌شود."),
    ("برق لب شیشه‌ای", "lip-gloss", "Liana", 199000, None, 3, "mascara", (240, 120, 160), False, 39,
     [("حجم", "۶ میلی‌لیتر"), ("جلوه", "براق و شیشه‌ای"), ("ویژگی", "غیرچسبنده")],
     "برق لبی سبک با جلوه شیشه‌ای و احساس راحت روی لب."),
    ("بالم لب ترمیم‌کننده", "lip-balm", "Parnia", 95000, None, 60, "lipstick", (248, 180, 190), False, 150,
     [("وزن", "۴ گرم"), ("ماده مؤثره", "شی‌باتر و ویتامین E")],
     "بالمی مغذی برای نرمی و ترمیم لب‌های خشک."),
    ("شامپو تقویت‌کننده کراتینه", "shampoo", "Avin", 240000, 204000, 45, "pump", (150, 110, 190), False, 66,
     [("حجم", "۴۰۰ میلی‌لیتر"), ("مناسب برای", "موهای آسیب‌دیده"), ("فاقد", "سولفات")],
     "شامپویی ملایم برای تقویت و درخشندگی موهای آسیب‌دیده."),
    ("ماسک مو آرگان", "hair-mask", "Toranj", 310000, None, 14, "jar", (220, 170, 90), False, 27,
     [("حجم", "۲۵۰ میلی‌لیتر"), ("ماده مؤثره", "روغن آرگان"), ("مناسب برای", "موهای خشک و وز")],
     "ماسک مغذی با روغن آرگان برای نرمی و کنترل وز مو."),
    ("ادوپرفیوم زنانه گل‌های بهاری", "perfume", "Rojan", 1650000, 1390000, 7, "perfume", (214, 120, 160), True, 19,
     [("حجم", "۱۰۰ میلی‌لیتر"), ("نوع", "ادوپرفیوم"), ("رایحه", "گلی و میوه‌ای")],
     "رایحه‌ای لطیف و ماندگار از ترکیب گل‌های بهاری و میوه‌های شیرین."),
]

PRODUCT_DESCRIPTION = """
<p>{summary}</p>
<h3>ویژگی‌های کلیدی</h3>
<ul>{features}</ul>
<h3>روش استفاده</h3>
<p>مقدار مناسبی از محصول را روی پوست تمیز استفاده کنید. برای بهترین نتیجه، از محصولات مکمل همان خانواده بهره ببرید.</p>
<blockquote>این محصول اصل است و با ضمانت اصالت کالا عرضه می‌شود.</blockquote>
"""

BANNERS = [
    # title, subtitle, button, link, colors, products, position
    ("حراج پاییزه لوازم آرایشی", "تا ۴۰٪ تخفیف روی برندهای محبوب", "مشاهده تخفیف‌ها", "/products/?discount=1",
     ((255, 214, 228), (214, 51, 118)), [("lipstick", (190, 30, 60), .12, .95), ("compact", (230, 190, 160), .27, .8), ("perfume", (214, 120, 160), .42, .9)], "hero"),
    ("مراقبت از پوست، هر روز", "کرم‌ها و سرم‌های اورجینال با ضمانت اصالت", "خرید محصولات پوستی", "/category/skin-care/",
     ((214, 236, 255), (84, 140, 214)), [("jar", (110, 170, 225), .14, .85), ("dropper", (240, 160, 60), .28, .9), ("tube", (222, 184, 150), .41, .85)], "hero"),
    ("رژ لب‌های جدید رسید!", "رنگ‌های ترند فصل را امتحان کنید", "مشاهده رژ لب‌ها", "/category/lip-makeup/",
     ((255, 226, 218), (196, 38, 76)), [("lipstick", (196, 38, 76), .12, .95), ("lipstick", (240, 120, 160), .24, .85), ("mascara", (200, 40, 90), .36, .9)], "hero"),
    ("ارسال رایگان به سراسر ایران", "برای خریدهای بالای ۱٫۵ میلیون تومان", "شروع خرید", "/products/",
     ((236, 228, 255), (132, 102, 186)), [("pump", (150, 110, 190), .15, .85), ("jar", (220, 170, 90), .3, .8)], "hero"),
    ("عطرهای خاص و ماندگار", "رایحه‌ای برای هر سلیقه", "", "/category/perfume/",
     ((255, 232, 240), (205, 120, 160)), [("perfume", (214, 120, 160), .2, .9)], "promo"),
    ("برندهای ایرانی محبوب", "کیفیت عالی با قیمت مناسب", "", "/brands/",
     ((228, 246, 240), (0, 137, 123)), [("bottle", (110, 185, 145), .15, .85), ("jar", (104, 158, 214), .3, .75)], "promo"),
]

PAGES = [
    ("درباره ما", "about", "<p>{site} یک فروشگاه اینترنتی تخصصی لوازم آرایشی و بهداشتی است که با هدف عرضه محصولات اصل و باکیفیت راه‌اندازی شده است.</p><h2>چرا ما؟</h2><ul><li>ضمانت اصالت تمام کالاها</li><li>ارسال سریع به سراسر کشور</li><li>مشاوره رایگان پیش و پس از خرید</li></ul><p>این متن نمونه است و از پنل مدیریت قابل ویرایش است.</p>"),
    ("قوانین و مقررات", "terms", "<h2>شرایط استفاده</h2><p>ثبت سفارش در این فروشگاه به معنای پذیرش قوانین زیر است.</p><ul><li>کالاهای آرایشی به دلیل رعایت بهداشت، پس از باز شدن پلمب قابل مرجوع نیستند.</li><li>در صورت دریافت کالای معیوب، حداکثر تا ۷ روز با پشتیبانی تماس بگیرید.</li><li>قیمت‌ها به تومان و شامل مالیات بر ارزش افزوده است.</li></ul><p>این متن نمونه است و از پنل مدیریت قابل ویرایش است.</p>"),
    ("حریم خصوصی", "privacy", "<p>اطلاعات شخصی شما (نام، شماره موبایل و آدرس) فقط برای پردازش و ارسال سفارش استفاده می‌شود و در اختیار شخص ثالث قرار نمی‌گیرد.</p><p>این متن نمونه است و از پنل مدیریت قابل ویرایش است.</p>"),
    ("راهنمای خرید و ارسال", "shipping-guide", "<h2>مراحل خرید</h2><ol><li>محصول را به سبد خرید اضافه کنید.</li><li>با شماره موبایل وارد شوید و کد تایید را وارد کنید.</li><li>آدرس را انتخاب کرده و از طریق درگاه امن بانکی پرداخت کنید.</li></ol><h2>زمان ارسال</h2><p>سفارش‌های تهران ۱ تا ۲ روز کاری و سایر شهرها ۲ تا ۵ روز کاری تحویل داده می‌شوند.</p>"),
]

ARTICLE_CATEGORIES = [("مراقبت از پوست", "skin-tips"), ("آموزش آرایش", "makeup-tutorials"), ("راهنمای خرید", "buying-guide")]

ARTICLES = [
    ("راهنمای انتخاب کرم ضدآفتاب مناسب نوع پوست", "sunscreen-guide", "skin-tips", ["کرم ضدآفتاب رنگی SPF50", "کرم مرطوب‌کننده آبرسان هیالورونیک"],
     "ضدآفتاب مهم‌ترین مرحله مراقبت روزانه از پوست است. در این مقاله یاد می‌گیرید چطور ضدآفتاب مناسب پوستتان را انتخاب کنید.",
     """<h2>چرا ضدآفتاب مهم است؟</h2><p>اشعه فرابنفش خورشید حتی در روزهای ابری به پوست می‌رسد و عامل اصلی لک، چین‌وچروک زودرس و آسیب‌های جدی‌تر پوستی است. استفاده روزانه از ضدآفتاب ساده‌ترین راه حفظ سلامت و جوانی پوست است.</p>
<h2>SPF چقدر باید باشد؟</h2><p>برای استفاده روزانه، ضدآفتابی با SPF حداقل ۳۰ و محافظت «طیف گسترده» (UVA و UVB) توصیه می‌شود. اگر مدت طولانی زیر آفتاب هستید، SPF بالاتر انتخاب کنید.</p>
<h3>انتخاب بر اساس نوع پوست</h3><ul><li><strong>پوست چرب:</strong> ضدآفتاب‌های فاقد چربی (Oil-free) با بافت ژل یا فلوئید.</li><li><strong>پوست خشک:</strong> فرمول‌های کرمی حاوی مواد مرطوب‌کننده.</li><li><strong>پوست حساس:</strong> ضدآفتاب‌های فیزیکی (مینرال) و بدون عطر.</li></ul>
<blockquote>ضدآفتاب را ۱۵ دقیقه قبل از بیرون رفتن بزنید و هر دو ساعت یک‌بار تمدید کنید.</blockquote>"""),
    ("روتین مراقبت از پوست در ۵ مرحله ساده", "skincare-routine", "skin-tips", ["ژل شست‌وشوی صورت پوست چرب", "تونر گلاب و آلوئه‌ورا", "سرم ویتامین C روشن‌کننده"],
     "با یک روتین ساده و منظم می‌توانید پوستی سالم‌تر و شاداب‌تر داشته باشید.",
     """<h2>مرحله ۱: پاک‌سازی</h2><p>صبح و شب صورت خود را با یک شوینده ملایم متناسب با نوع پوستتان بشویید.</p>
<h2>مرحله ۲: تونر</h2><p>تونر به متعادل کردن پوست و آماده‌سازی آن برای جذب بهتر مراحل بعدی کمک می‌کند.</p>
<h2>مرحله ۳: سرم</h2><p>سرم‌ها غلظت بالایی از مواد مؤثره دارند؛ مثلاً ویتامین C برای روشنی پوست در روتین صبح مناسب است.</p>
<h2>مرحله ۴: مرطوب‌کننده</h2><p>حتی پوست‌های چرب هم به آبرسانی نیاز دارند؛ کافی است مرطوب‌کننده سبک انتخاب کنید.</p>
<h2>مرحله ۵: ضدآفتاب</h2><p>آخرین و مهم‌ترین مرحله روتین صبح، استفاده از ضدآفتاب است.</p>"""),
    ("چطور رژ لب مناسب رنگ پوستمان انتخاب کنیم؟", "choose-lipstick", "makeup-tutorials", ["رژ لب جامد مات رنگ ۱۰۵", "رژ لب مایع بادوام", "برق لب شیشه‌ای"],
     "رنگ مناسب رژ لب می‌تواند کل چهره را درخشان‌تر نشان دهد. با چند نکته ساده رنگ ایده‌آل خود را پیدا کنید.",
     """<p>برای انتخاب رژ لب، ابتدا «زیرتون» پوست خود را بشناسید: گرم، سرد یا خنثی.</p>
<h3>زیرتون گرم</h3><p>رنگ‌های آجری، مرجانی و نارنجی‌های گرم معمولاً به این پوست‌ها بسیار می‌آیند.</p>
<h3>زیرتون سرد</h3><p>صورتی‌های سرد، قرمزهای آبی‌دار و رنگ‌های بری انتخاب‌های خوبی هستند.</p>
<h3>زیرتون خنثی</h3><p>خوش‌شانس هستید! بیشتر رنگ‌ها، به‌خصوص نودهای صورتی و قرمزهای کلاسیک به شما می‌آیند.</p>
<blockquote>قبل از رژ لب، از بالم لب استفاده کنید تا رنگ یکدست‌تر و ماندگارتر شود.</blockquote>"""),
    ("نکات مهم نگهداری و تاریخ انقضای لوازم آرایشی", "cosmetics-storage", "buying-guide", ["ریمل حجم‌دهنده ضدآب", "پنکک فشرده دو حالته"],
     "لوازم آرایشی هم تاریخ مصرف دارند. با رعایت چند نکته ساده، هم سالم‌تر آرایش کنید و هم عمر محصولات را بیشتر کنید.",
     """<h2>علامت PAO چیست؟</h2><p>روی بسیاری از محصولات، شکل یک قوطی باز با عددی مثل 12M دیده می‌شود؛ یعنی محصول پس از باز شدن تا ۱۲ ماه قابل استفاده است.</p>
<h3>عمر تقریبی محصولات پس از باز شدن</h3><ul><li>ریمل و خط چشم مایع: ۳ تا ۶ ماه</li><li>کرم پودر: ۶ تا ۱۲ ماه</li><li>پنکک و سایه‌های پودری: ۱۲ تا ۲۴ ماه</li><li>رژ لب: حدود ۱۲ ماه</li></ul>
<h3>نکات نگهداری</h3><ul><li>محصولات را دور از نور مستقیم و گرما نگه دارید.</li><li>برس‌ها و اسفنج‌ها را مرتب بشویید.</li><li>لوازم آرایش چشم را با دیگران به اشتراک نگذارید.</li></ul>"""),
]


class Command(BaseCommand):
    help = "ایجاد داده‌های نمونه (تنظیمات، برند، محصول، بنر، مقاله و ...) برای مشاهده ظاهر فروشگاه"

    @transaction.atomic
    def handle(self, *args, **options):
        self._site()
        self._contact()
        categories = self._categories()
        brands = self._brands()
        products = self._products(categories, brands)
        self._banners()
        self._pages()
        self._articles(products)
        self.stdout.write(self.style.SUCCESS("داده‌های نمونه با موفقیت ایجاد شد."))

    def _log(self, message):
        self.stdout.write(f"  • {message}")

    def _site(self):
        site = SiteSettings.load()
        if site.site_name == SiteSettings._meta.get_field("site_name").default:
            site.site_name = "رز بیوتی"
            site.slogan = "زیبایی اصیل، انتخاب هوشمندانه"
            site.about_short = (
                "فروشگاه اینترنتی رز بیوتی، عرضه‌کننده محصولات آرایشی و بهداشتی اصل "
                "با ضمانت اصالت کالا و ارسال سریع به سراسر ایران."
            )
            site.phone = "021-00000000"
            site.email = "info@example.com"
            site.working_hours = "شنبه تا پنجشنبه، ۱۰ صبح تا ۹ شب"
            site.shipping_cost = 45000
            site.free_shipping_threshold = 1500000
            site.meta_description = "خرید اینترنتی لوازم آرایشی و بهداشتی اصل با بهترین قیمت"
            site.save()
        self._log("تنظیمات سایت")

    def _contact(self):
        links = [
            (SocialLink.Platform.INSTAGRAM, "your_shop", "اینستاگرام"),
            (SocialLink.Platform.TELEGRAM, "your_shop", "کانال تلگرام"),
            (SocialLink.Platform.WHATSAPP, "09120000000", "پشتیبانی واتساپ"),
            (SocialLink.Platform.TWITTER, "your_shop", "توییتر"),
            (SocialLink.Platform.PHONE, "021-00000000", "تماس تلفنی"),
        ]
        for order, (platform, value, title) in enumerate(links):
            SocialLink.objects.get_or_create(platform=platform, defaults={"value": value, "title": title, "order": order})
        Branch.objects.get_or_create(
            name="فروشگاه مرکزی",
            defaults={
                "address": "تهران، خیابان ولیعصر، نرسیده به میدان ونک، پلاک ۱۲۳ (آدرس نمونه)",
                "phone": "021-00000000",
                "working_hours": "شنبه تا پنجشنبه ۱۰ تا ۲۱ — جمعه‌ها ۱۶ تا ۲۱",
                "latitude": "35.757400",
                "longitude": "51.409700",
                "zoom": 16,
            },
        )
        self._log("شبکه‌های اجتماعی و موقعیت فروشگاه")

    def _categories(self):
        result = {}
        for order, (name, slug, kind, color, children) in enumerate(CATEGORIES):
            parent, created = Category.objects.get_or_create(slug=slug, defaults={"name": name, "order": order})
            if created:
                parent.image.save(f"{slug}.png", category_image(kind, color), save=True)
            result[slug] = parent
            for child_order, (child_name, child_slug) in enumerate(children):
                child, _ = Category.objects.get_or_create(
                    slug=child_slug, defaults={"name": child_name, "parent": parent, "order": child_order}
                )
                result[child_slug] = child
        self._log(f"{len(result)} دسته‌بندی")
        return result

    def _brands(self):
        result = {}
        for order, (name, latin, country, color) in enumerate(BRANDS):
            brand, created = Brand.objects.get_or_create(
                name=name,
                defaults={
                    "name_en": latin,
                    "slug": latin.lower(),
                    "country": country,
                    "order": order,
                    "description": f"<p>برند {name} ({latin}) از تولیدکنندگان محصولات آرایشی و بهداشتی. (متن نمونه)</p>",
                },
            )
            if created:
                brand.logo.save(f"{latin.lower()}.png", logo_image(latin[0], latin, color), save=True)
            result[latin] = brand
        self._log(f"{len(result)} برند")
        return result

    def _products(self, categories, brands):
        now = timezone.now()
        result = {}
        for index, row in enumerate(PRODUCTS):
            name, cat, brand, price, discount, stock, kind, color, featured, sold, specs, summary = row
            features = "".join(f"<li>{title}: {value}</li>" for title, value in specs)
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    "category": categories[cat],
                    "brand": brands[brand],
                    "price": price,
                    "discount_price": discount,
                    "stock": stock,
                    "is_featured": featured,
                    "sold_count": sold,
                    "sku": f"RB-{1001 + index}",
                    "short_description": summary,
                    "description": PRODUCT_DESCRIPTION.format(summary=summary, features=features),
                },
            )
            if created:
                for variant in range(3):
                    image = ProductImage(product=product, order=variant, alt_text=name)
                    image.image.save(f"{product.sku.lower()}-{variant + 1}.jpg", product_image(kind, color, variant), save=True)
                for order, (title, value) in enumerate(specs):
                    ProductSpecification.objects.create(product=product, title=title, value=value, order=order)
                Product.objects.filter(pk=product.pk).update(created_at=now - timedelta(days=index * 2))
            result[name] = product
        self._log(f"{len(result)} محصول (هر کدام با ۳ تصویر)")
        return result

    def _banners(self):
        for order, (title, subtitle, button, link, colors, items, position) in enumerate(BANNERS):
            if Banner.objects.filter(title=title).exists():
                continue
            banner = Banner(
                title=title, subtitle=subtitle, button_text=button, link=link, position=position, order=order
            )
            if position == Banner.Position.HERO:
                banner.image.save(f"hero-{order + 1}.jpg", scene_image((1920, 640), colors, items), save=False)
                # Mobile version: products at the top, the caption sits at the bottom.
                shown = items[:2]
                positions = [0.5] if len(shown) == 1 else [0.34, 0.66]
                mobile_items = [(kind, color, x, 0.62) for (kind, color, _, _), x in zip(shown, positions, strict=True)]
                banner.mobile_image.save(
                    f"hero-{order + 1}-mobile.jpg",
                    scene_image((800, 600), (colors[1], colors[0]), mobile_items, vertical_center=0.38),
                    save=False,
                )
            else:
                banner.image.save(f"promo-{order + 1}.jpg", scene_image((900, 400), colors, items), save=False)
            banner.save()
        self._log("بنرهای اسلایدر و تبلیغاتی")

    def _pages(self):
        site_name = SiteSettings.load().site_name
        for order, (title, slug, body) in enumerate(PAGES):
            Page.objects.get_or_create(slug=slug, defaults={"title": title, "body": body.format(site=site_name), "order": order})
        self._log("صفحات ثابت")

    def _articles(self, products):
        categories = {}
        for order, (name, slug) in enumerate(ARTICLE_CATEGORIES):
            categories[slug], _ = ArticleCategory.objects.get_or_create(slug=slug, defaults={"name": name, "order": order})
        now = timezone.now()
        cover_items = [
            [("tube", (222, 184, 150), .35, .9), ("jar", (110, 170, 225), .6, .8)],
            [("pump", (110, 185, 145), .3, .8), ("bottle", (238, 160, 186), .5, .85), ("dropper", (240, 160, 60), .7, .8)],
            [("lipstick", (190, 30, 60), .35, .9), ("lipstick", (240, 120, 160), .5, .8), ("mascara", (200, 40, 90), .65, .85)],
            [("palette", (190, 140, 120), .4, .7), ("mascara", (45, 45, 58), .68, .85)],
        ]
        cover_colors = [((255, 238, 214), (230, 170, 120)), ((226, 246, 236), (110, 185, 145)), ((255, 226, 234), (196, 38, 76)), ((238, 230, 250), (150, 105, 170))]
        for index, (title, slug, category, related, summary, body) in enumerate(ARTICLES):
            article, created = Article.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "category": categories[category],
                    "summary": summary,
                    "body": body,
                    "status": Article.Status.PUBLISHED,
                    "published_at": now - timedelta(days=3 + index * 5),
                    "is_featured": index == 0,
                },
            )
            if created:
                article.cover.save(f"{slug}.jpg", scene_image((1200, 675), cover_colors[index], cover_items[index]), save=True)
                article.related_products.set([products[name] for name in related if name in products])
        self._log(f"{len(ARTICLES)} مقاله")
