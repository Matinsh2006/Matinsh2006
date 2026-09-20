from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import (
    Brand,
    Category,
    Color,
    Gender,
    Product,
    ProductKind,
    ProductVariant,
    Size,
)


class CatalogTestData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand = Brand.objects.create(name="درسا")
        cls.women_category = Category.objects.create(name="مانتو", gender=Gender.WOMEN)
        cls.men_category = Category.objects.create(name="پیراهن", gender=Gender.MEN)
        cls.size_m = Size.objects.create(label="M", size_type=ProductKind.CLOTHING, order=2)
        cls.size_l = Size.objects.create(label="L", size_type=ProductKind.CLOTHING, order=3)
        cls.black = Color.objects.create(name="مشکی", hex_code="#111827")
        cls.cream = Color.objects.create(name="کرم", hex_code="#e7d8c9")

        cls.manto = Product.objects.create(
            title="مانتو کتان", category=cls.women_category, brand=cls.brand, price=1_000_000
        )
        cls.shirt = Product.objects.create(
            title="پیراهن مردانه", category=cls.men_category, price=500_000, discount_price=400_000
        )
        ProductVariant.objects.create(product=cls.manto, size=cls.size_m, color=cls.black, stock=5)
        ProductVariant.objects.create(product=cls.manto, size=cls.size_l, color=cls.cream, stock=0)
        ProductVariant.objects.create(product=cls.shirt, size=cls.size_m, color=cls.black, stock=3)


class ProductModelTests(CatalogTestData):
    def test_gender_follows_category(self):
        self.assertEqual(self.manto.gender, Gender.WOMEN)
        self.assertEqual(self.shirt.gender, Gender.MEN)

    def test_unicode_slug_generated(self):
        self.assertTrue(self.manto.slug)
        self.assertIn("مانتو", self.manto.slug)

    def test_discount_calculation(self):
        self.assertTrue(self.shirt.has_discount)
        self.assertEqual(self.shirt.final_price, 400_000)
        self.assertEqual(self.shirt.discount_percent, 20)

    def test_available_sizes_excludes_out_of_stock(self):
        labels = [size.label for size in self.manto.available_sizes]
        self.assertEqual(labels, ["M"])

    def test_variant_price_uses_extra_price(self):
        variant = ProductVariant.objects.create(
            product=self.manto, size=self.size_l, color=self.black, stock=1, extra_price=50_000
        )
        self.assertEqual(variant.price, 1_050_000)


class ProductListViewTests(CatalogTestData):
    def test_gender_pages_separate_products(self):
        women = self.client.get(reverse("catalog:women"))
        men = self.client.get(reverse("catalog:men"))
        self.assertIn(self.manto, women.context["products"])
        self.assertNotIn(self.shirt, women.context["products"])
        self.assertIn(self.shirt, men.context["products"])

    def test_brand_filter(self):
        response = self.client.get(reverse("catalog:product_list"), {"brand": self.brand.slug})
        self.assertEqual(list(response.context["products"]), [self.manto])

    def test_search_filter(self):
        response = self.client.get(reverse("catalog:product_list"), {"q": "پیراهن"})
        self.assertEqual(list(response.context["products"]), [self.shirt])

    def test_price_filter(self):
        response = self.client.get(reverse("catalog:product_list"), {"max_price": "600000"})
        self.assertEqual(list(response.context["products"]), [self.shirt])

    def test_inactive_product_hidden(self):
        self.manto.is_active = False
        self.manto.save()
        response = self.client.get(reverse("catalog:product_list"))
        self.assertNotIn(self.manto, response.context["products"])

    def test_category_page(self):
        response = self.client.get(self.women_category.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["products"]), [self.manto])


class ProductDetailViewTests(CatalogTestData):
    def test_detail_renders_with_variant_map(self):
        response = self.client.get(self.manto.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        key = f"{self.size_m.pk}-{self.black.pk}"
        self.assertIn(key, response.context["variant_map"])
        self.assertEqual(response.context["variant_map"][key]["stock"], 5)

    def test_missing_product_returns_404(self):
        self.assertEqual(self.client.get("/shop/product/ناموجود/").status_code, 404)
