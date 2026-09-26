from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("shop/", views.shop, name="shop"),
    path("men/", views.gender_view, {"gender": "men"}, name="men"),
    path("women/", views.gender_view, {"gender": "women"}, name="women"),
    path("category/<str:slug>/", views.category_view, name="category"),
    path("category/<str:parent_slug>/<str:slug>/", views.subcategory_view, name="subcategory"),
    path("brand/<str:slug>/", views.brand_view, name="brand"),
    path("product/<str:slug>/", views.product_detail, name="product"),
    path("search/", views.search_view, name="search"),
    path("search/suggest/", views.search_suggest, name="search_suggest"),
]
