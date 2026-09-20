from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("women/", views.gender_list, {"gender": "women"}, name="women"),
    path("men/", views.gender_list, {"gender": "men"}, name="men"),
    path("brands/", views.brand_list, name="brand_list"),
    path("category/<str:slug>/", views.category_detail, name="category_detail"),
    path("product/<str:slug>/", views.product_detail, name="product_detail"),
]
