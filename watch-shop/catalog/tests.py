import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .forms import GroupedCategoryChoiceField
from .models import Brand, Category, Gender, Product, ProductImage

MEDIA = tempfile.mkdtemp()


def image_file(name="watch.png", color=(180, 120, 90)):
    buffer = BytesIO()
    Image.new("RGB", (40, 40), color).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_catalog():
    brand = Brand.objects.create(name="اورلیوس", name_en="Aurelius", slug="aurelius")
    sport = Category.objects.create(name="اسپرت", slug="sport")
    women = Category.objects.create(parent=sport, name="زنانه", slug="women", gender=Gender.WOMEN)
    men = Category.objects.create(parent=sport, name="مردانه", slug="men", gender=Gender.MEN)
    return brand, sport, women, men


@override_settings(MEDIA_ROOT=MEDIA)
class CatalogModelTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.brand, self.sport, self.women, self.men = make_catalog()

    def test_category_titles_follow_type_then_gender(self):
        self.assertEqual(self.women.title, "ساعت زنانه اسپرت")
        self.assertEqual(self.men.title, "ساعت مردانه اسپرت")
        self.assertEqual(self.sport.title, "ساعت اسپرت")
        self.assertEqual(str(self.women), "اسپرت › زنانه")
        self.assertEqual(self.women.get_absolute_url(), "/category/sport/women/")

    def test_only_two_levels(self):
        deep = Category(parent=self.women, name="خیلی عمیق", slug="deep")
        with self.assertRaises(ValidationError):
            deep.full_clean()

    def test_product_must_use_leaf_category(self):
        product = Product(name="ساعت", slug="x", brand=self.brand, category=self.sport, price=1000)
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_multiple_images_ordered(self):
        product = Product.objects.create(name="ساعت", slug="x", brand=self.brand, category=self.women, price=1000)
        ProductImage.objects.create(product=product, image=image_file("b.png"), order=2)
        ProductImage.objects.create(product=product, image=image_file("a.png"), order=1)
        self.assertEqual([img.order for img in product.ordered_images], [1, 2])
        self.assertEqual(product.main_image.order, 1)
        self.assertTrue(product.main_image.image.name.endswith(".webp"))

    def test_discount_and_gender(self):
        product = Product.objects.create(
            name="ساعت", slug="x", brand=self.brand, category=self.women, price=800, compare_at_price=1000
        )
        self.assertEqual(product.discount_percent, 20)
        self.assertEqual(product.gender, "women")
        self.assertEqual(list(Product.objects.for_gender("women")), [product])
        self.assertEqual(list(Product.objects.for_gender("men")), [])

    def test_grouped_category_choices(self):
        field = GroupedCategoryChoiceField(queryset=Category.objects.leaves().select_related("parent").order_by("parent__name", "name"))
        choices = list(field.choices)
        self.assertEqual(choices[0][0], "")
        group_name, options = choices[1]
        self.assertEqual(group_name, "اسپرت")
        self.assertEqual({label for _, label in options}, {"ساعت زنانه اسپرت", "ساعت مردانه اسپرت"})


