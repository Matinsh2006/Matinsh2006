from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("products/", views.product_list, name="product_list"),
    path("products/<uslug:slug>/", views.product_detail, name="product_detail"),
    path("categories/", views.category_list, name="category_list"),
    path("category/<uslug:category_slug>/", views.product_list, name="category"),
    path("brands/", views.brand_list, name="brand_list"),
    path("brands/<uslug:brand_slug>/", views.product_list, name="brand_detail"),
]
