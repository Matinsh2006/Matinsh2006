from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("start/<str:number>/", views.start_payment, name="start"),
    path("callback/<uuid:uuid>/", views.payment_callback, name="callback"),
    path("test-gateway/<str:authority>/", views.fake_gateway, name="fake_gateway"),
]
