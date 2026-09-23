import io

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from articles.models import Article
from gallery.models import PortfolioImage, PortfolioItem
from salon.models import SalonProfile
from services.models import Service


def make_image_file(name, color):
    # Plain color placeholder only - PIL's default bitmap font can't shape
    # Persian text (letters render disconnected), so no text is drawn here.
    # Real photos uploaded via the admin won't have this limitation.
    from PIL import Image

    img = Image.new("RGB", (800, 600), color)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return ContentFile(buffer.getvalue(), name=name)


class Command(BaseCommand):
    help = "Populates the database with demo content so the site isn't empty on first run."

    def handle(self, *args, **options):
        self.seed_salon_profile()
        self.seed_services()
        self.seed_portfolio()
        self.seed_articles()
        self.stdout.write(self.style.SUCCESS("داده‌های نمونه با موفقیت ایجاد شدند."))

    def seed_salon_profile(self):
        salon = SalonProfile.get_solo()
        if salon.address:
            return
        salon.name = "آرایشگاه بانو متین"
        salon.tagline = "زیبایی شما، هنر ما"
        salon.about = (
            "آرایشگاه زنانه متین با سال‌ها تجربه، خدمات تخصصی زیبایی را در محیطی آرام "
            "و دخترانه به بانوان ارائه می‌دهد."
        )
        salon.address = "تهران، خیابان ولیعصر، نرسیده به میدان ونک، پلاک ۱۲۳، طبقه دوم"
        salon.map_lat = 35.7595
        salon.map_lng = 51.4110
        salon.contact_phone = "09120000000"
        salon.telegram_url = "https://t.me/matinsh_salon"
        salon.instagram_url = "https://instagram.com/matinsh_salon"
        salon.whatsapp_url = "https://wa.me/989120000000"
        salon.twitter_url = "https://twitter.com/matinsh_salon"
        salon.save()

    def seed_services(self):
        if Service.objects.exists():
            return
        data = [
            {
                "name": "کوتاهی و شینیون مو",
                "short_description": "کوتاهی حرفه‌ای و شینیون مخصوص مجالس",
                "description": "کوتاهی و شینیون مو متناسب با فرم صورت شما، توسط آرایشگران مجرب.",
                "price": 350000,
                "duration_minutes": 45,
                "deposit_amount": 0,
            },
            {
                "name": "رنگ و هایلایت مو",
                "short_description": "رنگ مو با محصولات باکیفیت و بدون آسیب",
                "description": "رنگ، مش و هایلایت مو با جدیدترین تکنیک‌های روز دنیا.",
                "price": 1200000,
                "duration_minutes": 120,
                "deposit_amount": 200000,
            },
            {
                "name": "کراتین و احیا مو",
                "short_description": "صافی و احیای موهای آسیب‌دیده",
                "description": "کراتین تخصصی برای احیا و صاف کردن موهای وز و آسیب‌دیده.",
                "price": 1800000,
                "duration_minutes": 180,
                "deposit_amount": 300000,
            },
            {
                "name": "میکاپ عروس و مجلسی",
                "short_description": "میکاپ حرفه‌ای مخصوص عروس و مجالس",
                "description": "میکاپ ماندگار و متناسب با پوست شما برای روزهای خاص.",
                "price": 2500000,
                "duration_minutes": 90,
                "deposit_amount": 500000,
            },
            {
                "name": "مانیکور و پدیکور",
                "short_description": "خدمات کامل ناخن با ژلیش",
                "description": "مانیکور و پدیکور بهداشتی همراه با ژلیش و طراحی ناخن.",
                "price": 400000,
                "duration_minutes": 60,
                "deposit_amount": 0,
            },
        ]
        colors = ["#ad4a72", "#c9a24a", "#8a3a5b", "#d98fa3", "#7c6a70"]
        for index, item in enumerate(data):
            service = Service(**item)
            service.image.save(
                f"service-{index}.jpg",
                make_image_file(f"service-{index}.jpg", colors[index % len(colors)]),
                save=False,
            )
            service.save()

    def seed_portfolio(self):
        if PortfolioItem.objects.exists():
            return
        titles = ["رنگ موی کاراملی", "کراتین و احیای مو", "میکاپ عروس", "مش و هایلایت"]
        for index, title in enumerate(titles):
            item = PortfolioItem.objects.create(
                title=title, description="نمونه‌ای از کار انجام‌شده در سالن."
            )
            before = make_image_file(f"portfolio-{index}-before.jpg", "#7c6a70")
            after = make_image_file(f"portfolio-{index}-after.jpg", "#ad4a72")
            PortfolioImage.objects.create(
                portfolio_item=item, image=before, image_type=PortfolioImage.TYPE_BEFORE, order=1
            )
            PortfolioImage.objects.create(
                portfolio_item=item, image=after, image_type=PortfolioImage.TYPE_AFTER, order=2
            )

    def seed_articles(self):
        if Article.objects.exists():
            return
        articles = [
            {
                "title": "۵ نکته برای مراقبت از موهای رنگ‌شده",
                "summary": "راهکارهایی ساده برای ماندگاری بیشتر رنگ مو",
                "content": (
                    "<p>مراقبت از موهای رنگ‌شده نیازمند استفاده از شامپوهای مخصوص، "
                    "اجتناب از آب داغ هنگام شست‌وشو و استفاده منظم از ماسک مو است.</p>"
                    "<p>همچنین بهتر است حداقل هفته‌ای یک بار از روغن‌های طبیعی برای "
                    "تغذیه موها استفاده کنید.</p>"
                ),
            },
            {
                "title": "چگونه پوستی شاداب داشته باشیم؟",
                "summary": "راهنمای مراقبت روزانه از پوست",
                "content": (
                    "<p>نوشیدن آب کافی، استفاده از ضدآفتاب و پاکسازی منظم پوست از "
                    "مهم‌ترین اصول داشتن پوستی شاداب هستند.</p>"
                ),
            },
        ]
        for data in articles:
            Article.objects.create(**data)