@override_settings(MEDIA_ROOT=MEDIA)
class CatalogViewTests(TestCase):
    def setUp(self):
        self.brand, self.sport, self.women, self.men = make_catalog()
        self.lady = Product.objects.create(name="ساعت زنانه آبی", name_en="Aqua Lady", slug="aqua-lady", brand=self.brand, category=self.women, price=2_000_000)
        self.man = Product.objects.create(name="ساعت مردانه غواصی", name_en="Deep Sea", slug="deep-sea", brand=self.brand, category=self.men, price=5_000_000, stock=0)

    def test_subcategory_page(self):
        response = self.client.get(reverse("catalog:subcategory", args=["sport", "women"]))
        self.assertContains(response, "ساعت زنانه اسپرت")
        self.assertContains(response, "Aqua Lady")
        self.assertNotContains(response, "Deep Sea")

    def test_category_page_includes_children(self):
        response = self.client.get(reverse("catalog:category", args=["sport"]))
        self.assertContains(response, "Aqua Lady")
        self.assertContains(response, "Deep Sea")

    def test_gender_pages(self):
        self.assertContains(self.client.get(reverse("catalog:women")), "Aqua Lady")
        self.assertNotContains(self.client.get(reverse("catalog:women")), "Deep Sea")

    def test_filters_and_sorting(self):
        response = self.client.get(reverse("catalog:shop"), {"sort": "expensive"})
        products = list(response.context["products"])
        # Out of stock items are listed last even when they are more expensive.
        self.assertEqual(products, [self.lady, self.man])
        response = self.client.get(reverse("catalog:shop"), {"available": "1"})
        self.assertEqual(list(response.context["products"]), [self.lady])
        response = self.client.get(reverse("catalog:shop"), {"max_price": "3000000"})
        self.assertEqual(list(response.context["products"]), [self.lady])

    def test_search_normalises_arabic_letters(self):
        response = self.client.get(reverse("catalog:search"), {"q": "زنانه آبي"})
        self.assertEqual(list(response.context["products"]), [self.lady])
        suggest = self.client.get(reverse("catalog:search_suggest"), {"q": "Deep"}).json()
        self.assertEqual(suggest["products"][0]["name"], "ساعت مردانه غواصی")

    def test_product_detail(self):
        response = self.client.get(self.lady.get_absolute_url())
        self.assertContains(response, "application/ld+json")
        self.assertContains(response, "ساعت زنانه اسپرت")

    def test_inactive_product_hidden(self):
        self.lady.is_active = False
        self.lady.save()
        self.assertEqual(self.client.get(self.lady.get_absolute_url()).status_code, 404)


@override_settings(MEDIA_ROOT=MEDIA)
class CatalogAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(phone="09120000000", password="pass12345!")
        self.client.force_login(self.admin)
        self.brand, self.sport, self.women, self.men = make_catalog()

    def test_add_product_with_category_brand_and_bulk_images(self):
        response = self.client.get(reverse("admin:catalog_product_add"))
        self.assertContains(response, '<optgroup label="اسپرت">')
        self.assertContains(response, "ساعت زنانه اسپرت")
        data = {
            "name": "ساعت تست",
            "name_en": "Test",
            "slug": "test-watch",
            "sku": "",
            "brand": self.brand.pk,
            "category": self.women.pk,
            "price": "1500000",
            "stock": "3",
            "is_active": "on",
            "images-TOTAL_FORMS": "0",
            "images-INITIAL_FORMS": "0",
            "specs-TOTAL_FORMS": "0",
            "specs-INITIAL_FORMS": "0",
            "bulk_images": [image_file("1.png"), image_file("2.png"), image_file("3.png")],
        }
        response = self.client.post(reverse("admin:catalog_product_add"), data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        product = Product.objects.get(slug="test-watch")
        self.assertEqual(product.images.count(), 3)
        self.assertEqual(product.category, self.women)
        self.assertIsNone(product.sku)

    def test_root_category_creates_gender_children(self):
        response = self.client.post(
            reverse("admin:catalog_category_add"),
            {
                "name": "کلاسیک",
                "slug": "classic",
                "order": "0",
                "is_active": "on",
                "create_gender_children": "on",
                "children-TOTAL_FORMS": "0",
                "children-INITIAL_FORMS": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        classic = Category.objects.get(slug="classic", parent=None)
        self.assertEqual(sorted(classic.children.values_list("slug", flat=True)), ["men", "women"])

    def test_admin_changelists_load(self):
        for name in ["catalog_product", "catalog_category", "catalog_brand", "core_banner", "core_storelocation",
                     "orders_order", "payments_payment", "accounts_user"]:
            self.assertEqual(self.client.get(reverse(f"admin:{name}_changelist")).status_code, 200, name)
        self.assertEqual(self.client.get(reverse("admin:core_storelocation_add")).status_code, 200)
        response = self.client.get(reverse("admin:core_sitesettings_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(response["Location"]).status_code, 200)
