from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("pay/<str:number>/", views.pay_order, name="pay"),
    path("callback/<str:gateway_code>/", views.callback, name="callback"),
    path("result/<str:number>/", views.result, name="result"),
    path("test-gateway/<str:authority>/", views.fake_gateway, name="fake_gateway"),
]
