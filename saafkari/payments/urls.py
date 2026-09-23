from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("start/<str:code>/", views.start_payment, name="start"),
    path("callback/<str:invoice>/", views.payment_callback, name="callback"),
    path("receipt/<str:invoice>/", views.receipt_view, name="receipt"),
    path("sandbox/<str:invoice>/", views.sandbox_view, name="sandbox"),
    path("mine/", views.my_payments, name="mine"),
]
