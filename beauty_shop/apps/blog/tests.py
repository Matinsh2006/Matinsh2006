from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Article, ArticleCategory
from apps.core.testing import make_product, make_user


def make_article(title, status=Article.Status.PUBLISHED, **extra):
    return Article.objects.create(title=title, body="<p>" + "کلمه " * 450 + "</p>", status=status, **extra)


class ArticleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = ArticleCategory.objects.create(name="مراقبت از پوست")
        cls.published = make_article("راهنمای ضدآفتاب", category=cls.category)
        cls.draft = make_article("پیش‌نویس", status=Article.Status.DRAFT)
        cls.scheduled = make_article("مقاله آینده", published_at=timezone.now() + timedelta(days=2))

    def test_list_shows_only_published(self):
        response = self.client.get(reverse("blog:list"))
        self.assertEqual(list(response.context["articles"]), [self.published])
        response = self.client.get(self.category.get_absolute_url())
        self.assertEqual(list(response.context["articles"]), [self.published])

    def test_detail_and_views_counted_once_per_session(self):
        product = make_product(name="ضدآفتاب رنگی")
        self.published.related_products.add(product)
        response = self.client.get(self.published.get_absolute_url())
        self.assertContains(response, "راهنمای ضدآفتاب")
        self.assertContains(response, "ضدآفتاب رنگی")
        self.client.get(self.published.get_absolute_url())
        self.published.refresh_from_db()
        self.assertEqual(self.published.views, 1)
        # The product page links back to the article.
        self.assertIn(self.published, self.client.get(product.get_absolute_url()).context["related_articles"])

    def test_drafts_are_hidden_but_previewable_by_staff(self):
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(self.scheduled.get_absolute_url()).status_code, 404)
        self.client.force_login(make_user(is_staff=True))
        self.assertContains(self.client.get(self.draft.get_absolute_url()), "پیش‌نمایش")

    def test_reading_time_and_excerpt(self):
        self.assertEqual(self.published.reading_time, 2)
        self.assertTrue(self.published.excerpt.startswith("کلمه کلمه"))

    def test_search(self):
        response = self.client.get(reverse("blog:list"), {"q": "ضدآفتاب"})
        self.assertEqual(list(response.context["articles"]), [self.published])
