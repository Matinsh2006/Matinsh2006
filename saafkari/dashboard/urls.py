"""نشانی‌های پنل کارفرما."""
from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    # نوبت‌ها
    path("appointments/", views.appointment_list, name="appointments"),
    path("appointments/<str:code>/", views.appointment_manage, name="appointment_manage"),
    # خدمات
    path("services/", views.ServiceListView.as_view(), name="services"),
    path("services/new/", views.ServiceCreateView.as_view(), name="service_create"),
    path("services/<int:pk>/edit/", views.ServiceUpdateView.as_view(), name="service_edit"),
    path("services/<int:pk>/delete/", views.ServiceDeleteView.as_view(), name="service_delete"),
    path("service-categories/", views.ServiceCategoryListView.as_view(), name="service_categories"),
    path("service-categories/new/", views.ServiceCategoryCreateView.as_view(), name="service_category_create"),
    path("service-categories/<int:pk>/edit/", views.ServiceCategoryUpdateView.as_view(), name="service_category_edit"),
    path("service-categories/<int:pk>/delete/", views.ServiceCategoryDeleteView.as_view(), name="service_category_delete"),
    # بنرها
    path("banners/", views.BannerListView.as_view(), name="banners"),
    path("banners/new/", views.BannerCreateView.as_view(), name="banner_create"),
    path("banners/<int:pk>/edit/", views.BannerUpdateView.as_view(), name="banner_edit"),
    path("banners/<int:pk>/delete/", views.BannerDeleteView.as_view(), name="banner_delete"),
    # نمونه‌کارها
    path("portfolio/", views.PortfolioListView.as_view(), name="portfolio"),
    path("portfolio/new/", views.portfolio_form_view, name="portfolio_create"),
    path("portfolio/<int:pk>/edit/", views.portfolio_form_view, name="portfolio_edit"),
    path("portfolio/<int:pk>/delete/", views.PortfolioDeleteView.as_view(), name="portfolio_delete"),
    # مقالات
    path("articles/", views.ArticleListView.as_view(), name="articles"),
    path("articles/new/", views.ArticleCreateView.as_view(), name="article_create"),
    path("articles/<int:pk>/edit/", views.ArticleUpdateView.as_view(), name="article_edit"),
    path("articles/<int:pk>/delete/", views.ArticleDeleteView.as_view(), name="article_delete"),
    path("article-categories/", views.ArticleCategoryListView.as_view(), name="article_categories"),
    path("article-categories/new/", views.ArticleCategoryCreateView.as_view(), name="article_category_create"),
    path("article-categories/<int:pk>/edit/", views.ArticleCategoryUpdateView.as_view(), name="article_category_edit"),
    path("article-categories/<int:pk>/delete/", views.ArticleCategoryDeleteView.as_view(), name="article_category_delete"),
    # شبکه‌های اجتماعی
    path("socials/", views.SocialLinkListView.as_view(), name="socials"),
    path("socials/new/", views.SocialLinkCreateView.as_view(), name="social_create"),
    path("socials/<int:pk>/edit/", views.SocialLinkUpdateView.as_view(), name="social_edit"),
    path("socials/<int:pk>/delete/", views.SocialLinkDeleteView.as_view(), name="social_delete"),
    # لوکیشن
    path("locations/", views.LocationListView.as_view(), name="locations"),
    path("locations/new/", views.LocationCreateView.as_view(), name="location_create"),
    path("locations/<int:pk>/edit/", views.LocationUpdateView.as_view(), name="location_edit"),
    path("locations/<int:pk>/delete/", views.LocationDeleteView.as_view(), name="location_delete"),
    # تنظیمات و ساعت کاری
    path("settings/", views.site_settings_view, name="settings"),
    path("working-hours/", views.working_hours_view, name="working_hours"),
    path("holidays/new/", views.holiday_create, name="holiday_create"),
    path("holidays/<int:pk>/delete/", views.holiday_delete, name="holiday_delete"),
    # مالی و مشتریان
    path("payments/", views.payment_list, name="payments"),
    path("customers/", views.customer_list, name="customers"),
    path("messages/", views.message_list, name="messages"),
]
