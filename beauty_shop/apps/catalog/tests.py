from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Product
from apps.core.testing import make_brand, make_category, make_product


class ProductModelTests(TestCase):
    def test_prices_and_discount(self):
        product = make_product(price=200000, discount_price=150000)
        self.assertTrue(product.has_discount)
        self.assertEqual(product.final_price, 150000)
        self.assertEqual(product.discount_percent, 25)
        product.discount_price = 250000
        self.assertFalse(product.has_discount)
        self.assertEqual(product.final_price, 200000)
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_unique_persian_slugs_and_normalized_name(self):
        first = make_product(name="كرم مرطوب‌كننده")
        second = make_product(name="کرم مرطوب‌کننده")
        self.assertEqual(first.name, "کرم مرطوب‌کننده")  # Arabic letters normalized
        self.assertEqual(first.slug, "کرم-مرطوب-کننده")
        self.assertEqual(second.slug, "کرم-مرطوب-کننده-2")

    def test_max_order_quantity(self):
        with self.settings(CART_MAX_QUANTITY_PER_ITEM=5):
            self.assertEqual(make_product(stock=3).max_order_quantity, 3)
            self.assertEqual(make_product(stock=30).max_order_quantity, 5)


class CatalogViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.skin = make_category("مراقبت از پوست", slug="skin")
        cls.cream = make_category("کرم", slug="cream", parent=cls.skin)
        cls.lips = make_category("آرایش لب", slug="lips")
        cls.glara = make_brand("گلارا", slug="glara")
        cls.nila = make_brand("نیلا", slug="nila")
        cls.cheap = make_product(name="کرم ارزان", price=90000, category=cls.cream, brand=cls.glara, sold_count=5)
        cls.discounted = make_product(name="کرم تخفیف‌دار", price=300000, discount_price=100000, category=cls.skin, brand=cls.nila)
        cls.lipstick = make_product(name="رژ لب قرمز", price=250000, category=cls.lips, brand=cls.glara, sold_count=50)
        cls.soldout = make_product(name="رژ لب ناموجود", price=120000, stock=0, category=cls.lips)
        cls.hidden = make_product(name="محصول مخفی", is_active=False)

    def names(self, response):
        return [product.name for product in response.context["products"]]

    def test_list_hides_inactive_and_puts_soldout_last(self):
        names = self.names(self.client.get(reverse("catalog:product_list")))
        self.assertNotIn("محصول مخفی", names)
        self.assertEqual(names[-1], "رژ لب ناموجود")

    def test_category_includes_children(self):
        names = self.names(self.client.get(self.skin.get_absolute_url()))
        self.assertCountEqual(names, ["کرم ارزان", "کرم تخفیف‌دار"])
        self.assertEqual(self.client.get(reverse("catalog:category", args=["missing"])).status_code, 404)

    def test_filters(self):
        url = reverse("catalog:product_list")
        self.assertCountEqual(self.names(self.client.get(url, {"brand": ["glara"]})), ["کرم ارزان", "رژ لب قرمز"])
        # Price filter uses the discounted price.
        self.assertCountEqual(self.names(self.client.get(url, {"max_price": "۱۰۰٬۰۰۰"})), ["کرم ارزان", "کرم تخفیف‌دار"])
        self.assertEqual(self.names(self.client.get(url, {"discount": "1"})), ["کرم تخفیف‌دار"])
        self.assertNotIn("رژ لب ناموجود", self.names(self.client.get(url, {"available": "1"})))
        self.assertCountEqual(self.names(self.client.get(url, {"category": "lips"})), ["رژ لب قرمز", "رژ لب ناموجود"])

    def test_sorting(self):
        url = reverse("catalog:product_list")
        self.assertEqual(self.names(self.client.get(url, {"sort": "cheapest"}))[:3], ["کرم ارزان", "کرم تخفیف‌دار", "رژ لب قرمز"])
        self.assertEqual(self.names(self.client.get(url, {"sort": "bestselling"}))[0], "رژ لب قرمز")
        self.assertEqual(self.names(self.client.get(url, {"sort": "discount"}))[0], "کرم تخفیف‌دار")

    def test_search_normalizes_arabic_letters(self):
        response = self.client.get(reverse("catalog:product_list"), {"q": "كرم"})
        self.assertCountEqual(self.names(response), ["کرم ارزان", "کرم تخفیف‌دار"])
        response = self.client.get(reverse("catalog:product_list"), {"q": "گلارا رژ"})
        self.assertEqual(self.names(response), ["رژ لب قرمز"])

    def test_brand_page(self):
        response = self.client.get(self.glara.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(self.names(response), ["کرم ارزان", "رژ لب قرمز"])
        self.assertContains(self.client.get(reverse("catalog:brand_list")), "گلارا")

    def test_product_detail(self):
        response = self.client.get(self.lipstick.get_absolute_url())
        self.assertContains(response, "رژ لب قرمز")
        self.assertContains(response, "application/ld+json")
        self.assertIn(self.soldout, response.context["related_products"])
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)

    def test_pagination(self):
        with self.settings(PRODUCTS_PER_PAGE=2):
            response = self.client.get(reverse("catalog:product_list"), {"page": 2})
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(Product.objects.active().count(), 4)
