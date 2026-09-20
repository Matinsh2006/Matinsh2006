from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.cart_detail, name="cart_detail"),
    path("add/<int:variant_id>/", views.cart_add, name="cart_add"),
    path("update/<int:item_id>/", views.cart_update, name="cart_update"),
    path("remove/<int:item_id>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<str:ref_code>/", views.order_detail, name="order_detail"),
]
