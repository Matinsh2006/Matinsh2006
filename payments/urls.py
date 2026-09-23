from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("request/<int:appointment_id>/", views.request_payment_view, name="request_payment"),
    path("callback/<int:pk>/", views.payment_callback, name="callback"),
    path("result/<int:pk>/", views.payment_result, name="result"),
]
